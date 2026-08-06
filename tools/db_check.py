"""SQLiteデータベースの内容を確認する開発用ツール。"""

from pathlib import Path
import sqlite3
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "metea.db"


def get_connection() -> sqlite3.Connection:
    """確認対象のSQLiteデータベースへ接続する。"""

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def get_table_names(
    connection: sqlite3.Connection,
) -> list[str]:
    """データベース内のテーブル名を取得する。"""

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def print_table(
    connection: sqlite3.Connection,
    table_name: str,
) -> None:
    """指定したテーブルの件数と内容を表示する。"""

    rows = connection.execute(
        f"SELECT * FROM {table_name}"
    ).fetchall()

    print()
    print("=" * 70)
    print(f"Table: {table_name}")
    print(f"件数: {len(rows)}")
    print("=" * 70)

    if not rows:
        print("データはありません。")
        return

    column_names = rows[0].keys()

    print(" | ".join(column_names))
    print("-" * 70)

    for row in rows:
        values = [
            str(row[column_name])
            for column_name in column_names
        ]

        print(" | ".join(values))


def main() -> None:
    """テーブル内容を表示する。"""

    connection = get_connection()

    try:
        table_names = get_table_names(connection)

        # 引数なし → 全テーブル表示
        if len(sys.argv) == 1:
            target_tables = table_names

        else:
            keyword = sys.argv[1].lower()

            # work と入力した場合
            if keyword == "work":
                target_tables = [
                    table_name
                    for table_name in table_names
                    if table_name.startswith("user_work_")
                ]

            # テーブル名指定
            else:
                target_tables = [
                    table_name
                    for table_name in table_names
                    if keyword in table_name.lower()
                ]

        if not target_tables:
            print("対象テーブルが見つかりません。")
            return

        for table_name in target_tables:
            print_table(connection, table_name)

    finally:
        connection.close()


if __name__ == "__main__":
    main()