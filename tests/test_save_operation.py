"""接続共有の原子性と、ログイン済み再確認の安全性。"""
import os,tempfile,unittest
from pathlib import Path
from datetime import date
from unittest.mock import patch
from database.operation import database_operation,current_operation
from database.connection import get_connection
from database.initialize import initialize_database
from services.current_user_service import user_scope,CURRENT_USER_SESSION_KEY
from services import google_auth_service as auth

class SessionReuseTest(unittest.TestCase):
    def setUp(self):
        self.claims=dict(iss='https://accounts.google.com',sub='subject',email='test@example.test',email_verified=True)
        self.state={CURRENT_USER_SESSION_KEY:2,auth.VERIFIED_GOOGLE_CLAIMS_KEY:auth.verified_claims_signature(self.claims)}
    def test_same_identity_always_checks_enabled(self):
        with patch.object(auth,'require_account_enabled') as check:
            for _ in range(2):self.assertEqual(auth.reuse_verified_session(self.claims,None,self.state),2)
            self.assertEqual(check.call_count,2);check.assert_called_with(2,None,subject='subject')
    def test_changed_claim_or_suspended_session_requires_full_resolution(self):
        for key,value in [('sub','other'),('email','other@example.test'),('email_verified',False),('iss','untrusted')]:
            with self.subTest(key=key):self.assertIsNone(auth.reuse_verified_session(dict(self.claims,**{key:value}),None,self.state))
        self.state.pop(CURRENT_USER_SESSION_KEY)
        self.assertIsNone(auth.reuse_verified_session(self.claims,None,self.state))
    def test_disabled_account_is_not_hidden_by_session_reuse(self):
        with patch.object(auth,'require_account_enabled',side_effect=auth.LoginDenied('disabled')):
            with self.assertRaises(auth.LoginDenied):auth.reuse_verified_session(self.claims,None,self.state)

class DatabaseOperationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        env=patch.dict(os.environ,{'METEA_DATABASE_BACKEND':'sqlite','METEA_DATABASE_PATH':str(Path(self.tmp.name)/'test.db'),'METEA_AUTH_MODE':'legacy','METEA_REQUIRE_AUTH':'true'})
        env.start();self.addCleanup(env.stop);initialize_database()
    def test_post_save_failure_rolls_back_profile_and_draft_deletion(self):
        from services.basic_info_service import save_basic_info,load_basic_info,save_basic_info_draft,load_basic_info_draft
        from models import BasicInfo
        with user_scope(1):
            old=BasicInfo('旧','名前','female',date(1994,9,16),'福岡県','福岡市','駅','test')
            save_basic_info(old);save_basic_info_draft({'private':'keep'})
            with patch('services.basic_info_service.save_general_activity',side_effect=RuntimeError('failure')):
                with self.assertRaises(RuntimeError):save_basic_info(BasicInfo('新','名前','female',date(1994,9,16),'福岡県','福岡市','駅','test'))
            self.assertEqual(load_basic_info(),old);self.assertEqual(load_basic_info_draft(),{'private':'keep'})
        self.assertIsNone(current_operation())
    def test_one_connection_nested_operations_and_recheck_next_operation(self):
        from database import connection
        from database.access_control import require_user_id,DataAccessDenied
        @database_operation
        def inner():
            require_user_id(1)
            db=get_connection();db.execute('SELECT 1');db.close()
        @database_operation
        def outer():
            require_user_id(1);inner()
            with self.assertRaises(DataAccessDenied):require_user_id(2)
        with user_scope(1),patch.object(auth,'auth_mode',return_value='google'),patch.object(auth,'access_invitations',return_value=None),patch.object(auth,'require_account_enabled') as check,patch.object(connection,'_open_connection',wraps=connection._open_connection) as opened:
            outer();self.assertEqual(check.call_count,1);self.assertEqual(opened.call_count,1)
            outer();self.assertEqual(check.call_count,2);self.assertEqual(opened.call_count,2)
        self.assertIsNone(current_operation())
    def test_caught_repository_rollback_prevents_outer_commit(self):
        @database_operation
        def save_then_catch():
            db=get_connection();db.execute("UPDATE users SET display_name='should roll back' WHERE id=1");db.commit();db.rollback();db.close()
        with self.assertRaises(RuntimeError):save_then_catch()
        db=get_connection()
        try:self.assertIsNone(db.execute('SELECT display_name FROM users WHERE id=1').fetchone()[0])
        finally:db.close()

    def test_caught_nested_service_error_prevents_commit(self):
        @database_operation
        def inner():
            get_connection().execute("UPDATE users SET display_name='rollback' WHERE id=1")
            raise ValueError('later failure')
        @database_operation
        def outer():
            try:inner()
            except ValueError:pass
        with self.assertRaises(RuntimeError):outer()
        db=get_connection()
        try:self.assertIsNone(db.execute('SELECT display_name FROM users WHERE id=1').fetchone()[0])
        finally:db.close()

if __name__=='__main__':unittest.main()
