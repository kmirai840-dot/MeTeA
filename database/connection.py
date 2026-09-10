from pathlib import Path
import os
import sqlite3


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "metea.db"


def get_database_path() -> Path:
    """環境変数があれば指定先、なければ従来のDBパスを返す。"""

    configured_path = os.getenv("METEA_DATABASE_PATH", "").strip()
    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return DEFAULT_DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """明示した保存先へ接続する。接続失敗時に別DBへ戻さない。"""

    backend = os.getenv('METEA_DATABASE_BACKEND', 'sqlite').strip().lower()
    if backend == 'postgresql':
        from database.postgres import PostgresConnection
        url = os.getenv('METEA_POSTGRES_URL', '').strip()
        if not url:
            import streamlit as st
            url = str(st.secrets.get('storage', {}).get('postgres_url', '')).strip()
        if not url.startswith(('postgresql://', 'postgres://')):
            raise ValueError('PostgreSQLの接続設定がありません。')
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        if parsed.hostname not in {'localhost', '127.0.0.1'} and parse_qs(parsed.query).get('sslmode', [''])[0] not in {'require', 'verify-ca', 'verify-full'}:
            raise ValueError('外部PostgreSQLにはTLS接続が必要です。')
        return PostgresConnection(url)
    if backend != 'sqlite':
        raise ValueError('METEA_DATABASE_BACKENDはsqliteまたはpostgresqlを指定してください。')

    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def begin_account_registration(connection):
    if getattr(connection, 'dialect', '') == 'postgresql':
        connection.execute("SELECT pg_advisory_xact_lock(hashtext(current_schema()), 194027)")
    else:
        connection.execute('BEGIN IMMEDIATE')
