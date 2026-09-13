"""publicと分離した一時スキーマで実際の保存・更新を検証する。"""
import os
import unittest
from unittest.mock import patch
from test_postgres_integration import PostgresFixture
from services.current_user_service import user_scope
from services.user_skill_service import save_skills, load_skills
from database.connection import get_connection
from database.access_control import DataAccessDenied
from database.repositories.user_skill_repository import get_user_skills, save_user_skills


class PostgresUserSkillsTest(PostgresFixture, unittest.TestCase):
    def test_insert_update_restore_and_isolation(self):
        with patch.dict(os.environ, {"METEA_AUTH_MODE": "legacy"}):
            c = get_connection()
            try:
                c.execute("INSERT INTO users(id) VALUES (2)")
                c.commit()
            finally:
                c.close()
            with user_scope(1):
                self.assertTrue(save_skills("Excel関数"))
                self.assertEqual(load_skills(), "Excel関数")
                self.assertTrue(save_skills("Excel関数、Python"))
                self.assertEqual(load_skills(), "Excel関数、Python")
                self.assertFalse(save_skills("Excel関数、Python"))
                with self.assertRaises(DataAccessDenied):
                    save_user_skills(2, "overwrite")
            with user_scope(2):
                self.assertEqual(load_skills(), "")
                with self.assertRaises(DataAccessDenied):
                    get_user_skills(1)
