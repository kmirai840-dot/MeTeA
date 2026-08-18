"""AI評価バックグラウンド実行の回帰テスト。"""

import unittest
from unittest.mock import patch

from models import JobMatchEvaluation
from services import job_matching_auto_evaluation_service as service


class JobMatchingBackgroundTest(unittest.TestCase):
    def setUp(self) -> None:
        service._submitted_jobs.clear()

    @patch.object(service._executor, "submit")
    @patch.object(service, "set_job_match_evaluation_status")
    @patch.object(service, "get_job_match_evaluations", return_value={})
    @patch.object(service, "get_current_user_id", return_value=1)
    def test_enqueue_returns_immediately_and_marks_queued(
        self, _user, _load, set_status, submit
    ) -> None:
        self.assertTrue(service.enqueue_job_evaluation(10))
        set_status.assert_called_once_with(1, 10, "queued")
        submit.assert_called_once()

    @patch.object(service._executor, "submit")
    @patch.object(service, "set_job_match_evaluation_status")
    @patch.object(service, "get_job_match_evaluations")
    @patch.object(service, "get_current_user_id", return_value=1)
    def test_running_job_is_not_enqueued_twice(
        self, _user, load, set_status, submit
    ) -> None:
        load.return_value = {
            10: JobMatchEvaluation(job_id=10, evaluation_status="running")
        }
        self.assertFalse(service.enqueue_job_evaluation(10))
        set_status.assert_not_called()
        submit.assert_not_called()

    @patch.object(service._executor, "submit")
    @patch.object(service, "set_job_match_evaluation_status")
    @patch.object(service, "get_job_match_evaluations")
    @patch.object(service, "get_current_user_id", return_value=1)
    def test_failed_job_requires_explicit_retry(
        self, _user, load, set_status, submit
    ) -> None:
        load.return_value = {
            10: JobMatchEvaluation(job_id=10, evaluation_status="failed")
        }
        self.assertFalse(service.enqueue_job_evaluation(10))
        self.assertTrue(service.enqueue_job_evaluation(10, retry=True))
        set_status.assert_called_once_with(1, 10, "queued")
        submit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
