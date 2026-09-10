import copy
import unittest
from unittest.mock import patch
import streamlit as st
import test_google_auth as base
from services import google_auth_service as auth
from services import current_user_service as identity
from database.repositories.draft_repository import save_draft,get_draft

CODE = 'test-code-only-32-random-characters'

class InviteCodeTest(unittest.TestCase):
    setUp = base.GoogleAccountTest.setUp
    sql = base.GoogleAccountTest.sql

    def test_registration_revisit_rotation_and_revocation(self):
        settings=copy.deepcopy(base.SETTINGS)
        settings['access'].update(registration_mode='invite_code',invite_code=CODE,allowed_emails=[])
        with patch.object(st,'secrets',settings):
            self.assertIsNone(auth.validate_login_settings(settings))
            for wrong in (None,'','bad'):
                with self.assertRaises(auth.InvitationRequired):
                    auth.resolve_google_user(base.claims(),None,invitation_code=wrong)
            self.assertEqual(len(self.sql('SELECT id FROM users')),1)
            uid=auth.resolve_google_user(base.claims(),None,invitation_code=CODE)
            with identity.user_scope(uid):
                save_draft(uid,'code-test',{'text':'mine'})
            settings['access']['invite_code']='rotated-test-code-32-characters'
            self.assertEqual(auth.resolve_google_user(base.claims(),None),uid)
            with identity.user_scope(uid):
                self.assertEqual(get_draft(uid,'code-test'),{'text':'mine'})
            with self.assertRaises(auth.InvitationRequired):
                auth.resolve_google_user(base.claims('b@example.com','b'),None,invitation_code=CODE)
            other=auth.resolve_google_user(base.claims('b@example.com','b'),None,invitation_code=settings['access']['invite_code'])
            with identity.user_scope(other):
                self.assertIsNone(get_draft(other,'code-test'))
            self.sql('UPDATE users SET is_active=0 WHERE id=?',(uid,))
            with self.assertRaises(auth.LoginDenied):
                auth.resolve_google_user(base.claims(),None,invitation_code=settings['access']['invite_code'])
            with self.assertRaises(auth.LoginDenied):
                auth.require_account_enabled(uid,None)

    def test_code_cannot_bypass_claims_or_claim_legacy_owner(self):
        settings=copy.deepcopy(base.SETTINGS)
        settings['access'].update(registration_mode='invite_code',invite_code=CODE)
        with patch.object(st,'secrets',settings):
            with self.assertRaises(auth.LoginDenied):
                auth.resolve_google_user(base.claims(email_verified=False),None,invitation_code=CODE)
            self.sql("UPDATE users SET email='a@example.com' WHERE id=1")
            with self.assertRaises(auth.LoginDenied):
                auth.resolve_google_user(base.claims(),None,invitation_code=CODE)
            self.assertIsNone(self.sql('SELECT auth_subject FROM users WHERE id=1')[0][0])

    def test_bad_configuration_fails_closed(self):
        for mode,code in [('invite_code','short'),('unknown',CODE)]:
            settings=copy.deepcopy(base.SETTINGS)
            settings['access'].update(registration_mode=mode,invite_code=code)
            with self.assertRaises(auth.LoginConfigurationError):
                auth.validate_login_settings(settings)

    def test_invitation_form_creates_account_after_submit(self):
        from streamlit.testing.v1 import AppTest
        class User(dict):
            is_logged_in=True
        settings=copy.deepcopy(base.SETTINGS)
        settings['access'].update(registration_mode='invite_code',invite_code=CODE)
        with patch.object(st,'secrets',settings),patch.object(st,'user',User(base.claims())):
            at=AppTest.from_string('from services.google_auth_service import require_google_user; require_google_user()',default_timeout=30).run()
            self.assertFalse(at.exception)
            at.text_input[0].input(CODE)
            at.button[0].click().run()
            self.assertFalse(at.exception)
            self.assertEqual(len(self.sql("SELECT id FROM users WHERE auth_provider='google'")),1)
