"""既存の内部リンクを同じStreamlitセッション内で遷移させる。"""
from pathlib import Path
from urllib.parse import parse_qsl
import streamlit as st
from streamlit.components.v2 import component
from ui.page_execution import PENDING_PAGE_KEY

PAGES = frozenset(('home announcements application_dashboard application_detail selection_preparation basic_info hope_conditions job_hunting_axis work_values career profile_review self_discovery job_change_reason job_registration job_list job_detail job_comparison application_list milestones activity_history settings operator help logout privacy').split())
KEY = 'metea_navigation_bridge'


def parse_navigation(search):
    if not isinstance(search, str) or len(search) > 2048 or not search.startswith('?'):
        return None
    pairs = parse_qsl(search[1:], keep_blank_values=True)
    if len(pairs) > 20 or any(len(k) > 50 or len(v) > 512 for k, v in pairs):
        return None
    params = dict(pairs)
    page = params.get('page', 'home')
    if page not in PAGES:
        return None
    params['page'] = page
    return params


def _on_navigate():
    event = st.session_state.get(KEY, {})
    params = parse_navigation(event.get('navigate'))
    if params is not None:
        st.query_params.from_dict(params)
        st.session_state[PENDING_PAGE_KEY] = params['page']


_bridge = component('metea_navigation', js=Path(__file__).with_suffix('.js').read_text(encoding='utf-8'))


def install_navigation():
    # callbackはページ本体・認証処理の再実行前に遷移先だけを設定する。
    _bridge(key=KEY, data={'pages': sorted(PAGES)}, on_navigate_change=_on_navigate, height=0)
