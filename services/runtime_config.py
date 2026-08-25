"""ローカル実行とStreamlit Cloudで共通利用する実行時設定。"""

from __future__ import annotations

import hmac
import hashlib
import os
from datetime import datetime, timedelta

import extra_streamlit_components as stx
import streamlit as st
from dotenv import load_dotenv
from extra_streamlit_components.CookieManager import (
    _component_func as _cookie_component,
)


SECRET_KEYS = (
    "OPENAI_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "APP_PASSWORD",
    "APP_ENV",
    "METEA_DATABASE_PATH",
)

AUTH_COOKIE_NAME = "metea_demo_auth"
AUTH_COOKIE_LIFETIME_HOURS = 12


def _authentication_token(password: str) -> str:
    """パスワードを保存せず、ブラウザ認証確認用の署名を作る。"""

    return hmac.new(
        password.encode("utf-8"),
        b"metea-demo-browser-auth-v1",
        hashlib.sha256,
    ).hexdigest()


def _cookie_manager() -> stx.CookieManager:
    """全画面で同じキーを使うCookie管理部品を返す。"""

    return stx.CookieManager(key="metea_demo_cookie_manager")


def _read_browser_cookies() -> dict[str, str] | None:
    """Cookie部品の読込完了後だけCookie一覧を返す。"""

    cookies = _cookie_component(
        method="getAll",
        key="metea_demo_cookie_probe",
        default=None,
    )
    if cookies is None:
        return None
    return dict(cookies)


def configure_runtime_secrets() -> None:
    """`.env`またはStreamlit Secretsから実行時設定を読み込む。"""

    load_dotenv()

    for key in SECRET_KEYS:
        if os.getenv(key, "").strip():
            continue

        try:
            value = str(st.secrets.get(key, "")).strip()
        except (FileNotFoundError, KeyError):
            value = ""

        if value:
            os.environ[key] = value


def is_demo_environment() -> bool:
    """公開デモ環境として起動しているかを返す。"""

    return os.getenv("APP_ENV", "").strip().lower() == "demo"


def require_app_password() -> None:
    """公開環境にパスワードが設定されている場合だけ認証を求める。"""

    expected_password = os.getenv("APP_PASSWORD", "").strip()

    if not expected_password:
        return

    if st.session_state.get("app_authenticated") is True:
        return

    expected_token = _authentication_token(expected_password)
    browser_cookies = _read_browser_cookies()
    if browser_cookies is None:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] { display: none; }
            .stApp { background: #f5f8fc; }
            .block-container {
                max-width: 560px;
                padding-top: 12vh;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.info("認証情報を確認しています。")
        st.stop()

    saved_token = str(browser_cookies.get(AUTH_COOKIE_NAME) or "")
    if saved_token and hmac.compare_digest(saved_token, expected_token):
        st.session_state["app_authenticated"] = True
        return

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: #f5f8fc; }
        .block-container {
            max-width: 560px;
            padding-top: 12vh;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("MeTeA デモ")
    st.write("共有された閲覧用パスワードを入力してください。")

    with st.form("app_password_form", clear_on_submit=False):
        entered_password = st.text_input(
            "パスワード",
            type="password",
            autocomplete="current-password",
        )
        submitted = st.form_submit_button(
            "デモを開く",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if hmac.compare_digest(entered_password, expected_password):
            cookie_manager = _cookie_manager()
            cookie_manager.set(
                AUTH_COOKIE_NAME,
                expected_token,
                key="metea_demo_auth_cookie_set",
                path="/",
                expires_at=datetime.now() + timedelta(hours=AUTH_COOKIE_LIFETIME_HOURS),
                secure=is_demo_environment(),
                same_site="strict",
            )
            st.session_state["app_authenticated"] = True
            st.rerun()

        st.error("パスワードが正しくありません。")

    st.stop()


def clear_app_authentication() -> None:
    """ブラウザとStreamlitセッションのデモ認証情報を削除する。"""

    st.session_state.pop("app_authenticated", None)
    _cookie_manager().delete(
        AUTH_COOKIE_NAME,
        key="metea_demo_auth_cookie_delete",
        path="/",
    )
