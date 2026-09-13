import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from contextlib import ExitStack
from services import job_detail_data_service as data
from database.operation import current_operation


class DetailDataTest(unittest.TestCase):
    def test_read_operation_ends_before_rendering(self):
        job = SimpleNamespace(nearest_station="駅")
        basic = SimpleNamespace(nearest_station_place_id="place")
        values = {"load_job":job, "load_basic_info":basic, "load_current_job_commute":None,
                  "load_job_match_evaluations":{}, "load_job_application_decisions":{}, 'load_confirmation_records':[{'item_key':'test', 'status':'dismissed'}]}
        connection = MagicMock()
        with ExitStack() as stack:
            connect = stack.enter_context(patch("database.connection._open_connection", return_value=connection))
            for name, value in values.items():
                def read(*args, value=value, **kwargs):
                    self.assertIsNotNone(current_operation())
                    from database.connection import get_connection
                    get_connection().close()
                    return value
                stack.enter_context(patch.object(data, name, side_effect=read))
            result = data.load_job_detail_data(157)
            connect.assert_called_once()
            connection.commit.assert_called_once()
            connection.close.assert_called_once()
        self.assertIsNone(current_operation())
        self.assertIs(result['job'], job)
        self.assertEqual(result['resolutions'], {'test':'dismissed'})

    def test_progress_reuses_supplied_evaluations(self):
        from ui import job_evaluation_progress as progress
        with patch.object(progress, 'load_job_match_evaluations') as load:
            self.assertEqual(progress.render_evaluation_progress({}), {})
            load.assert_not_called()

    def test_page_passes_snapshot_to_renderers(self):
        from streamlit.testing.v1 import AppTest
        from pages import job_detail as page
        snapshot = dict(job=SimpleNamespace(company_name='test', job_title='title'), evaluations={})
        with ExitStack() as stack:
            stack.enter_context(patch.object(data, 'load_job_detail_data', return_value=snapshot))
            stack.enter_context(patch('ui.job_evaluation_area._poll'))
            renders = {}
            for name in ('render_ai_matching_result','render_matching_detail','render_application_decision'):
                renders[name] = stack.enter_context(patch.object(page, name))
            for name in ('render_job_navigation','render_basic_information','render_job_description','render_requirements','render_working_conditions','render_salary_and_benefits'):
                stack.enter_context(patch.object(page,name))
            app = AppTest.from_string('import streamlit as st\nst.query_params["job_id"]="157"\nfrom pages.job_detail import show_page\nshow_page()').run()
            self.assertFalse(app.exception)
            for render in renders.values():
                self.assertEqual(render.call_args.kwargs['snapshot'],snapshot)
            self.assertIs(render.call_args.kwargs['snapshot']['job'], snapshot['job'])
