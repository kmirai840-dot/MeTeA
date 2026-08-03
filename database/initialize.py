from pathlib import Path

from database.connection import get_connection


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def initialize_database() -> None:
    """必要なSQLiteテーブルを作成する。"""

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = get_connection()

    try:
        connection.executescript(schema)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()