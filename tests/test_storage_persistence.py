"""別プロセスでSQLiteの保存・本人識別・ロールバックを確認する。実DBは使わない。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StoragePersistenceTest(unittest.TestCase):
    def test_restart_preserves_two_users_and_committed_drafts(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, METEA_DATABASE_PATH=str(Path(directory) / "restart.db"),
                       METEA_DATABASE_BACKEND=getattr(self, 'database_backend', 'sqlite'),
                       METEA_AUTH_MODE="legacy", METEA_REQUIRE_AUTH="true")
            self.run_process('''
from database.initialize import initialize_database
from database.connection import get_connection
from database.repositories.draft_repository import save_draft
from services.current_user_service import user_scope
initialize_database()
with get_connection() as db:
    db.execute("INSERT INTO users(id) VALUES (2)")
db.close()
for uid in (1, 2):
    with user_scope(uid):
        save_draft(uid, "restart-check", {"owner": uid, "text": "saved"})
# 未コミットの変更はプロセス終了時に破棄される必要がある。
db = get_connection()
db.execute("UPDATE form_drafts SET draft_data='{}' WHERE user_id=2")
''', env)
            self.run_process('''
from database.initialize import initialize_database
from database.repositories.draft_repository import get_draft
from database.access_control import DataAccessDenied
from services.current_user_service import user_scope, get_current_user_id, UserIdentityRequired
initialize_database()
for uid in (1, 2):
    with user_scope(uid):
        assert get_draft(uid, "restart-check") == {"owner": uid, "text": "saved"}
        try:
            get_draft(3-uid, "restart-check")
        except DataAccessDenied:
            pass
        else:
            raise AssertionError("Other user's draft was accessible")
try:
    get_current_user_id()
except UserIdentityRequired:
    pass
else:
    raise AssertionError("Restart must not restore a global user identity")
''', env)

    def run_process(self, source, env):
        result = subprocess.run([sys.executable, "-B", "-c", source], cwd=ROOT,
                                env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
