import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from services.current_user_service import user_scope
from database.initialize import initialize_database
from database.connection import get_connection
from database.access_control import DataAccessDenied
from database.repositories.user_skill_repository import get_user_skills, save_user_skills
from services.user_skill_service import load_skills, save_skills


class UserSkillsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {"METEA_DATABASE_BACKEND": "sqlite", "METEA_DATABASE_PATH": str(Path(tmp.name)/"test.db"), "METEA_AUTH_MODE": "legacy"})
        env.start()
        self.addCleanup(env.stop)
        initialize_database()
        db = get_connection()
        db.execute("INSERT INTO users(id) VALUES (2)")
        db.commit()
        db.close()

    def test_persistence_isolation_and_change_only_invalidation(self):
        with patch("services.user_skill_service.invalidate_current_user_job_evaluations") as invalidate:
            with user_scope(1):
                self.assertEqual(load_skills(), "")
                self.assertTrue(save_skills("Excel SUMIF：講座で学習"))
                self.assertFalse(save_skills("Excel SUMIF：講座で学習"))
                self.assertEqual(load_skills(), "Excel SUMIF：講座で学習")
                with self.assertRaises(DataAccessDenied): get_user_skills(2)
                with self.assertRaises(DataAccessDenied): save_user_skills(2, "overwrite")
            with user_scope(2): self.assertEqual(load_skills(), "")
            invalidate.assert_called_once()
            with user_scope(1):
                self.assertTrue(save_skills(""))
                self.assertEqual(load_skills(), "")

    def test_form_and_ai_context(self):
        from streamlit.testing.v1 import AppTest
        from ui import user_skills
        with patch.object(user_skills, "load_skills", return_value="Excel"), patch.object(user_skills, "save_skills", return_value=True) as save:
            app = AppTest.from_string("from ui.user_skills import render_user_skills\nrender_user_skills()").run()
            app.text_area[0].input("Excel VLOOKUP：独学").run()
            save.assert_not_called()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            save.assert_called_once_with("Excel VLOOKUP：独学")
        from models import Job
        from services.job_matching_context_service import build_ai_matching_context
        kwargs = dict(job=Job(), hope_condition=None, hope_items=[], work_value_rankings=[], work_value_details=[], work_style_answers=[], job_hunting_axes=[], careers=[])
        context = build_ai_matching_context(**kwargs, user_skills="Excel VLOOKUP：独学")
        self.assertEqual(context["user_matching_information"]["self_reported_tools_and_skills"], "Excel VLOOKUP：独学")
        self.assertNotIn("self_reported_tools_and_skills", build_ai_matching_context(**kwargs).get("user_matching_information", {}))
