"""保存先の設定ミスでSQLiteへ誤って書き込まないことを確認する。"""
import os
import unittest
from unittest.mock import patch

from database.connection import get_connection


class DatabaseConfigurationTest(unittest.TestCase):
    def test_unknown_backend_is_rejected_before_opening_sqlite(self):
        with patch.dict(os.environ, {'METEA_DATABASE_BACKEND': 'postgreql'}), \
             patch('database.connection.sqlite3.connect') as sqlite:
            with self.assertRaises(ValueError):
                get_connection()
            sqlite.assert_not_called()

    def test_postgres_connection_failure_never_falls_back_to_sqlite(self):
        with patch.dict(os.environ, {'METEA_DATABASE_BACKEND': 'postgresql',
                                    'METEA_POSTGRES_URL': 'postgresql://example.invalid/metea?sslmode=require'}), \
             patch('database.postgres.PostgresConnection', side_effect=ConnectionError('offline')), \
             patch('database.connection.sqlite3.connect') as sqlite:
            with self.assertRaises(ConnectionError):
                get_connection()
            sqlite.assert_not_called()

    def test_remote_postgres_without_tls_is_rejected(self):
        with patch.dict(os.environ, {'METEA_DATABASE_BACKEND': 'postgresql',
                                    'METEA_POSTGRES_URL': 'postgresql://example.invalid/metea?sslmode=disable'}), \
             patch('database.postgres.PostgresConnection') as postgres:
            with self.assertRaises(ValueError):
                get_connection()
            postgres.assert_not_called()
