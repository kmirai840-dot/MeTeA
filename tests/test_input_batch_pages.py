from unittest import TestCase
from unittest.mock import patch
from contextlib import ExitStack
from streamlit.testing.v1 import AppTest

class InputBatchPagesTest(TestCase):
    def setUp(self):
        self.stack=ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('ui.job_form_visibility.install_visibility'))
    def test_work_values_inputs_inside_form(self):
        self.stack.enter_context(patch('pages.work_values.load_work_values_draft',return_value={}))
        self.stack.enter_context(patch('pages.work_values.load_work_values_data',return_value=([],[],[])))
        app=AppTest.from_string('from pages.work_values import show_page; show_page()',default_timeout=45).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('form')),1)
        self.assertTrue(app.radio)
    def test_hope_dynamic_fields_and_legacy_draft_preserved(self):
        self.stack.enter_context(patch('pages.hope_conditions.load_hope_conditions_draft',return_value={'hope_prefectures':['福岡県'],'hope_city_1_福岡県':'福岡市','hope_location_priority_1_福岡県':'must'}))
        app=AppTest.from_string('from pages.hope_conditions import render_hope_conditions_page; render_hope_conditions_page()',default_timeout=45).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('form')),1)
        self.assertEqual(app.text_input(key='hope_city_福岡県').value,'福岡市')
        self.assertEqual(app.selectbox(key='hope_location_priority_福岡県').value,'must')

    def test_axis_add_form(self):
        self.stack.enter_context(patch('pages.job_hunting_axis.load_job_hunting_axis_draft',return_value={}))
        self.stack.enter_context(patch('pages.job_hunting_axis.load_job_hunting_axis_data',return_value=[]))
        self.stack.enter_context(patch('pages.job_hunting_axis.suggest_job_hunting_axes',return_value=[]))
        app=AppTest.from_string('from pages.job_hunting_axis import render_job_hunting_axis_page; render_job_hunting_axis_page()',default_timeout=45).run()
        self.assertFalse(app.exception)
        app.button(key='job_hunting_axis_show_add_form').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('form')),1)

    def test_career_manual_form(self):
        self.stack.enter_context(patch('pages.career.load_career_data',return_value=[]))
        self.stack.enter_context(patch('ui.user_skills.render_user_skills'))
        app=AppTest.from_string("import streamlit as st; from pages.career import show_page, CAREER_ENTRY_MODE_KEY; st.session_state[CAREER_ENTRY_MODE_KEY]='manual'; show_page()",default_timeout=45).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('form')),1)
        self.assertTrue(app.text_input)
