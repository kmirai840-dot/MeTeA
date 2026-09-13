import unittest
from unittest.mock import patch
import test_confirmation_results as existing
from services import job_confirmation_service as service
from services.current_user_service import user_scope
from database.access_control import DataAccessDenied

class PersonalJudgmentTest(unittest.TestCase):
    setUp = existing.ConfirmationResultsTest.setUp

    def test_judgment_and_fact_are_independent_and_owned(self):
        change=dict(item_name='転勤条件',item_reason='不明',accepted=True,score_adjustment=1)
        with user_scope(1), patch.object(service,'_invalidate_confirmation') as invalidate:
            self.assertEqual(service.save_confirmation_decisions(10,[change]),1)
            row=service.load_confirmation_records(10)[0]
            self.assertEqual((row['status'],row['result_text'],row['accepted'],row['score_adjustment']),('pending','',1,1))
            invalidate.assert_not_called()
            self.assertEqual(service.save_confirmation_decisions(10,[change]),0)
            service.save_confirmation_decisions(10,[dict(change,result_text='転勤あり')])
            invalidate.assert_called_once()
            row=service.load_confirmation_records(10)[0]
            self.assertEqual((row['status'],row['accepted'],row['score_adjustment']),('confirmed',1,1))
            service.save_confirmation_decisions(10,[dict(change,accepted=False,score_adjustment=-1)])
            row=service.load_confirmation_records(10)[0]
            self.assertEqual((row['result_text'],row['accepted'],row['score_adjustment']),('転勤あり',0,0))
            self.assertEqual(invalidate.call_count,1)
            service.save_confirmation_decisions(10,[dict(change,remove_fact=True)])
            row=service.load_confirmation_records(10)[0]
            self.assertEqual((row['status'],row['result_text'],row['accepted']),('pending','',1))
            self.assertEqual(invalidate.call_count,2)
        with user_scope(2):
            with self.assertRaises(DataAccessDenied): service.save_confirmation_decisions(10,[change])

    def test_legacy_and_caps_and_atomicity(self):
        with user_scope(1):
            service.mark_confirmation_not_required(10,'転勤条件','不明')
            row=service.load_confirmation_records(10)[0]
            self.assertEqual((row['accepted'],row['score_adjustment']),(0,0))
            changes=[dict(item_name='別項目',item_reason='',result_text='確認した事実',accepted=True,score_adjustment=1),dict(item_name='不正',item_reason='',accepted=True,score_adjustment=99)]
            with self.assertRaises(ValueError): service.save_confirmation_decisions(10,changes)
            self.assertEqual(len(service.load_confirmation_records(10)),1)
        records=[dict(item_name=str(n),accepted=1,score_adjustment=1) for n in range(10)]
        self.assertEqual(service.personal_score_adjustment(records),5)
        self.assertEqual(service.personal_score_adjustment(records[:1]*10),1)
        self.assertEqual(service.personal_score_adjustment([dict(r,score_adjustment=-1) for r in records]),-5)

    def test_form_submits_fact_and_personal_judgment_together(self):
        from streamlit.testing.v1 import AppTest
        script="""from ui.job_confirmation_results import render_batch_confirmation_form
render_batch_confirmation_form(10,[dict(item_key='a',item_name='転勤条件',reason='不明')],[],[],lambda:None)
"""
        with patch.object(service,'save_confirmation_decisions',return_value=1) as save, patch('ui.job_evaluation_area.refresh_saved_confirmation_details'):
            app=AppTest.from_string(script, default_timeout=30).run()
            app.selectbox[0].select('転勤あり')
            app.checkbox[0].check()
            app.selectbox[1].select('加点')
            app.button[0].click().run()
            self.assertFalse(app.exception)
            change=save.call_args.args[1][0]
            self.assertEqual((change['result_text'],change['accepted'],change['score_adjustment']),('転勤条件：転勤あり',True,1))
            self.assertEqual(len(app.button),1)
