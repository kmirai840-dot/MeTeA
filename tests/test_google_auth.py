"""OIDC後の招待判定・再ログイン・失効を一時DBと模擬st.userで検証する。"""
from __future__ import annotations

import copy
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from database.connection import get_connection
from database.initialize import initialize_database
from database.repositories.draft_repository import get_draft, save_draft
from services import google_auth_service as auth
from services import current_user_service as identity


INVITES = frozenset({"a@example.com", "b@example.com"})
SETTINGS = {
    "auth": {
        "redirect_uri": "http://localhost:8501/oauth2callback",
        "cookie_secret": "test-only-cookie-secret-32-characters",
        "google": {"client_id": "test.apps.googleusercontent.com", "client_secret": "test-only",
                   "server_metadata_url": auth.GOOGLE_METADATA_URL},
    },
    "access": {"allowed_emails": list(INVITES)},
}


def claims(email="a@example.com", subject="subject-a", **kwargs):
    return {"iss": "https://accounts.google.com", "sub": subject, "email": email,
            "email_verified": True, "name": "Test user", **kwargs}


class GoogleAccountTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {"METEA_DATABASE_BACKEND": getattr(self, 'database_backend', 'sqlite'),
                                      "METEA_DATABASE_PATH": str(Path(tmp.name) / "accounts.db"),
                                      "METEA_AUTH_MODE": "google"})
        env.start()
        self.addCleanup(env.stop)
        secrets = patch.object(st, "secrets", copy.deepcopy(SETTINGS))
        secrets.start()
        self.addCleanup(secrets.stop)
        initialize_database()

    def sql(self, sql, args=()):
        connection = get_connection()
        try:
            rows = connection.execute(sql, args).fetchall()
            connection.commit()
            return rows
        finally:
            connection.close()

    def test_first_login_does_not_claim_legacy_user_one(self):
        uid = auth.resolve_google_user(claims(), INVITES)
        self.assertEqual(uid, 2)
        old = self.sql("SELECT auth_subject,email FROM users WHERE id=1")[0]
        self.assertEqual(tuple(old), (None, None))

    def test_relogin_restores_same_user_and_saved_input(self):
        uid = auth.resolve_google_user(claims(), INVITES)
        with identity.user_scope(uid):
            save_draft(uid, "form", {"text": "saved"})
        initialize_database()
        again = auth.resolve_google_user(claims(name="New name"), INVITES)
        self.assertEqual(uid, again)
        with identity.user_scope(again):
            self.assertEqual(get_draft(again, "form"), {"text": "saved"})

    def test_two_google_accounts_have_separate_data(self):
        first = auth.resolve_google_user(claims(), INVITES)
        second = auth.resolve_google_user(claims("b@example.com", "subject-b"), INVITES)
        self.assertNotEqual(first, second)
        for uid in (first, second):
            with identity.user_scope(uid):
                save_draft(uid, "same-form", {"owner": uid})
        for uid in (first, second):
            with identity.user_scope(uid):
                self.assertEqual(get_draft(uid, "same-form"), {"owner": uid})
                with self.assertRaises(PermissionError):
                    get_draft(first if uid == second else second, "same-form")

    def test_concurrent_first_login_creates_one_identity(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(auth.resolve_google_user, claims(), INVITES) for _ in range(2)]
            self.assertEqual(futures[0].result(), futures[1].result())
        self.assertEqual(self.sql("SELECT COUNT(*) FROM users WHERE auth_provider='google'")[0][0], 1)

    def test_invalid_or_uninvited_claims_create_no_user(self):
        for info in [claims("outsider@example.com"), claims(email_verified=False),
                     claims(email_verified="true"), claims(iss="https://other.example"),
                     claims(subject=""), claims(email=None)]:
            with self.subTest(info=info), self.assertRaises(auth.LoginDenied):
                auth.resolve_google_user(info, INVITES)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM users")[0][0], 1)

    def test_email_collision_does_not_reassign_existing_account(self):
        self.sql("UPDATE users SET email='a@example.com' WHERE id=1")
        with self.assertRaises(auth.LoginDenied):
            auth.resolve_google_user(claims(), INVITES)
        self.assertIsNone(self.sql("SELECT auth_subject FROM users WHERE id=1")[0][0])

    def test_same_email_with_different_subject_is_denied(self):
        uid = auth.resolve_google_user(claims(), INVITES)
        with self.assertRaises(auth.LoginDenied):
            auth.resolve_google_user(claims(subject="different-person"), INVITES)
        self.assertEqual(self.sql("SELECT auth_subject FROM users WHERE id=?", (uid,))[0][0], "subject-a")

    def test_changed_verified_email_keeps_subject_identity(self):
        uid = auth.resolve_google_user(claims(), INVITES)
        self.assertEqual(auth.resolve_google_user(claims("b@example.com"), INVITES), uid)

    def test_disabled_or_deleted_account_cannot_login(self):
        uid = auth.resolve_google_user(claims(), INVITES)
        self.sql("UPDATE users SET is_active=0 WHERE id=?", (uid,))
        with self.assertRaises(auth.LoginDenied):
            auth.resolve_google_user(claims(), INVITES)
        self.sql("UPDATE users SET is_active=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (uid,))
        with self.assertRaises(auth.LoginDenied):
            auth.resolve_google_user(claims(), INVITES)

    def test_revocation_stops_existing_session_and_background_writes(self):
        uid = auth.resolve_google_user(claims(), INVITES)
        with identity.user_scope(uid):
            save_draft(uid, "form", {"value": "before"})
            self.sql("UPDATE users SET is_active=0 WHERE id=?", (uid,))
            with self.assertRaises(auth.LoginDenied):
                save_draft(uid, "form", {"value": "after"})
        self.assertIn("before", self.sql("SELECT draft_data FROM form_drafts WHERE user_id=?", (uid,))[0][0])

    def test_invitation_removal_stops_existing_session(self):
        uid = auth.resolve_google_user(claims(), INVITES)
        with patch.object(st, "secrets", {"access": {"allowed_emails": []}}), identity.user_scope(uid):
            with self.assertRaises(auth.LoginDenied):
                get_draft(uid, "form")

    def test_google_mode_cannot_default_to_user_one(self):
        with patch.object(identity, "_streamlit_session_state", return_value={}):
            with self.assertRaises(identity.UserIdentityRequired):
                identity.get_current_user_id()


class GoogleSettingsTest(unittest.TestCase):
    def test_valid_settings_and_case_normalized_allowlist(self):
        settings = copy.deepcopy(SETTINGS)
        settings["access"]["allowed_emails"] = [" A@EXAMPLE.COM "]
        self.assertEqual(auth.validate_login_settings(settings), frozenset({"a@example.com"}))

    def test_missing_and_invalid_settings_fail_closed(self):
        samples = [{}, {"auth": "invalid"}, {"auth": {"google": "invalid"}}]
        for path, value in [("redirect_uri", "http://public.example/oauth2callback"),
                            ("redirect_uri", "https://example.com/wrong"), ("cookie_secret", "short")]:
            sample = copy.deepcopy(SETTINGS)
            sample["auth"][path] = value
            samples.append(sample)
        sample = copy.deepcopy(SETTINGS)
        sample["auth"]["google"]["server_metadata_url"] = "https://other.example"
        samples.append(sample)
        for sample in samples:
            with self.subTest(sample=sample), self.assertRaises(auth.LoginConfigurationError):
                auth.validate_login_settings(sample)

    def test_empty_or_malformed_invitation_list_is_not_open_registration(self):
        for value in [[], "a@example.com", ["*"], [None], ["@example.com"]]:
            sample = copy.deepcopy(SETTINGS)
            sample["access"]["allowed_emails"] = value
            with self.subTest(value=value), self.assertRaises(auth.LoginConfigurationError):
                auth.validate_login_settings(sample)

    def test_invalid_mode_does_not_fall_back_to_demo(self):
        with patch.dict(os.environ, {"METEA_AUTH_MODE": "gooogle"}):
            with self.assertRaises(auth.LoginConfigurationError):
                auth.auth_mode()


class StopScreen(Exception):
    pass


class FakeUser(dict):
    @property
    def is_logged_in(self):
        return bool(self)


class GoogleLoginScreenTest(unittest.TestCase):
    def test_unauthenticated_screen_starts_named_google_login(self):
        with patch.object(st, "secrets", SETTINGS), patch.object(st, "user", FakeUser()), \
             patch.object(st, "title"), patch.object(st, "write"), \
             patch.object(st, "button", return_value=True), patch.object(st, "login") as login, \
             patch.object(st, "stop", side_effect=StopScreen), \
             patch.object(identity, "clear_current_user_id") as clear:
            with self.assertRaises(StopScreen):
                auth.require_google_user()
            login.assert_called_once_with("google")
            clear.assert_called_once()

    def test_configuration_failure_cannot_use_previous_session(self):
        with patch.object(st, "secrets", {}), patch.object(st, "title"), patch.object(st, "info"), \
             patch.object(st, "stop", side_effect=StopScreen), \
             patch.object(identity, "clear_current_user_id") as clear:
            with self.assertRaises(StopScreen):
                auth.require_google_user()
            clear.assert_called_once()

    def test_authenticated_identity_is_passed_to_application(self):
        with patch.object(st, "secrets", SETTINGS), patch.object(st, "user", FakeUser(claims())), \
             patch("database.initialize.initialize_database"), \
             patch.object(auth, "resolve_google_user", return_value=2) as resolve, \
             patch.object(identity, "set_current_user_id") as set_user:
            auth.require_google_user()
            resolve.assert_called_once_with(claims(), INVITES)
            set_user.assert_called_once_with(2)

    def test_logout_clears_session_and_google_cookie(self):
        with patch.object(identity, "clear_current_user_id") as clear, \
             patch.object(st, "query_params", {}), patch.object(st, "logout") as logout:
            auth.logout_google_user()
            clear.assert_called_once()
            logout.assert_called_once()


if __name__ == "__main__":
    unittest.main()
