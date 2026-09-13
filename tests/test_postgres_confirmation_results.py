import os
import unittest
from unittest.mock import patch
from test_postgres_integration import PostgresFixture
from database.connection import get_connection
from database.confirmation_schema import ensure_confirmation_schema
from services.current_user_service import user_scope
from services.job_confirmation_service import save_confirmation_result, load_confirmation_records
from database.access_control import DataAccessDenied

class PostgresConfirmationTest(PostgresFixture, unittest.TestCase):
    def test_migration_save_update_and_isolation(self):
        with patch.dict(os.environ, {'METEA_AUTH_MODE':'legacy'}):
            c=get_connection()
            try:
                c.execute('INSERT INTO users(id) VALUES (2)')
                c.execute('INSERT INTO user_jobs(id,user_id) VALUES (10,1)')
                c.execute("INSERT INTO user_job_confirmation_resolutions(user_id,job_id,item_key,status) VALUES (1,10,'old','not_required')")
                c.execute('ALTER TABLE user_job_confirmation_resolutions DROP COLUMN result_text')
                ensure_confirmation_schema(c)
                ensure_confirmation_schema(c)
                c.commit()
            finally: c.close()
            with user_scope(1):
                self.assertEqual(load_confirmation_records(10)[0]['status'],'not_required')
                self.assertTrue(save_confirmation_result(10,'残業時間','不明','月10時間'))
                self.assertTrue(save_confirmation_result(10,'残業時間','不明','月20時間'))
                self.assertEqual(load_confirmation_records(10)[1]['result_text'],'月20時間')
            with user_scope(2):
                with self.assertRaises(DataAccessDenied): load_confirmation_records(10)
                with self.assertRaises(DataAccessDenied): save_confirmation_result(10,'残業時間','不明','改変')
