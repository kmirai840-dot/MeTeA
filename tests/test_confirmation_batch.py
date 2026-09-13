from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import unittest
import test_confirmation_results as existing
from services import job_confirmation_service as service
from services.current_user_service import user_scope


class ConfirmationBatchTest(unittest.TestCase):
    setUp = existing.ConfirmationResultsTest.setUp
    def test_batch_atomic_and_invalidate_once(self):
        changes = [dict(item_name='転勤条件',item_reason='',result_text='転勤なし'), dict(item_name='残業時間',item_reason='',result_text='月10時間')]
        with user_scope(1), patch.object(service, '_invalidate_confirmation', side_effect=RuntimeError('fail')):
            with self.assertRaises(RuntimeError): service.save_confirmation_batch(10, changes)
            self.assertEqual(service.load_confirmation_records(10), [])
        with user_scope(1), patch.object(service, '_invalidate_confirmation') as invalidate:
            self.assertEqual(service.save_confirmation_batch(10, changes), 2)
            invalidate.assert_called_once()
            self.assertEqual(service.save_confirmation_batch(10, changes), 0)
            self.assertEqual(invalidate.call_count, 1)
            self.assertEqual(len(service.load_confirmation_records(10)), 2)
            with self.assertRaises(Exception): service.save_confirmation_batch(11, changes)

    def test_batch_form_single_submit_skips_blank_preserves_after_save(self):
        script = '''from ui.job_confirmation_results import render_batch_confirmation_form
items=[dict(item_key='a',item_name='転勤条件',reason=''),dict(item_key='b',item_name='残業時間',reason=''),dict(item_key='c',item_name='夜勤',reason='')]
render_batch_confirmation_form(10,items,[],[],lambda:None)
'''
        with patch.object(service, 'save_confirmation_decisions', return_value=2) as save, patch('ui.job_evaluation_area.refresh_saved_confirmation_details') as notify:
            app=AppTest.from_string(script, default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.button),1)
            app.selectbox[0].select('転勤なし')
            app.number_input[0].set_value(10)
            save.assert_not_called()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(save.call_args.args[1]),3)
            self.assertEqual(app.number_input[0].value,10)
            notify.assert_called_once_with(10, 2)

    def test_invalid_batch_does_not_save_any(self):
        script = '''from ui.job_confirmation_results import render_batch_confirmation_form
render_batch_confirmation_form(10,[dict(item_key='a',item_name='転勤条件',reason=''),dict(item_key='b',item_name='夜勤',reason='')],[],[],lambda:None)
'''
        with patch.object(service, 'save_confirmation_decisions') as save:
            app=AppTest.from_string(script, default_timeout=30).run()
            app.selectbox[0].select('転勤なし')
            app.selectbox[2].select('その他（補足に記載）')
            app.button[0].click().run()
            self.assertTrue(app.error)
            save.assert_not_called()

    def test_public_company_items_have_selectors_in_single_form(self):
        script = """from ui.job_confirmation_results import render_batch_confirmation_form
names=['土曜日','服装・髪型自由','未経験・第二新卒歓迎','老舗・安定企業','独自項目']
render_batch_confirmation_form(10,[dict(item_key=str(n),item_name=name,reason='') for n,name in enumerate(names)],[],[],lambda:None)
"""
        app=AppTest.from_string(script, default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.selectbox),10)
        self.assertEqual(len(app.button),1)
        self.assertTrue(all(field.value is None for field in app.selectbox[::2]))
