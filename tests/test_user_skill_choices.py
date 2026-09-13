import unittest
from unittest.mock import patch
from services.user_skill_choices import format_skill_choices, parse_skill_choices


class SkillChoicesTest(unittest.TestCase):
    def test_round_trip_and_legacy_preservation(self):
        notes = "独学で習得\nその他：社内ツール"
        text = format_skill_choices(["Excel：VLOOKUP"], ["Excel：ピボットテーブル"], notes)
        self.assertEqual(parse_skill_choices(text), (["Excel：VLOOKUP"], ["Excel：ピボットテーブル"], notes))
        self.assertEqual(parse_skill_choices(notes), ([], [], notes))
        self.assertEqual(format_skill_choices([], [], ""), "")
        self.assertEqual(format_skill_choices(["Excel：VLOOKUP", "Excel：IF"], [], ""), format_skill_choices(["Excel：IF", "Excel：VLOOKUP"], [], ""))

    def test_form_restores_choices_and_saves_experience_separately(self):
        from streamlit.testing.v1 import AppTest
        from ui import user_skills
        initial = format_skill_choices(["Excel：VLOOKUP"], [], "以前の文章")
        with patch.object(user_skills, "load_skills", return_value=initial), patch.object(user_skills, "save_skills", return_value=True) as save:
            app = AppTest.from_string("from ui.user_skills import render_user_skills\nrender_user_skills()").run()
            self.assertEqual(app.multiselect[0].value, ["Excel：VLOOKUP"])
            self.assertEqual(app.text_area[0].value, "以前の文章")
            app.multiselect[1].select("Excel：ピボットテーブル")
            save.assert_not_called()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(parse_skill_choices(save.call_args.args[0]), (["Excel：VLOOKUP"], ["Excel：ピボットテーブル"], "以前の文章"))
