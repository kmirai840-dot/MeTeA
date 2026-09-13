import unittest
from unittest.mock import patch
from services.user_skill_choices import format_skill_choices, parse_skill_choices


class SkillChoicesTest(unittest.TestCase):
    def test_old_excel_details_are_preserved_without_inventing_skills(self):
        old = "【選択したスキル】\n仕事で使用：Excel：VLOOKUP／Excel：IF\n学習・個人活動で使用：Excel：ピボットテーブル\n補足：元のメモ"
        work, learning, notes = parse_skill_choices(old)
        self.assertEqual(work, ["Excel関数"])
        self.assertEqual(learning, [])
        self.assertIn("Excel：VLOOKUP", notes)
        self.assertIn("Excel：ピボットテーブル", notes)
        self.assertIn("元のメモ", notes)
        self.assertEqual(parse_skill_choices(format_skill_choices(work, learning, notes)), (work, learning, notes))

    def test_requested_languages_can_be_saved_and_restored(self):
        values = ["Python：プログラミング", "SQL：データ抽出・集計", "Java：プログラミング", "Excel VBA", "GAS（Google Apps Script）：自動化・スクリプト作成"]
        work, learning, notes = parse_skill_choices(format_skill_choices(values, [], ""))
        self.assertEqual(set(work), set(values))
        self.assertEqual(learning, [])

    def test_round_trip_and_legacy_preservation(self):
        notes = "独学で習得\nその他：社内ツール"
        text = format_skill_choices(["Excel関数"], ["Excel入力"], notes)
        self.assertEqual(parse_skill_choices(text), (["Excel関数"], ["Excel入力"], notes))
        self.assertEqual(parse_skill_choices(notes), ([], [], notes))
        self.assertEqual(format_skill_choices([], [], ""), "")
        self.assertEqual(format_skill_choices(["Excel関数", "Excel VBA"], [], ""), format_skill_choices(["Excel VBA", "Excel関数"], [], ""))

    def test_form_restores_choices_and_saves_experience_separately(self):
        from streamlit.testing.v1 import AppTest
        from ui import user_skills
        initial = format_skill_choices(["Excel関数"], [], "以前の文章")
        with patch.object(user_skills, "load_skills", return_value=initial), patch.object(user_skills, "save_skills", return_value=True) as save:
            app = AppTest.from_string("from ui.user_skills import render_user_skills\nrender_user_skills()").run()
            self.assertEqual(app.multiselect[0].value, ["Excel関数"])
            self.assertEqual(app.text_area[0].value, "以前の文章")
            app.multiselect[1].select("Excel入力")
            save.assert_not_called()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(parse_skill_choices(save.call_args.args[0]), (["Excel関数"], ["Excel入力"], "以前の文章"))
