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
    """MeTeAのSQLiteデータベースへ接続する。"""

    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection
