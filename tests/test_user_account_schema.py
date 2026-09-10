from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from database.user_account_schema import (
    USER_ACCOUNT_COLUMNS,
    ensure_user_account_schema,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "database" / "schema.sql"


class UserAccountSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TEXT
            )
            """
        )
        self.connection.execute(
            """
            INSERT INTO users (id, created_at, updated_at)
            VALUES (1, '2026-08-18 00:00:00', '2026-08-18 00:00:00')
            """
        )

    def tearDown(self) -> None:
        self.connection.close()

    def test_migration_preserves_existing_user_and_adds_defaults(self) -> None:
        added = ensure_user_account_schema(self.connection)
        self.assertEqual(set(added), set(USER_ACCOUNT_COLUMNS))
        row = self.connection.execute(
            """
            SELECT id, created_at, email_verified, is_active
            FROM users
            WHERE id = 1
            """
        ).fetchone()
        self.assertEqual(row, (1, "2026-08-18 00:00:00", 0, 1))

    def test_migration_is_idempotent(self) -> None:
        ensure_user_account_schema(self.connection)
        self.assertEqual(ensure_user_account_schema(self.connection), ())

    def test_email_is_unique_case_insensitively(self) -> None:
        ensure_user_account_schema(self.connection)
        self.connection.execute(
            "INSERT INTO users (id, email) VALUES (2, 'friend@example.com')"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "INSERT INTO users (id, email) VALUES (3, 'FRIEND@example.com')"
            )

    def test_provider_subject_pair_is_unique(self) -> None:
        ensure_user_account_schema(self.connection)
        self.connection.execute(
            """
            INSERT INTO users (id, auth_provider, auth_subject)
            VALUES (2, 'google', 'google-subject')
            """
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                """
                INSERT INTO users (id, auth_provider, auth_subject)
                VALUES (3, 'google', 'google-subject')
                """
            )

    def test_fresh_schema_contains_account_columns_and_indexes(self) -> None:
        connection = sqlite3.connect(":memory:")
        try:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            ensure_user_account_schema(connection)
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(users)")
            }
            self.assertTrue(set(USER_ACCOUNT_COLUMNS).issubset(columns))
            indexes = {
                str(row[1]) for row in connection.execute("PRAGMA index_list(users)")
            }
            self.assertIn("ux_users_email", indexes)
            self.assertIn("ux_users_auth_identity", indexes)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
