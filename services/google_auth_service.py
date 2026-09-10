"""Google OIDCで確認した本人と、招待済みの内部利用者を結び付ける。"""
from __future__ import annotations

import os
import hmac
import sqlite3
import psycopg
from collections.abc import Mapping
from urllib.parse import urlparse

from database.connection import get_connection, begin_account_registration


class LoginDenied(PermissionError):
    pass


class InvitationRequired(LoginDenied):
    pass


class LoginConfigurationError(ValueError):
    pass


GOOGLE_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"


def auth_mode() -> str:
    mode = os.getenv("METEA_AUTH_MODE", "").strip().lower()
    if not mode:
        mode = "google" if os.getenv("METEA_REQUIRE_AUTH", "").lower() in {"1", "true", "yes"} else "legacy"
    if mode not in {"google", "legacy"}:
        raise LoginConfigurationError("METEA_AUTH_MODEにはgoogleまたはlegacyを指定してください。")
    return mode


def allowed_emails(settings: Mapping) -> frozenset[str]:
    access = settings.get("access", {})
    raw = access.get("allowed_emails", []) if isinstance(access, Mapping) else None
    if not isinstance(raw, (list, tuple)) or any(
        not isinstance(value, str) or value.count("@") != 1 or any(c.isspace() for c in value.strip())
        or not all(value.strip().split("@")) for value in raw
    ):
        raise LoginConfigurationError("access.allowed_emailsをメールアドレスの配列で設定してください。")
    return frozenset(value.strip().casefold() for value in raw)


def access_invitations(settings: Mapping):
    access = settings.get("access", {})
    mode = access.get("registration_mode", "email_allowlist")
    if mode == "invite_code":
        code = access.get("invite_code", "")
        if not isinstance(code, str) or len(code) < 16:
            raise LoginConfigurationError("招待コードは16文字以上で設定してください。")
        return None  # 有効なGoogleアカウントの登録済みIDを継続利用する。
    if mode != "email_allowlist":
        raise LoginConfigurationError("利用者登録方式の設定を確認してください。")
    return allowed_emails(settings)


def validate_login_settings(settings: Mapping) -> frozenset[str]:
    auth = settings.get("auth", {})
    google = auth.get("google", {}) if isinstance(auth, Mapping) else {}
    if not isinstance(google, Mapping):
        raise LoginConfigurationError("Googleログインの設定が不足しています。")
    required = (auth.get("redirect_uri"), auth.get("cookie_secret"),
                google.get("client_id"), google.get("client_secret")) if isinstance(auth, Mapping) else ()
    if len(required) != 4 or any(not isinstance(v, str) or not v.strip() for v in required):
        raise LoginConfigurationError("Googleログインの設定が不足しています。")
    redirect = urlparse(auth["redirect_uri"])
    local = redirect.hostname in {"localhost", "127.0.0.1"}
    if (redirect.scheme != "https" and not (local and redirect.scheme == "http")) or not redirect.hostname or redirect.path != "/oauth2callback" or redirect.query or redirect.fragment or redirect.username:
        raise LoginConfigurationError("Googleログインの戻り先URLを確認してください。")
    if len(auth["cookie_secret"]) < 32 or google.get("server_metadata_url") != GOOGLE_METADATA_URL:
        raise LoginConfigurationError("GoogleログインのCookie設定・認証元を確認してください。")
    emails = access_invitations(settings)
    if emails is not None and not emails:
        raise LoginConfigurationError("招待するメールアドレスが未設定です。")
    return emails


def resolve_google_user(claims: Mapping, invitations: frozenset[str] | None, *, invitation_code=None) -> int:
    """Streamlit検証済みst.user専用。ブラウザ入力・未検証JWTからは呼ばない。"""
    email = claims.get("email")
    subject = claims.get("sub")
    if (claims.get("iss") not in {"https://accounts.google.com", "accounts.google.com"}
            or claims.get("email_verified") is not True
            or not isinstance(subject, str) or not subject.strip()
            or not isinstance(email, str)):
        raise LoginDenied("確認済みのGoogleアカウントでログインしてください。")
    email = email.strip().casefold()
    if invitations is not None and email not in invitations:
        raise LoginDenied("このアカウントはMeTeAの利用対象に登録されていません。")
    name = claims.get("name", "")
    picture = claims.get("picture", "")
    name = name[:256] if isinstance(name, str) else ""
    picture = picture[:2048] if isinstance(picture, str) else ""
    connection = get_connection()
    try:
        # 同じGoogleアカウントからの同時初回ログインを1件にまとめる。
        begin_account_registration(connection)
        existing = connection.execute(
            "SELECT * FROM users WHERE auth_provider = 'google' AND auth_subject = ?", (subject,)
        ).fetchone()
        if existing is not None and (not existing["is_active"] or existing["deleted_at"] is not None):
            raise LoginDenied("このアカウントの利用は停止されています。")
        collision = connection.execute(
            "SELECT id FROM users WHERE lower(email) = lower(?)", (email,)
        ).fetchone()
        if collision is not None and (existing is None or collision["id"] != existing["id"]):
            # メールだけで既存ユーザーを乗っ取ったり、ID 1を自動移管しない。
            raise LoginDenied("アカウントの確認が必要です。運営者に連絡してください。")
        if existing is None:
            if invitations is None:
                import streamlit as st
                # 呼出し引数だけで無制限登録を有効にしない。
                if access_invitations(st.secrets) is not None:
                    raise LoginDenied("登録方式が一致しません。")
                expected = st.secrets["access"]["invite_code"]
                if not isinstance(invitation_code, str) or not hmac.compare_digest(
                        invitation_code.strip().encode(), expected.encode()):
                    raise InvitationRequired("初回利用には招待コードが必要です。コードを確認して入力してください。")
            cursor = connection.execute(
                """INSERT INTO users(email, display_name, auth_provider, auth_subject,
                       avatar_url, email_verified, last_login_at)
                   VALUES (?, ?, 'google', ?, ?, 1, CURRENT_TIMESTAMP)""",
                (email, name, subject, picture),
            )
            user_id = int(cursor.lastrowid)
        else:
            user_id = int(existing["id"])
            connection.execute(
                """UPDATE users SET email = ?, display_name = ?, avatar_url = ?, email_verified = 1,
                   last_login_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (email, name, picture, user_id),
            )
        connection.commit()
        return user_id
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise LoginDenied("アカウントの確認が必要です。運営者に連絡してください。") from error
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def require_account_enabled(user_id: int, invitations: frozenset[str]) -> None:
    """業務Repositoryでも無効化・招待解除を確認。バックグラウンド処理を含む。"""
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT email, auth_provider, auth_subject, email_verified, is_active, deleted_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if (row is None or not row["is_active"] or row["deleted_at"] is not None
                or row["auth_provider"] != "google" or not row["auth_subject"] or not row["email_verified"]
                or (invitations is not None and str(row["email"] or "").casefold() not in invitations)):
            raise LoginDenied("このアカウントは現在利用できません。")
    finally:
        connection.close()


def logout_google_user() -> None:
    import streamlit as st
    from services.current_user_service import clear_current_user_id
    clear_current_user_id()
    st.query_params.clear()
    st.logout()


def require_google_user() -> None:
    import streamlit as st
    from database.initialize import initialize_database
    from services.current_user_service import clear_current_user_id, set_current_user_id
    try:
        invitations = validate_login_settings(st.secrets)
    except (LoginConfigurationError, FileNotFoundError):
        clear_current_user_id()
        st.title("MeTeA")
        st.info("現在、ログインの準備中です。運営者からの案内をお待ちください。")
        st.stop()
    if not st.user.is_logged_in:
        clear_current_user_id()
        st.title("MeTeA")
        st.write("ご自身のGoogleアカウントでログインしてください。初回は招待コードを入力します。" if invitations is None else "招待されたGoogleアカウントでログインしてください。")
        from ui.data_notice import render_data_notice
        render_data_notice()
        if st.button("Googleでログイン", type="primary"):
            st.login("google")
        st.stop()
    try:
        initialize_database()
        entered_code = st.session_state.pop("metea_pending_invite_code", None)
        if entered_code is None:
            user_id = resolve_google_user(dict(st.user), invitations)
        else:
            user_id = resolve_google_user(dict(st.user), invitations, invitation_code=entered_code)
        set_current_user_id(user_id)
    except InvitationRequired as error:
        from services.current_user_service import CURRENT_USER_SESSION_KEY
        if CURRENT_USER_SESSION_KEY in st.session_state:
            clear_current_user_id()
        st.title("MeTeAへようこそ")
        st.info(str(error))
        from ui.data_notice import render_data_notice
        render_data_notice()
        with st.form("first_invitation"):
            code = st.text_input("招待コード", type="password")
            submitted = st.form_submit_button("利用を開始")
        if submitted:
            st.session_state["metea_pending_invite_code"] = code
            st.rerun()
        if st.button("別のGoogleアカウントを使う"):
            logout_google_user()
        st.stop()
    except (ConnectionError, psycopg.OperationalError, psycopg.InterfaceError):
        clear_current_user_id()
        st.title("MeTeA")
        st.error("保存先との接続が切れました。少し待ってから再試行してください。")
        if st.button("再試行"):
            st.rerun()
        st.stop()
    except LoginDenied as error:
        clear_current_user_id()
        st.title("MeTeA")
        st.error(str(error))
        if st.button("別のアカウントでログイン"):
            logout_google_user()
        st.stop()
