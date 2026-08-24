"""ローカル実行とStreamlit Cloudで共通利用する実行時設定。"""

from __future__ import annotations

import hmac
import os

import streamlit as st
from dotenv import load_dotenv


SECRET_KEYS = (
    "OPENAI_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "APP_PASSWORD",
    "APP_ENV",
    "METEA_DATABASE_PATH",
)


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
            st.session_state["app_authenticated"] = True
            st.rerun()

        st.error("パスワードが正しくありません。")

    st.stop()
