"""現在操作中の利用者を一元管理する。

認証機能を導入するまでは、既存データの所有者である利用者ID 1を既定値とする。
認証完了後は ``set_current_user_id`` を呼ぶだけで、画面・サービスが参照する
利用者を切り替えられる。
"""
from __future__ import annotations

import os
from typing import Any
from contextlib import contextmanager
from contextvars import ContextVar


CURRENT_USER_SESSION_KEY = "metea_current_user_id"
DEFAULT_USER_ID = 1
_background_user_id: ContextVar[int | None] = ContextVar("metea_background_user_id", default=None)


class UserIdentityRequired(PermissionError):
    """認証必須モードで本人を特定できない。"""


def _normalize_user_id(value: Any) -> int:
    if isinstance(value, bool) or not str(value).isdigit():
        raise ValueError("利用者IDは正の整数である必要があります。")
    user_id = int(value)
    if user_id <= 0:
        raise ValueError("利用者IDは1以上である必要があります。")
    return user_id


def _configured_default_user_id() -> int:
    configured = os.getenv("METEA_DEFAULT_USER_ID", "").strip()
    if not configured:
        return DEFAULT_USER_ID
    return _normalize_user_id(configured)


def _streamlit_session_state():
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx(suppress_warning=True) is None:
            return None
        return st.session_state
    except (ImportError, RuntimeError):
        return None


def get_current_user_id() -> int:
    """現在の利用者IDを返す。認証導入前は既存利用者ID 1を使用する。"""
    background_user = _background_user_id.get()
    if background_user is not None:
        return background_user
    session_state = _streamlit_session_state()
    current = session_state.get(CURRENT_USER_SESSION_KEY) if session_state is not None else None
    if current is not None:
        return _normalize_user_id(current)
    if (os.getenv("METEA_AUTH_MODE", "").strip().lower() == "google"
            or os.getenv("METEA_REQUIRE_AUTH", "").strip().lower() in {"1", "true", "yes"}):
        raise UserIdentityRequired("ログインが必要です。")
    # 個別ログイン導入までの既存ローカル・デモ互換。セッションには固定しない。
    return _configured_default_user_id()


def set_current_user_id(user_id: int) -> None:
    """認証済み利用者を現在のStreamlitセッションへ設定する。"""
    normalized = _normalize_user_id(user_id)
    session_state = _streamlit_session_state()
    if session_state is None:
        raise RuntimeError("Streamlitセッション外では利用者を変更できません。")
    if session_state.get(CURRENT_USER_SESSION_KEY) != normalized:
        # 前の利用者のフォーム、選択中ID、下書き等を持ち越さない。
        authenticated = session_state.get("app_authenticated")
        session_state.clear()
        if authenticated is not None:
            session_state["app_authenticated"] = authenticated
    session_state[CURRENT_USER_SESSION_KEY] = normalized


def clear_current_user_id() -> None:
    """ログアウト時などに現在の利用者IDをセッションから除去する。"""
    session_state = _streamlit_session_state()
    if session_state is not None:
        session_state.clear()


@contextmanager
def user_scope(user_id: int):
    """信頼されたサーバー処理へ本人IDを渡す。ブラウザ入力からは呼ばない。

    ThreadPoolExecutorではStreamlitのセッションを参照できないため、投入時の
    本人IDを明示的に設定する。終了・例外時とも元のコンテキストへ戻す。
    """
    token = _background_user_id.set(_normalize_user_id(user_id))
    try:
        yield
    finally:
        _background_user_id.reset(token)
