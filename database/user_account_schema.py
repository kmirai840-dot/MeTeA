"""利用者アカウント用のSQLiteスキーマ移行処理。"""

from __future__ import annotations

import sqlite3


USER_ACCOUNT_COLUMNS: dict[str, str] = {
    "email": "TEXT COLLATE NOCASE",
    "display_name": "TEXT",
    "auth_provider": "TEXT",
    "auth_subject": "TEXT",
    "avatar_url": "TEXT",
    "email_verified": (
        "INTEGER NOT NULL DEFAULT 0 CHECK (email_verified IN (0, 1))"
    ),
    "is_active": "INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))",
    "last_login_at": "TEXT",
}


def _user_column_names(connection: sqlite3.Connection) -> set[str]:
    """usersテーブルに存在する列名を取得する。"""

    return {str(row[1]) for row in connection.execute("PRAGMA table_info(users)")}


def ensure_user_account_schema(connection: sqlite3.Connection) -> tuple[str, ...]:
    """既存データを保持したまま、利用者アカウント列と制約を追加する。

    複数回実行しても同じ状態になるように設計している。戻り値は今回追加した列名。
    """

    existing_columns = _user_column_names(connection)
    added_columns: list[str] = []

    for column_name, definition in USER_ACCOUNT_COLUMNS.items():
        if column_name in existing_columns:
            continue
        connection.execute(
            f'ALTER TABLE users ADD COLUMN "{column_name}" {definition}'
        )
        added_columns.append(column_name)

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email
        ON users(email COLLATE NOCASE)
        WHERE email IS NOT NULL AND TRIM(email) <> ''
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_users_auth_identity
        ON users(auth_provider, auth_subject)
        WHERE auth_provider IS NOT NULL
          AND TRIM(auth_provider) <> ''
          AND auth_subject IS NOT NULL
          AND TRIM(auth_subject) <> ''
        """
    )

    return tuple(added_columns)
