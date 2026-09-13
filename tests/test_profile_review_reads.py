import unittest
from streamlit.testing.v1 import AppTest
import test_user_data_isolation as fixtures


class ProfileReviewReadTest(unittest.TestCase):
    setUp = fixtures.UserDataIsolationTest.setUp

    def test_all_review_categories_render_with_scoped_snapshot(self):
        script = '''
import streamlit as st
st.session_state['metea_current_user_id'] = 1
from pages.profile_review import show_page
show_page()
'''
        for category in ('', 'basic', 'hope', 'values', 'axis', 'career'):
            with self.subTest(category=category):
                app = AppTest.from_string(script, default_timeout=30)
                if category:
                    app.query_params['category'] = category
                app.run()
                self.assertFalse(app.exception)
