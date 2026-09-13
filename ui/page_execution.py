"""入力中の部分更新と、保存後のページ遷移を分けて扱う。"""
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

PENDING_PAGE_KEY = "metea_pending_page"


def rerun_current_page() -> None:
    """fragment実行中だけ部分更新し、初回の全体実行にも対応する。"""
    ctx = get_script_run_ctx()
    scope = "fragment" if ctx and ctx.fragment_ids_this_run else "app"
    st.rerun(scope=scope)


def navigate_to_page(page: str) -> None:
    """保存後の遷移先をサーバーにも保持し、全体ルーターへ渡す。"""
    st.session_state[PENDING_PAGE_KEY] = page
    st.query_params["page"] = page
    st.rerun()


def resolve_current_page() -> str:
    """直前に確定した遷移を、遅れて届いた古いURLより優先する。"""
    pending = st.session_state.get(PENDING_PAGE_KEY)
    if pending is not None:
        st.query_params["page"] = pending
        del st.session_state[PENDING_PAGE_KEY]
        return pending
    return st.query_params.get("page", "home")


def request_save(form: str) -> None:
    st.session_state[f"metea_save_requested_{form}"] = True


def take_save_request(form: str) -> bool:
    return st.session_state.pop(f"metea_save_requested_{form}", False)


def defer_save_failure(form: str, label: str, *, recovery: str) -> None:
    st.session_state[f"metea_save_failure_{form}"] = (label, recovery)


def render_deferred_save_failure(form: str) -> None:
    from ui.design_system import render_save_failure
    failure = st.session_state.pop(f"metea_save_failure_{form}", None)
    if failure:
        render_save_failure(failure[0], recovery=failure[1])
