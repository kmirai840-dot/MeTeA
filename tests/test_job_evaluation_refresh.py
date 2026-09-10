"""実DBは使わず、変更の取りこぼしと画面監視を検証する。"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from database.initialize import initialize_database
from database.repositories import job_evaluation_repository as repo, job_repository
from models import Job, JobMatchEvaluation
from services.current_user_service import user_scope
from services import job_matching_auto_evaluation_service as worker
from ui import job_evaluation_progress as ui


class RefreshTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {"METEA_DATABASE_BACKEND": "sqlite",
            "METEA_DATABASE_PATH": str(Path(tmp.name)/"test.db"),
            "METEA_AUTH_MODE": "legacy", "METEA_REQUIRE_AUTH": "true"})
        env.start()
        self.addCleanup(env.stop)
        scope = user_scope(1)
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        initialize_database()
        self.job = job_repository.create_job(1, Job(company_name="test"))
        repo.save_job_match_evaluation(1, JobMatchEvaluation(job_id=self.job, overall_score=70))
        worker._submitted_jobs.clear()

    def test_unchanged_does_not_call_ai(self):
        with patch.object(worker._executor, "submit") as submit:
            self.assertFalse(worker.enqueue_job_evaluation(self.job))
            submit.assert_not_called()

    def test_change_during_evaluation_survives_result_save(self):
        repo.mark_job_match_evaluation_stale(1, self.job, "first")
        repo.set_job_match_evaluation_status(1, self.job, "running")
        self.assertFalse(repo.get_job_match_evaluations(1)[self.job].is_stale)
        repo.mark_job_match_evaluation_stale(1, self.job, "second")
        repo.save_job_match_evaluation(1, JobMatchEvaluation(job_id=self.job, overall_score=80))
        repo.set_job_match_evaluation_status(1, self.job, "completed")
        result = repo.get_job_match_evaluations(1)[self.job]
        self.assertTrue(result.is_stale)
        self.assertEqual(result.stale_reason, "second")
        self.assertEqual(result.overall_score, 80)
        repo.set_job_match_evaluation_status(1, self.job, "running")
        repo.save_job_match_evaluation(1, JobMatchEvaluation(job_id=self.job, overall_score=90))
        self.assertFalse(repo.get_job_match_evaluations(1)[self.job].is_stale)

    def test_failed_or_running_first_jobs_do_not_starve_later_jobs(self):
        with patch.object(worker, "load_current_user_stale_job_ids", return_value=[1,2,3,4,5]), patch.object(worker, "enqueue_job_evaluation", side_effect=[False,False,False,True,True]) as enqueue:
            self.assertEqual(worker.enqueue_stale_job_evaluations(max_jobs=2), 2)
            self.assertEqual(enqueue.call_count, 5)

    def test_snapshot_is_isolated_and_pending_stops_on_failure(self):
        from database.connection import get_connection
        with get_connection() as db:
            db.execute("INSERT INTO users(id) VALUES (2)")
        db.close()
        with user_scope(2):
            self.assertEqual(ui.evaluation_snapshot(), ())
        repo.set_job_match_evaluation_status(1, self.job, "running")
        self.assertTrue(ui.has_pending(ui.evaluation_snapshot()))
        repo.set_job_match_evaluation_status(1, self.job, "failed")
        self.assertFalse(ui.has_pending(ui.evaluation_snapshot()))

    def test_monitor_reads_status_only_and_refreshes_on_completion(self):
        initial = ((self.job, "running", False, "old"),)
        done = ((self.job, "completed", False, "new"),)
        callbacks = []
        fake = Mock()
        def fragment(**kw):
            self.assertEqual(kw["run_every"], 3)
            def decorate(fn):
                callbacks.append(fn)
                return fn
            return decorate
        fake.fragment = fragment
        with patch.object(ui, "st", fake), patch.object(ui, "load_job_match_evaluations"), patch.object(ui, "enqueue_stale_job_evaluations") as enqueue, patch.object(ui, "evaluation_snapshot", side_effect=[initial,initial,done]):
            ui.render_evaluation_progress()
            fake.rerun.assert_not_called()
            callbacks[0]()
            fake.rerun.assert_called_once()
            enqueue.assert_called_once()  # 定期確認ではAIを投入しない

    def test_job_update_invalidates_only_changed_content(self):
        from services.job_service import update_job_data
        job = Job(company_name="test", occupation="engineer", source_type="求人サイト", source_name="test", job_summary="test")
        self.assertEqual(update_job_data(self.job, job), [])
        repo.save_job_match_evaluation(1, JobMatchEvaluation(job_id=self.job, overall_score=70))
        self.assertEqual(update_job_data(self.job, job), [])
        self.assertFalse(repo.get_job_match_evaluations(1)[self.job].is_stale)
        job.job_summary = "changed"
        self.assertEqual(update_job_data(self.job, job), [])
        self.assertTrue(repo.get_job_match_evaluations(1)[self.job].is_stale)

    def test_idle_has_no_timer(self):
        with patch.object(ui, "st") as st, patch.object(ui, "load_job_match_evaluations"), patch.object(ui, "enqueue_stale_job_evaluations"), patch.object(ui, "evaluation_snapshot", return_value=((self.job,"completed",False,"now"),)):
            ui.render_evaluation_progress()
            st.fragment.assert_not_called()

    def test_worker_continues_queue(self):
        with patch.object(worker, "automatically_evaluate_and_save_job", return_value=(JobMatchEvaluation(job_id=self.job), "")), patch.object(worker, "enqueue_stale_job_evaluations") as next_batch:
            worker._run_background_evaluation(1, self.job)
            next_batch.assert_called_once()

if __name__ == "__main__":
    unittest.main()
