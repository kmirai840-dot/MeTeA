import unittest
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from pages import job_registration as page

class MethodCardsTest(unittest.TestCase):
    def test_select_hides_cards_and_change_preserves_input(self):
        for mode in ('pdf','text','url'):
            with self.subTest(mode=mode):
                def render_input(): st.text_input('Test input',key='test_source_input')
                with patch.object(page,'render_pdf_registration',side_effect=render_input), patch.object(page,'render_text_registration',side_effect=render_input), patch.object(page,'render_url_registration',side_effect=render_input):
                    app=AppTest.from_string('from pages.job_registration import render_method_selection\nrender_method_selection()').run()
                    app.button(key='select_job_'+mode).click().run()
                    self.assertFalse(app.exception)
                    self.assertFalse(any(b.key=='select_job_pdf' for b in app.button))
                    app.text_input(key='test_source_input').input('keep input').run()
                    app.button(key='change_job_registration_method').click().run()
                    self.assertTrue(any(b.key=='select_job_pdf' for b in app.button))
                    self.assertEqual(app.text_input(key='test_source_input').value,'keep input')
                    app.button(key='select_job_'+mode).click().run()
                    self.assertFalse(any(b.key=='select_job_pdf' for b in app.button))
                    self.assertEqual(app.text_input(key='test_source_input').value,'keep input')
                    self.assertFalse(app.exception)

    def test_manual_keeps_existing_form_transition(self):
        app=AppTest.from_string('from pages import job_registration as p\nif p.st.session_state.get(p.JOB_FORM_STEP_KEY)=="form": p.st.title("form")\nelse: p.render_method_selection()').run()
        app.button(key='select_job_manual').click().run()
        self.assertEqual(app.title[0].value,'form')
        self.assertFalse(app.exception)
