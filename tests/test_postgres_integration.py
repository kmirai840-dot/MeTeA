"""専用のランダムスキーマで実PostgreSQLを検証。publicには触れない。

METEA_TEST_POSTGRES_URLを明示したときだけ実行。既存の分離・認証テストを
同じRepositoryに対して再使用し、SQLite専用の検査だけ置き換える。
"""
import os
from pathlib import Path
import re
import unittest
import uuid
from unittest.mock import patch

import test_google_auth as google_tests
import test_user_data_isolation as isolation_tests
import test_storage_persistence as persistence_tests


class PostgresFixture:
    database_backend = 'postgresql'
    @classmethod
    def setUpClass(cls):
        if not os.getenv('METEA_TEST_POSTGRES_URL'):
            raise unittest.SkipTest('METEA_TEST_POSTGRES_URL is not configured')
        from database.connection import get_connection
        from database.postgres import create_schema
        cls.schema = 'metea_test_' + uuid.uuid4().hex
        cls.env = patch.dict(os.environ, {
            'METEA_DATABASE_BACKEND': 'postgresql',
            'METEA_POSTGRES_URL': os.environ['METEA_TEST_POSTGRES_URL'],
            'METEA_POSTGRES_SCHEMA': cls.schema,
        })
        cls.env.start()
        cls.addClassCleanup(cls.env.stop)
        cls.addClassCleanup(cls.drop_schema)
        c = get_connection()
        try:
            create_schema(c)
            c.commit()
        finally:
            c.close()
        ddl = Path(__file__).resolve().parents[1] / 'database/schema_postgres.sql'
        cls.tables = re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', ddl.read_text(encoding='utf-8'))

    @classmethod
    def drop_schema(cls):
        from database.connection import get_connection
        from psycopg import sql
        assert re.fullmatch(r'metea_test_[a-f0-9]{32}', cls.schema)
        c = get_connection()
        try:
            c.raw.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(cls.schema)))
            c.commit()
        finally:
            c.close()

    def setUp(self):
        from database.connection import get_connection
        from psycopg import sql
        c = get_connection()
        try:
            c._prepare()
            c.raw.execute(sql.SQL('TRUNCATE {} RESTART IDENTITY CASCADE').format(
                sql.SQL(',').join(sql.Identifier(self.schema, t) for t in self.tables)))
            c.execute('INSERT INTO users DEFAULT VALUES')
            c.commit()
        finally:
            c.close()
        super().setUp()


class PostgresIsolationTest(PostgresFixture, isolation_tests.UserDataIsolationTest):
    def dump(self):
        from database.connection import get_connection
        from psycopg import sql
        c = get_connection()
        try:
            c._prepare()
            return repr([(t, [tuple(row) for row in c.raw.execute(
                sql.SQL('SELECT * FROM {} ORDER BY id').format(sql.Identifier(self.schema, t))).fetchall()])
                for t in self.tables])
        finally:
            c.close()

    def test_all_25_tables_have_two_users_or_their_children(self):
        from database.connection import get_connection
        c = get_connection()
        try:
            self.assertEqual(len(self.tables), 25)
            for table in self.tables:
                self.assertGreaterEqual(c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], 2)
            self.assertEqual(c.execute("SELECT count(*) FROM pg_constraint "
                                       "WHERE connamespace=current_schema()::regnamespace "
                                       "AND contype='f' AND NOT convalidated").fetchone()[0], 0)
        finally:
            c.close()


class PostgresGoogleAccountTest(PostgresFixture, google_tests.GoogleAccountTest):
    pass


class PostgresRestartTest(PostgresFixture, persistence_tests.StoragePersistenceTest):
    pass


class PostgresQueryTest(PostgresFixture, unittest.TestCase):
    def test_parameters_literals_and_rollback(self):
        from database.connection import get_connection
        c = get_connection()
        try:
            malicious = "x'); DELETE FROM users; -- ? CURRENT_TIMESTAMP 50%"
            result = c.execute("SELECT ? AS data, '? CURRENT_TIMESTAMP 10%' AS literal", (malicious,)).fetchone()
            self.assertEqual(result['data'], malicious)
            self.assertEqual(result['literal'], '? CURRENT_TIMESTAMP 10%')
            for original in ['PDF\x00原文', '@metea:base64:v1:literal']:
                c.execute('INSERT INTO users(display_name) VALUES (?)', (original,))
                self.assertEqual(c.execute('SELECT display_name FROM users ORDER BY id DESC LIMIT 1').fetchone()[0], original)
            c.rollback()
            c.execute('INSERT INTO users(email) VALUES (?)', ('rollback@example.com',))
            c.rollback()
            self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0], 1)
        finally:
            c.close()


class PostgresMigrationTest(unittest.TestCase):
    def test_all_tables_copy_exactly_and_repeat_is_refused(self):
        if not os.getenv('METEA_TEST_POSTGRES_URL'):
            self.skipTest('METEA_TEST_POSTGRES_URL is not configured')
        from tools.migrate_to_postgres import migrate
        from database.postgres import PostgresConnection
        from psycopg import sql
        schema = 'metea_test_' + uuid.uuid4().hex
        url = os.environ['METEA_TEST_POSTGRES_URL']
        with patch.dict(os.environ, {'METEA_DATABASE_BACKEND': 'sqlite', 'METEA_POSTGRES_URL': url}):
            fixture = isolation_tests.UserDataIsolationTest()
            fixture.setUp()
            try:
                source = Path(os.environ['METEA_DATABASE_PATH'])
                import sqlite3
                with sqlite3.connect(source) as legacy:
                    legacy.execute('UPDATE user_jobs SET source_text=?, train_commute_minutes=?', ('PDF\x00原文', '35'))
                    legacy.execute('UPDATE user_job_sources SET source_text=?', ('@metea:base64:v1:literal',))
                preview = migrate(source, schema, False)
                result = migrate(source, schema, True)
                self.assertEqual(preview['tables'], result['tables'])
                self.assertEqual(len(result['tables']), 25)
                from tools.backup_postgres import backup
                archived = source.parent / 'postgres-backup.db'
                self.assertEqual(backup(archived, schema), result['tables'])
                with self.assertRaises(RuntimeError):
                    migrate(source, schema, True)
                c = PostgresConnection(url)
                try:
                    self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0], 2)
                    new_id = c.execute("INSERT INTO users(email) VALUES (?)", ('third@example.com',)).lastrowid
                    self.assertGreater(new_id, 2)
                    c.rollback()
                finally:
                    c.close()
            finally:
                fixture.doCleanups()
                c = PostgresConnection(url)
                try:
                    assert re.fullmatch(r'metea_test_[a-f0-9]{32}', schema)
                    c.raw.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))
                    c.commit()
                finally:
                    c.close()


import test_operator as operator_tests


class PostgresOperatorTest(PostgresFixture, operator_tests.OperatorTest):
    pass
