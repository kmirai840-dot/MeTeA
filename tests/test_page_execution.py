"""保存後の遷移が古いURLや別利用者へ持ち越されないことを検証する。"""
import unittest
from streamlit.testing.v1 import AppTest


class PageExecutionTest(unittest.TestCase):
    def test_delayed_old_url_does_not_cancel_committed_navigation(self):
        app = AppTest.from_string('''
import streamlit as st
from ui.page_execution import navigate_to_page, resolve_current_page, PENDING_PAGE_KEY
# URL更新後に古いクライアント状態が遅れて届く状況を再現。
if PENDING_PAGE_KEY in st.session_state:
    st.query_params['page'] = 'basic_info'
page = resolve_current_page()
st.text(page)
if page == 'hope_conditions':
    if st.button('戻る'):
        navigate_to_page('basic_info')
else:
    if st.button('保存して次へ'):
        st.session_state['save_count'] = st.session_state.get('save_count', 0) + 1
        navigate_to_page('hope_conditions')
''').run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text[0].value, 'hope_conditions')
        self.assertEqual(app.session_state['save_count'], 1)
        self.assertEqual(app.query_params['page'], ['hope_conditions'])
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text[0].value, 'basic_info')
        self.assertEqual(app.session_state['save_count'], 1)

    def test_user_switch_clears_pending_navigation(self):
        app = AppTest.from_string('''
import streamlit as st
from services.current_user_service import set_current_user_id
from ui.page_execution import PENDING_PAGE_KEY, resolve_current_page
set_current_user_id(2)
st.session_state[PENDING_PAGE_KEY] = 'career'
set_current_user_id(3)
st.text(resolve_current_page())
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text[0].value, 'home')

if __name__ == '__main__':
    unittest.main()
