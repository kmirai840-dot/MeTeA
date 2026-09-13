"""フォーム送信と認証再確認の間で失敗しても入力を保持する。"""
import os
import unittest
from datetime import date
from unittest.mock import patch

from models import BasicInfo
from services import current_user_service as identity
from pages import basic_info as page

PROFILE = BasicInfo(family_name="旧姓", given_name="名前", gender="female", birth_date=date(1994,9,16), prefecture="福岡県", municipality="福岡市", nearest_station="駅", nearest_station_place_id="station-test")

class InputRecoveryTest(unittest.TestCase):
    def test_suspension_denies_access_and_only_same_user_restores(self):
        state = {identity.CURRENT_USER_SESSION_KEY: 2, page.INPUT_SNAPSHOT_KEY: {"name":"private"}}
        with patch.object(identity, "_streamlit_session_state", return_value=state), patch.dict(os.environ, {"METEA_REQUIRE_AUTH":"true"}):
            identity.suspend_current_user_id()
            with self.assertRaises(identity.UserIdentityRequired): identity.get_current_user_id()
            identity.set_current_user_id(2)
            self.assertIn(page.INPUT_SNAPSHOT_KEY, state)
            identity.suspend_current_user_id()
            identity.set_current_user_id(3)
            self.assertNotIn(page.INPUT_SNAPSHOT_KEY, state)
            identity.clear_current_user_id()
            self.assertEqual(state,{})

    def test_submit_recovers_after_auth_stop_without_old_db_values(self):
        from streamlit.testing.v1 import AppTest
        source = """
import streamlit as st
from pages import basic_info as p
from services.current_user_service import set_current_user_id, suspend_current_user_id
if p.INPUT_SNAPSHOT_KEY in st.session_state and not st.session_state.get('failure_tested'):
    suspend_current_user_id()
    st.session_state['failure_tested'] = True
    st.button('再試行')
    st.stop()
set_current_user_id(2)
p.render_basic_info_page.__wrapped__()
"""
        with patch.object(page, 'format_station_candidate', side_effect=lambda value: value), patch.object(page, 'load_basic_info_draft', return_value=None), patch.object(page, 'load_basic_info', return_value=PROFILE), patch.object(page, 'save_basic_info_draft') as draft, patch.object(page, 'save_basic_info') as save:
            app = AppTest.from_string(source).run(timeout=20)
            self.assertFalse(app.exception)
            app.text_input(key=page.FAMILY_NAME_KEY).set_value('変更した姓')
            app.button(key='basic_next').click().run(timeout=20)
            self.assertFalse(app.exception)
            save.assert_not_called()
            self.assertEqual(app.session_state[page.INPUT_SNAPSHOT_KEY][page.FAMILY_NAME_KEY], '変更した姓')
            app.button[0].click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key=page.FAMILY_NAME_KEY).value, '変更した姓')
            app.button(key='basic_next').click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(save.call_args.args[0].family_name, '変更した姓')
            self.assertEqual(app.query_params['page'], ['hope_conditions'])

    def test_draft_failure_keeps_form_and_does_not_advance(self):
        from streamlit.testing.v1 import AppTest
        with patch.object(page, 'format_station_candidate', side_effect=lambda value: value), patch.object(page, 'load_basic_info_draft', return_value=None), patch.object(page, 'load_basic_info', return_value=PROFILE), patch.object(page, 'save_basic_info_draft', side_effect=ConnectionError('test')), patch.object(page, 'save_basic_info') as save:
            app = AppTest.from_string('from pages.basic_info import render_basic_info_page\nrender_basic_info_page()').run(timeout=20)
            app.text_input(key=page.FAMILY_NAME_KEY).set_value('残す姓')
            app.button(key='basic_next').click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key=page.FAMILY_NAME_KEY).value,'残す姓')
            self.assertTrue(any("下書きを保存できませんでした" in element.value for element in app.markdown))
            save.assert_not_called()
            self.assertNotIn('page',app.query_params)

if __name__ == '__main__': unittest.main()
