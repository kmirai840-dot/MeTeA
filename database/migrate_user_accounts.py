"""既存SQLiteデータベースへ利用者アカウント列を追加する。"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from database.user_account_schema import ensure_user_account_schema


DEFAULT_DB_PATH = Path(__file__).with_name("metea.db")


def migrate(db_path: Path) -> tuple[str, ...]:
    """指定したSQLiteデータベースを安全に更新する。"""

    connection = sqlite3.connect(db_path)
    try:
        added = ensure_user_account_schema(connection)
        connection.commit()
        return added
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="usersテーブルへ利用者アカウント列と一意制約を追加します。"
    )
    parser.add_argument("db_path", nargs="?", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    added = migrate(args.db_path)
    if added:
        print(f"Added users columns: {', '.join(added)}")
    else:
        print("User account schema is already up to date.")


if __name__ == "__main__":
    main()
