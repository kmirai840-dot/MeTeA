"""Changed-page routing smoke tests against an isolated database, without login/API calls."""
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import test_user_data_isolation as fixtures


class ChangedPageNavigationTest(unittest.TestCase):
    setUp = fixtures.UserDataIsolationTest.setUp

    def test_changed_routes_and_return_visits_in_one_session(self):
        jid = self.records[1]['job']
        aid = self.records[1]['application']
        from dataclasses import fields, replace
        from services.current_user_service import user_scope
        with user_scope(1):
            hope, items = fixtures.hope.get_hope_condition(1), fixtures.hope.get_hope_condition_items(1)
            hope = replace(hope, **{f.name: 'no_preference' for f in fields(hope) if f.name.endswith('_priority')})
            fixtures.hope.save_hope_conditions(1, hope, [replace(i, priority='no_preference') for i in items], '')
            second = fixtures.jobs.create_job(1, fixtures.m.Job(company_name='second company'))
        with ExitStack() as stack:
            for name in ('configure_runtime_secrets', 'require_app_password'):
                stack.enter_context(patch('services.runtime_config.' + name))
            stack.enter_context(patch('services.runtime_config.is_demo_environment', return_value=False))
            stack.enter_context(patch('services.job_matching_auto_evaluation_service.enqueue_job_evaluation', return_value=False))
            stack.enter_context(patch('services.job_matching_auto_evaluation_service.enqueue_stale_job_evaluations', return_value=0))
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=40)
            app.session_state['metea_current_user_id'] = 1
            routes = [
                {'page':'profile_review'},
                *({'page':'profile_review','category':c} for c in ('basic','hope','values','axis','career')),
                {'page':'career'}, {'page':'profile_review'},
                {'page':'job_list'}, {'page':'job_detail','job_id':str(jid)},
                {'page':'job_comparison','job_ids':f'{jid},{second}'}, {'page':'job_list'},
                {'page':'application_list'}, {'page':'milestones'}, {'page':'activity_history'},
                {'page':'application_detail','application_id':str(aid)},
                {'page':'selection_preparation','application_id':str(aid)},
                {'page':'selection_preparation'}, {'page':'application_list'},
                {'page':'application_dashboard'}, {'page':'settings'},
                {'page':'profile_review'},
            ]
            for route in routes:
                with self.subTest(route=route):
                    app.query_params.clear()
                    app.query_params.update(route)
                    app.run()
                    self.assertFalse(app.exception, [(e.message, e.stack_trace) for e in app.exception])
                    if route.get('page') == 'selection_preparation' and 'application_id' in route:
                        self.assertTrue(any('日程未定' in x.value for x in app.markdown))
                        for label in ('企業別準備', '共通準備', '選考別準備'):
                            next(r for r in app.get('button_group') if r.label == '準備の種類').set_value(label).run()
                            self.assertFalse(app.exception)
                    if route.get('page') == 'settings':
                        next(b for b in app.button if b.label == 'トップ画面へ戻る').click().run()
                        self.assertFalse(app.exception)
                        self.assertEqual(app.query_params.get('page', 'home'), 'home')


