"""PostgreSQL接続と既存Repositoryの小さなDB-API互換境界。

ユーザー入力は常にドライバのパラメータとして渡す。DDLやSQLiteのPRAGMAは
ここで翻訳せず、PostgreSQL専用のスキーマ初期化を使用する。
"""
from functools import lru_cache
import atexit
import base64
import os
import re
import sqlite3

import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool


UTC_TEXT = "to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"
TEXT_PREFIX = '@metea:base64:v1:'


def encode_value(value):
    # PDF由来のNULはPostgreSQLのTEXTへ直接入らない。削除せず可逆保存する。
    # タグと同じ接頭辞を持つ通常の文字列も包み、誤復号を防ぐ。
    if isinstance(value, str) and ('\x00' in value or value.startswith(TEXT_PREFIX)):
        return TEXT_PREFIX + base64.b64encode(value.encode('utf-8')).decode('ascii')
    return value


def decode_value(value):
    if isinstance(value, str) and value.startswith(TEXT_PREFIX):
        return base64.b64decode(value[len(TEXT_PREFIX):], validate=True).decode('utf-8')
    return value


class Row:
    def __init__(self, pairs):
        self.data = dict(pairs)

    def keys(self):
        return self.data.keys()

    def __iter__(self):
        return iter(self.data.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.data.values())[key]
        return self.data[key]


def row_factory(cursor):
    names = [column.name for column in cursor.description] if cursor.description else []
    return lambda values: Row(zip(names, map(decode_value, values)))


def translate_sql(statement: str, parameters: bool = False) -> str:
    """文字列・コメントを除外してqmarkと現在時刻だけを変換する。"""
    tokens = re.split(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/)",
                      statement, flags=re.S)
    for i in range(0, len(tokens), 2):
        tokens[i] = re.sub(r'\bCURRENT_TIMESTAMP\b', UTC_TEXT, tokens[i], flags=re.I)
    # psycopgは引用符内でも%を解釈するので、パラメータ使用時のみ全体をエスケープ。
    if parameters:
        tokens = [part.replace('%', '%%') for part in tokens]
        for i in range(0, len(tokens), 2):
            tokens[i] = tokens[i].replace('?', '%s')
    return ''.join(tokens)


@lru_cache(maxsize=2)
def _pool(url):
    pool = ConnectionPool(url, min_size=1, max_size=6, timeout=20,
                          kwargs={'connect_timeout': 15, 'prepare_threshold': None,
                                  'row_factory': row_factory}, open=True)
    atexit.register(pool.close)
    return pool


class Cursor:
    def __init__(self, raw, lastrowid=None):
        self.raw = raw
        self.lastrowid = lastrowid
        self.rowcount = raw.rowcount

    def fetchone(self):
        return self.raw.fetchone() if self.raw.description else None

    def fetchall(self):
        return self.raw.fetchall() if self.raw.description else []

    def __iter__(self):
        return iter(self.raw)


class PostgresConnection:
    dialect = 'postgresql'

    def __init__(self, url):
        self.schema = os.getenv('METEA_POSTGRES_SCHEMA', 'public')
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', self.schema):
            raise ValueError('PostgreSQLスキーマ名が不正です。')
        try:
            self.pool = _pool(url)
            self.raw = self.pool.getconn()
        except Exception:
            raise ConnectionError('PostgreSQLに接続できません。接続設定を確認してください。') from None
        self.ready = False
        self.closed = False

    def _prepare(self):
        if not self.ready:
            # SET LOCALはNeonのトランザクションプーリングでも毎回適用する。
            self.raw.execute("SELECT set_config('search_path', %s, true), "
                             "set_config('TimeZone', 'UTC', true), "
                             "set_config('statement_timeout', '30000', true)", (self.schema,))
            self.ready = True

    def execute(self, statement, parameters=None):
        self._prepare()
        query = translate_sql(statement, parameters is not None)
        returning = bool(re.match(r'\s*INSERT\s+INTO\b', query, re.I)) and not re.search(r'\bRETURNING\b', query, re.I)
        if returning:
            query = query.rstrip().rstrip(';') + ' RETURNING id'
        try:
            cursor = self.raw.execute(query, tuple(map(encode_value, parameters)) if parameters is not None else None)
        except psycopg.IntegrityError:
            # 既存呼出し側の例外契約を維持し、個人情報を含むDB詳細は表示しない。
            raise sqlite3.IntegrityError('データの一意制約または参照制約に違反しました。') from None
        last_id = None
        if returning:
            row = cursor.fetchone()
            last_id = row[0] if row else None
        return Cursor(cursor, last_id)

    def executemany(self, statement, parameters):
        for values in parameters:
            self.execute(statement, values)

    def commit(self):
        self.raw.commit()
        self.ready = False

    def rollback(self):
        self.raw.rollback()
        self.ready = False

    def close(self):
        if not self.closed:
            self.raw.rollback()
            self.pool.putconn(self.raw)
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        self.rollback() if kind else self.commit()


def initialize_postgres(connection):
    """スキーマは移行ツールで準備する。通常起動ではバージョンのみ確認する。"""
    try:
        row = connection.execute('SELECT version FROM metea_schema_version').fetchone()
        if row is None or row[0] != 1:
            raise RuntimeError('PostgreSQLスキーマのバージョンが一致しません。')
    except psycopg.errors.UndefinedTable:
        raise RuntimeError('PostgreSQLの初期化・移行を先に実行してください。') from None


def create_schema(connection):
    """空の専用スキーマでのみ実行する初回DDL。既存テーブルは変更しない。"""
    from pathlib import Path
    connection._prepare()
    count = connection.raw.execute("SELECT count(*) FROM information_schema.tables "
                                   "WHERE table_schema=%s", (connection.schema,)).fetchone()[0]
    if count:
        raise RuntimeError('移行先が空ではありません。初期化を停止しました。')
    connection.raw.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(connection.schema)))
    ddl = Path(__file__).with_name('schema_postgres.sql').read_text(encoding='utf-8')
    connection.raw.execute(ddl, prepare=False)
