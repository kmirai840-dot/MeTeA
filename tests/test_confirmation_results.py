import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from services.current_user_service import user_scope
from database.connection import get_connection
from database.initialize import initialize_database
from database.access_control import DataAccessDenied
from services import job_confirmation_service as service


class ConfirmationResultsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, {'METEA_DATABASE_BACKEND':'sqlite', 'METEA_DATABASE_PATH':str(Path(tmp.name)/'test.db'), 'METEA_AUTH_MODE':'legacy'})
        env.start(); self.addCleanup(env.stop)
        initialize_database()
        c = get_connection()
        c.execute('INSERT INTO users(id) VALUES (2)')
        c.execute('INSERT INTO user_jobs(id,user_id) VALUES (10,1)')
        c.execute('INSERT INTO user_jobs(id,user_id) VALUES (11,2)')
        c.commit(); c.close()

    def test_save_update_noop_restore_and_isolation(self):
        with patch.object(service, 'invalidate_current_user_job_evaluation') as invalidate, user_scope(1):
            self.assertTrue(service.save_confirmation_result(10,'転勤条件','情報なし','転勤なし'))
            self.assertFalse(service.save_confirmation_result(10,'転勤条件','情報なし','転勤なし'))
            self.assertTrue(service.save_confirmation_result(10,'転勤条件','情報なし','転勤あり'))
            rows = service.load_confirmation_records(10)
            self.assertEqual(rows[0]['result_text'],'転勤あり')
            self.assertEqual(rows[0]['status'],'confirmed')
            self.assertEqual(invalidate.call_count,2)
            service.restore_confirmation_item(10, rows[0]['item_key'])
            self.assertEqual(service.load_confirmation_records(10),[])
            self.assertEqual(invalidate.call_count,3)
            with self.assertRaises(DataAccessDenied): service.save_confirmation_result(11,'転勤条件','','改変')
        with user_scope(2):
            with self.assertRaises(DataAccessDenied): service.load_confirmation_records(10)

    def test_atomic_failure_does_not_save_partial_result(self):
        with user_scope(1), patch.object(service,'invalidate_current_user_job_evaluation',side_effect=RuntimeError('fail')):
            with self.assertRaises(RuntimeError): service.save_confirmation_result(10,'転勤条件','','転勤なし')
            self.assertEqual(service.load_confirmation_records(10),[])

    def test_empty_result_rejected_and_dismissal_retained(self):
        with user_scope(1):
            with self.assertRaises(ValueError): service.save_confirmation_result(10,'転勤条件','',' ')
            service.mark_confirmation_not_required(10,'転勤条件','')
            self.assertEqual(next(iter(service.load_job_confirmation_resolutions(10).values())),'not_required')

    def test_form_saves_once_and_restores_text(self):
        from streamlit.testing.v1 import AppTest
        from ui import job_confirmation_results as ui
        with patch.object(ui,'save_confirmation_result',return_value=True) as save:
            app=AppTest.from_string("from ui.job_confirmation_results import render_result_form\nrender_result_form(10,dict(item_key='k',item_name='転勤条件',item_reason='情報なし',result_text='前回'))", default_timeout=10).run()
            app.text_area[0].input('転勤なし').run()
            save.assert_not_called()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            save.assert_called_once_with(10,'転勤条件','情報なし','転勤なし')

    def test_schema_requires_confirmed_rule_result_and_context_receives_facts(self):
        import jsonschema
        from services.job_matching_ai_service import matching_response_schema
        from services.job_matching_evaluation_service import load_ai_matching_context
        with user_scope(1):
            service.save_confirmation_result(10,'転勤条件','不明','転勤なし')
            context=load_ai_matching_context(10)
        self.assertEqual(context['job']['confirmed_information'][0]['result_text'],'転勤なし')
        context['confirmed_rule_items']=[dict(item_name='転勤条件',hope_group='location_transfer',weight=3)]
        schema=matching_response_schema(context)
        with self.assertRaises(jsonschema.ValidationError): jsonschema.validate({'items':[]},schema)
        item=dict(category='hope_condition',evaluation_group='',item_name='転勤条件',judgment='一致',weight=3,hope_group='location_transfer',reason='転勤なし希望に合致',evidence='本人確認：転勤なし',is_major_required_mismatch=False)
        jsonschema.validate({'items':[],'confirmed_rules':{'confirmed_0':item}},schema)

    def test_confirmed_result_replaces_old_rule_and_preserves_weight(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import Mock
        from services import job_matching_evaluation_service as evaluation
        from services.job_matching_rule_service import MatchItemResult
        groups={'location_transfer':[MatchItemResult('転勤条件','要確認',3,'情報なし')]}
        context={'job':{'confirmed_information':[dict(item_name='転勤条件',result_text='転勤なし')]}, 'user_matching_information':{'hope_conditions':{'希望':'転勤なし'}}}
        item=dict(category='hope_condition',evaluation_group='',item_name='転勤条件',judgment='一致',weight=3,hope_group='location_transfer',reason='転勤なし希望に合致',evidence='確認：転勤なし',is_major_required_mismatch=False)
        client=Mock()
        client.responses.create.return_value=SimpleNamespace(status='completed',output_text=json.dumps({'items':[], 'confirmed_rules':{'confirmed_0':item}}))
        with user_scope(1), patch('services.job_matching_ai_service.OpenAI',return_value=client), patch.object(evaluation,'load_ai_matching_context',return_value=context), patch.object(evaluation,'evaluate_rule_hope_groups',return_value=groups):
            service.save_confirmation_result(10,'転勤条件','情報なし','転勤なし')
            result=evaluation.evaluate_complete_job_matching(10)
        self.assertEqual(result.rule_hope_groups['location_transfer'],[])
        self.assertEqual(result.semantic_evaluation.items[0].judgment,'一致')
        self.assertEqual(result.semantic_evaluation.items[0].weight,3)
        self.assertNotIn('情報なし',result.evaluation.confirmation_points)

    def test_saving_new_information_retries_only_its_failed_evaluation(self):
        c=get_connection()
        c.execute("INSERT INTO user_job_match_evaluations(user_id,job_id,evaluation_status) VALUES (1,10,'failed')")
        c.execute("INSERT INTO user_job_match_evaluations(user_id,job_id,evaluation_status) VALUES (2,11,'failed')")
        c.commit(); c.close()
        with user_scope(1): service.save_confirmation_result(10,'転勤条件','','転勤なし')
        c=get_connection()
        try:
            own=c.execute('SELECT is_stale,evaluation_status FROM user_job_match_evaluations WHERE job_id=10').fetchone()
            other=c.execute('SELECT evaluation_status FROM user_job_match_evaluations WHERE job_id=11').fetchone()
            self.assertEqual((own['is_stale'],own['evaluation_status']),(1,'ready'))
            self.assertEqual(other['evaluation_status'],'failed')
        finally: c.close()
