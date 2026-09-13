from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

SCRIPT = """import streamlit as st
from pages.job_detail import _render_application_decision_content
st.session_state['runs'] = st.session_state.get('runs',0)+1
_render_application_decision_content(10, {'decisions': {}})
"""

class DecisionFeedbackTest(TestCase):
    def test_success_updates_status_and_stays_visible_without_extra_rerun(self):
        with patch('pages.job_detail.save_job_application_decision_data',return_value=[]) as save:
            app=AppTest.from_string(SCRIPT,default_timeout=30).run()
            app.radio[0].set_value('応募しない')
            app.button[1].click().run()
            self.assertFalse(app.exception)
            save.assert_called_once()
            self.assertIn('保存しました',app.success[0].value)
            self.assertIn('応募しない',app.info[0].value)
            self.assertEqual(app.session_state['runs'],2)

    def test_validation_failure_does_not_show_success(self):
        with patch('pages.job_detail.save_job_application_decision_data',return_value=['応募判断を選択してください。']):
            app=AppTest.from_string(SCRIPT,default_timeout=30).run()
            app.button[1].click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.success)
            self.assertTrue(app.error)
