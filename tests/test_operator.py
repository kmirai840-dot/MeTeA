import csv
import io
import json
import os
import unittest
import zipfile
from unittest.mock import patch

import streamlit as st
import test_user_data_isolation as fixtures
from database.connection import get_connection
from database.access_control import DataAccessDenied
from services import operator_service as operator


class Claims(dict):
    is_logged_in = True


class OperatorTest(unittest.TestCase):
    def setUp(self):
        fixtures.UserDataIsolationTest.setUp(self)
        c = get_connection()
        try:
            for uid in (1, 2):
                c.execute("UPDATE users SET email=?, auth_provider='google', auth_subject=?, email_verified=1 WHERE id=?", (f'u{uid}@example.com', f'sub-{uid}', uid))
            c.commit()
        finally:
            c.close()
        self.settings = {'access': {'allowed_emails': ['u1@example.com', 'u2@example.com'], 'admin_emails': ['u1@example.com']}}
        self.claims = Claims(email='u1@example.com', sub='sub-1', iss='https://accounts.google.com', email_verified=True)
        for mock in (patch.dict(os.environ, {'METEA_AUTH_MODE': 'google'}),
                     patch.object(st, 'secrets', self.settings), patch.object(st, 'user', self.claims),
                     patch.object(operator, 'get_current_user_id', return_value=1)):
            mock.start()
            self.addCleanup(mock.stop)

    def test_authorization_denies_each_entry_and_revocation(self):
        self.assertEqual(operator.require_operator(), 1)
        mutations = [
            patch.dict(self.settings['access'], admin_emails=[]),
            patch.dict(self.settings['access'], allowed_emails=['u2@example.com']),
            patch.dict(self.claims, sub='sub-2'),
            patch.dict(self.claims, email_verified=False),
            patch.dict(os.environ, METEA_AUTH_MODE='legacy'),
            patch.object(operator, 'get_current_user_id', return_value=2),
            patch.object(self.claims, 'is_logged_in', False),
        ]
        for mutation in mutations:
            with mutation:
                for operation in (operator.list_users, lambda: operator.read_user_data(2), lambda: operator.export_user_data(2)):
                    with self.assertRaises(PermissionError):
                        operation()
        c = get_connection()
        try:
            c.execute('UPDATE users SET is_active=0 WHERE id=1')
            c.commit()
        finally:
            c.close()
        self.assertFalse(operator.is_operator())
        with self.assertRaises(PermissionError):
            operator.export_user_data(2)

    def test_selected_user_all_tables_children_and_csv_safety(self):
        self.assertEqual(len(operator.list_users()), 2)
        for uid in (1, 2):
            data = operator.read_user_data(uid)
            self.assertEqual(len(data['tables']), 26)
            for rows in data['tables'].values():
                self.assertTrue(rows)
                self.assertNotIn(f'person-{3-uid}', json.dumps(rows))
            self.assertNotIn('auth_subject', data['tables']['users'][0])
        c = get_connection()
        try:
            c.execute('UPDATE form_drafts SET draft_data=? WHERE user_id=2', ('=HYPERLINK("bad")',))
            c.commit()
        finally:
            c.close()
        with zipfile.ZipFile(io.BytesIO(operator.export_user_data(2))) as archive:
            data = json.loads(archive.read('data.json'))
            self.assertEqual(data['tables']['form_drafts'][0]['draft_data'], '=HYPERLINK("bad")')
            rows = list(csv.DictReader(io.StringIO(archive.read('form_drafts.csv').decode('utf-8-sig'))))
            self.assertEqual(rows[0]['draft_data'], '\'=HYPERLINK("bad")')
        for invalid in (True, '1 OR 1=1', -1):
            with self.assertRaises(ValueError):
                operator.read_user_data(invalid)
        with self.assertRaises(DataAccessDenied):
            operator.read_user_data(9999)

    def test_lightweight_browse_matches_export_and_checks_authority(self):
        for uid in (1,2):
            data = operator.read_user_data(uid)
            self.assertEqual(operator.list_user_table_counts(uid), {t:len(rows) for t,rows in data['tables'].items()})
            for table, rows in data['tables'].items():
                self.assertEqual(operator.read_user_table(uid, table), rows)
        with self.assertRaises(ValueError):
            operator.read_user_table(2, 'users; SELECT 1')
        with patch.dict(self.settings['access'], admin_emails=[]):
            for fn in (lambda:operator.list_user_table_counts(2), lambda:operator.read_user_table(2, 'users')):
                with self.assertRaises(PermissionError):
                    fn()

    def test_export_is_deferred_and_rechecks_session_and_revocation(self):
        from types import SimpleNamespace
        from services.current_user_service import CURRENT_USER_SESSION_KEY
        state = {CURRENT_USER_SESSION_KEY:1}
        with patch('streamlit.runtime.scriptrunner.get_script_run_ctx', return_value=SimpleNamespace(session_state=state)), patch.object(operator, '_read_user_data', wraps=operator._read_user_data) as read:
            download = operator.prepare_user_export(2)
            read.assert_not_called()
            # 呼出元スレッドのStreamlit user/sessionには依存しない。
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as pool:
                payload = pool.submit(download).result()
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                self.assertEqual(json.loads(archive.read('data.json'))['user_id'], 2)
            with patch.dict(self.settings['access'], admin_emails=[]):
                with self.assertRaises(PermissionError):
                    download()
            state.clear()
            with self.assertRaises(PermissionError):
                download()
            self.assertEqual(read.call_count, 1)


if __name__ == '__main__':
    unittest.main()
