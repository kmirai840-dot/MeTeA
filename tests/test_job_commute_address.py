import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from models import Job, JobCommuteCheck
from services import job_commute_service as service


class CommuteAddressTest(unittest.TestCase):
    def test_address_save_restore_and_changed_context(self):
        job = Job(prefecture="福岡県", municipality="福岡市", source_text="勤務地住所")
        with patch.object(service, "get_current_user_id", return_value=7), patch.object(service, "save_job_commute_check") as save:
            result = service.save_manual_job_commute(3, "出発駅", "place1", "福岡市中央区1-2", 30, job=job)
            self.assertEqual(save.call_args.kwargs["user_id"], 7)
        with patch.object(service, "get_current_user_id", return_value=7), patch.object(service, "get_job_commute_check", return_value=result):
            self.assertEqual(service.load_current_job_commute(3, "place1", "", job=job), result)
            self.assertIsNone(service.load_current_job_commute(3, "other", "", job=job))
            self.assertIsNone(service.load_current_job_commute(3, "place1", "", job=replace(job, source_text="変更後")))
            self.assertIsNone(service.load_current_job_commute(3, "place1", "別の駅", job=job))

    def test_legacy_station_is_preserved(self):
        result = JobCommuteCheck(3, "出発", "place1", "到着", 20, "manual", "2026-09-13")
        with patch.object(service, "get_current_user_id", return_value=7), patch.object(service, "get_job_commute_check", return_value=result):
            self.assertEqual(service.load_current_job_commute(3, "place1", "到着", job=Job(nearest_station="到着")), result)
            self.assertIsNone(service.load_current_job_commute(3, "place1", "", job=Job()))

    def test_address_ui_saves_without_ai_when_semantics_exist(self):
        from streamlit.testing.v1 import AppTest
        from pages import job_detail as page
        basic = SimpleNamespace(nearest_station="出発駅", nearest_station_place_id="place1", prefecture="福岡県", municipality="福岡市")
        saved = None
        def save(**kwargs):
            nonlocal saved
            saved = SimpleNamespace(duration_minutes=kwargs["duration_minutes"], destination_station_name=kwargs["destination_station_name"], checked_at="2026-09-13")
            return saved
        with patch.object(page, "load_job_match_evaluations", return_value={3:SimpleNamespace(evaluation_result_json="{}")}), patch("ui.job_evaluation_area.notify_evaluation_saved"), patch.object(page, "load_basic_info", return_value=basic), patch.object(page, "load_current_job_commute", side_effect=lambda **kw: saved), patch.object(page, "save_manual_job_commute", side_effect=save) as writer, patch.object(page, "invalidate_current_user_job_evaluation") as invalidate, patch.object(page, "enqueue_job_evaluation") as enqueue:
            app = AppTest.from_string('from pages.job_detail import render_commute_confirmation\nfrom models import Job\nrender_commute_confirmation(3, Job())').run()
            app.text_input[0].input("福岡市中央区1-2")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.number_input), 1)
            app.number_input[0].set_value(30)
            app.button[1].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(writer.call_args.kwargs["destination_station_name"], "福岡市中央区1-2")
            self.assertEqual(len(app.success), 1)
            enqueue.assert_not_called()
            invalidate.assert_not_called()
            app.button[1].click().run()
            enqueue.assert_not_called()
