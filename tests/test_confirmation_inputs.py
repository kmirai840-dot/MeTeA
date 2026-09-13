import unittest
from datetime import time
from unittest.mock import patch
from services.confirmation_input_service import format_input, restore_input, OTHER


class ConfirmationInputsTest(unittest.TestCase):
    def test_choice_numeric_time_round_trip(self):
        for name, value in [('転勤条件', '転勤なし'), ('残業時間', 0), ('年間休日数', 125), ('始業時刻', time(9, 30))]:
            with self.subTest(name=name):
                text = format_input(name, value, '担当者へ確認')
                self.assertEqual(restore_input(name, text), (value, '担当者へ確認'))

    def test_legacy_text_and_unknown_items_preserved(self):
        old = '全国転勤あり。ただし入社後3年間は免除。'
        value, notes = restore_input('転勤条件', old)
        self.assertEqual(value, OTHER)
        self.assertEqual(format_input('転勤条件', value, notes), old)
        self.assertEqual(format_input('企業文化', OTHER, old), old)
        self.assertEqual(restore_input('残業時間', old), (None, old))

    def test_blank_is_not_saved_as_no_or_zero(self):
        for name in ['転勤条件', '残業時間', '始業時刻']:
            self.assertEqual(restore_input(name, ''), (None, ''))
            with self.assertRaises(ValueError): format_input(name, None, '')
        with self.assertRaises(ValueError): format_input('年間休日数', 367, '')
        self.assertIn('確認できなかった', format_input('転勤条件', '確認できなかった', ''))

    def test_select_form_saves_once_and_restores_selection(self):
        from streamlit.testing.v1 import AppTest
        from ui import job_confirmation_results as ui
        with patch.object(ui, 'save_confirmation_result', return_value=True) as save:
            app = AppTest.from_string("from ui.job_confirmation_results import render_result_form\nrender_result_form(10,dict(item_key='k',item_name='転勤条件',item_reason='不明',result_text='転勤条件：転勤なし'))", default_timeout=10).run()
            self.assertEqual(app.selectbox[0].value, '転勤なし')
            app.selectbox[0].select('転勤あり').run()
            save.assert_not_called()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            save.assert_called_once_with(10, '転勤条件', '不明', '転勤条件：転勤あり')

    def test_number_and_time_widgets_start_empty(self):
        from streamlit.testing.v1 import AppTest
        for name, widget in [('残業時間', 'number_input'), ('始業時刻', 'time_input')]:
            app = AppTest.from_string(f"from ui.job_confirmation_results import render_result_form\nrender_result_form(10,dict(item_key='k',item_name='{name}',item_reason='不明'))", default_timeout=10).run()
            self.assertFalse(app.exception)
            self.assertIsNone(getattr(app, widget)[0].value)

    def test_public_item_names_use_choices_and_preserve_old_text(self):
        from services.confirmation_input_service import input_kind, choices_for, DETAIL
        for name in ['土曜日', '服装・髪型自由', '未経験・第二新卒歓迎', '老舗・安定企業', '独自の確認項目']:
            self.assertEqual(input_kind(name), 'choice')
            self.assertIsNone(restore_input(name, '')[0])
            old = '以前に確認した内容をそのまま保持'
            self.assertEqual(format_input(name, *restore_input(name, old)), old)
        for name, value in [('土曜日','毎週土曜日が休み'),('服装・髪型自由','服装・髪型ともに規定あり'),('未経験・第二新卒歓迎','実務経験が必要'),('老舗・安定企業','設立から10年未満')]:
            self.assertIn(value, choices_for(name))
            self.assertEqual(restore_input(name, format_input(name, value, '')), (value, ''))
        with self.assertRaises(ValueError): format_input('独自の確認項目', DETAIL, '')
        self.assertEqual(format_input('独自の確認項目', DETAIL, '確認した事実'), '確認した事実')
