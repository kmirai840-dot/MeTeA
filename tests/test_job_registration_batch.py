from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

SCRIPT = """import streamlit as st
from pages.job_registration import render_job_form, start_new_job_registration
if 'initialized' not in st.session_state:
    start_new_job_registration()
    st.session_state['initialized']=True
if st.session_state.get('job_form_step') != 'confirm':
    render_job_form()
"""

class JobRegistrationBatchTest(TestCase):
    def setUp(self):
        visibility=patch('ui.job_form_visibility.install_job_form_visibility')
        visibility.start()
        self.addCleanup(visibility.stop)

    def test_fields_batch_and_optional_values_ignored_when_unchecked(self):
        app=AppTest.from_string(SCRIPT,default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('form')),1)
        self.assertEqual(len(app.button),2)
        app.text_input(key='job_form_company_name').set_value('テスト企業')
        app.text_input(key='job_form_source_name').set_value('紹介会社')
        app.text_area(key='job_form_job_summary').set_value('テスト業務')
        # 全欄はフォーム内に存在し、未入力時の検証は送信後に実施。
        self.assertFalse(app.error)
        app.button(key='job_form_save').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input(key='job_form_company_name').value,'テスト企業')

    def test_submit_includes_conditional_values_and_keeps_unchecked_unknown(self):
        app=AppTest.from_string(SCRIPT,default_timeout=30).run()
        app.text_input(key='job_form_company_name').set_value('テスト企業')
        app.text_input(key='job_form_source_name').set_value('紹介会社')
        app.selectbox(key='job_form_source_type').select(app.selectbox(key='job_form_source_type').options[1])
        app.text_input(key='job_form_occupation').set_value('営業')
        app.text_area(key='job_form_job_summary').set_value('テスト業務')
        app.checkbox(key='job_form_has_overtime').check()
        app.number_input(key='job_form_overtime_value').set_value(12)
        app.selectbox(key='job_form_fixed_overtime_system').select('あり')
        app.number_input(key='job_form_fixed_overtime_hours').set_value(20)
        app.text_input(key='job_form_fixed_overtime_pay_min').set_value('40,000')
        app.button(key='job_form_save').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['job_form_step'],'confirm')
        job=app.session_state['job_confirm_data']
        self.assertEqual(str(job.overtime),'12')
        self.assertEqual(str(job.fixed_overtime_hours),'20')
        self.assertEqual(str(job.fixed_overtime_pay_min),'40000')
        self.assertIn(job.break_minutes,('',None))
