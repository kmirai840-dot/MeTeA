import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from models import Job, JobMatchEvaluation
from pages import job_list

class JobListPageTest(unittest.TestCase):
    def test_page_loads_empty_completed_and_failed_evaluations(self):
        for status in ('empty', 'completed', 'failed'):
            with self.subTest(status=status):
                jobs = [] if status == 'empty' else [(10, Job(company_name='Test'))]
                evaluations = {} if not jobs else {10: JobMatchEvaluation(job_id=10, overall_score=70, evaluation_status=status)}
                snapshot = dict(jobs=jobs, evaluations=evaluations, decisions={}, sources={})
                with patch.object(job_list, 'load_job_list_data', return_value=snapshot), patch.object(job_list, 'load_job_sources', side_effect=AssertionError('描画中の再取得')), patch.object(job_list, 'render_evaluation_progress', return_value=evaluations) as progress:
                    app=AppTest.from_string('from pages.job_list import show_page\nshow_page()').run(timeout=30)
                    self.assertEqual(list(app.exception), [])
                    progress.assert_called_once_with(evaluations)
                    if status == 'failed':
                        self.assertTrue(any(b.label == '再試行' for b in app.button))

if __name__ == '__main__':
    unittest.main()

