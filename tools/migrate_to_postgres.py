"""SQLiteスナップショットを空のPostgreSQLスキーマへ移行する。

接続文字列は秘密設定から取得。--applyがない場合は読み取り専用の事前確認。
実行前から完了・切替までアプリを停止し、移行元への書込みを止めること。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def digest(rows):
    return hashlib.sha256(json.dumps([list(r) for r in rows], ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def migrate(source_path: Path, schema: str, apply: bool):
    from database.postgres import PostgresConnection, create_schema, encode_value
    from psycopg import sql
    url = os.getenv('METEA_POSTGRES_URL', '')
    if not url:
        settings = tomllib.loads((ROOT / '.streamlit/secrets.toml').read_text(encoding='utf-8-sig'))
        url = settings['storage']['postgres_url']
    os.environ['METEA_POSTGRES_SCHEMA'] = schema
    ddl = (ROOT / 'database/schema_postgres.sql').read_text(encoding='utf-8')
    tables = re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', ddl)
    source = sqlite3.connect(source_path.resolve().as_uri() + '?mode=ro', uri=True)
    target = PostgresConnection(url)
    try:
        source.execute('BEGIN')
        if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or source.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('移行元DBの整合性チェックに失敗しました。')
        actual = {r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if actual != set(tables):
            raise RuntimeError('移行元のテーブル一覧がスキーマと一致しません。')
        target._prepare()
        target.raw.execute('SELECT pg_advisory_xact_lock(hashtext(%s), 194028)', (schema,))
        count = target.raw.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema=%s", (schema,)).fetchone()[0]
        if count:
            raise RuntimeError('移行先スキーマが空ではありません。上書きしません。')
        report = {'schema': schema, 'applied': apply, 'tables': {}}
        if apply:
            create_schema(target)
        for table in tables:
            columns = sorted(r[1] for r in source.execute(f'PRAGMA table_info("{table}")'))
            column_list = ','.join('"' + name.replace('"', '""') + '"' for name in columns)
            rows = source.execute(f'SELECT {column_list} FROM "{table}" ORDER BY id').fetchall()
            report['tables'][table] = {'rows': len(rows), 'sha256': digest(rows)}
            if not apply:
                continue
            target_columns = [r[0] for r in target.raw.execute(
                'SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s',
                (schema, table)).fetchall()]
            if set(columns) != set(target_columns):
                raise RuntimeError(f'移行元と移行先の列が一致しません: {table}')
            insert = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
                sql.Identifier(schema, table), sql.SQL(',').join(map(sql.Identifier, columns)),
                sql.SQL(',').join(sql.Placeholder() for _ in columns))
            with target.raw.cursor() as cursor:
                cursor.executemany(insert, [tuple(map(encode_value, row)) for row in rows])
            copied = target.raw.execute(sql.SQL('SELECT {} FROM {} ORDER BY id').format(
                sql.SQL(',').join(map(sql.Identifier, columns)), sql.Identifier(schema, table))).fetchall()
            if digest(copied) != digest(rows):
                raise RuntimeError(f'移行後の内容照合に失敗しました: {table}')
            highest = max((r[columns.index('id')] for r in rows), default=0)
            target.raw.execute('SELECT setval(pg_get_serial_sequence(%s, %s), %s, %s)',
                               (f'{schema}.{table}', 'id', max(1, highest), highest > 0))
        if apply:
            target.commit()
        return report
    except Exception:
        target.rollback()
        raise
    finally:
        target.close()
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--schema', default='public')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = migrate(args.source, args.schema, args.apply)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{'移行・全件照合完了' if args.apply else '事前確認完了'}: {len(report['tables'])} tables")
    except Exception as error:
        # 接続URLや行データを含む可能性があるため、DB例外の本文はログへ出さない。
        print('移行を停止しました:', type(error).__name__)
        if isinstance(error, RuntimeError):
            print(str(error))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
