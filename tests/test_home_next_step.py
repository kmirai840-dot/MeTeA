"""ホーム案内の優先順位・保存状態の変化・利用者分離を検証する。"""
from datetime import date, timedelta
from types import SimpleNamespace as NS
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from constants.work_values import WORK_STYLE_QUESTIONS
from services.home_next_step_service import choose_next_step, render_next_step_html, NextStep
from database.repositories.home_progress_repository import get_home_progress

TODAY = date(2026, 9, 13)

def complete_progress(**overrides):
    counts = dict(basic_info=1, hope_conditions=1, hope_occupation=1, hope_location=1,
                  hope_employment_type=1, job_hunting_axis=1, career=1)
    counts.update({'rank_' + k:3 for k in ('important_value','rewarding_scene','strength_environment')})
    counts.update({'style_' + q['question_type']:1 for q in WORK_STYLE_QUESTIONS})
    counts.update(overrides)
    return dict(counts=counts, drafts=[])

def view(days=1, status='pending', active=True):
    return dict(application=NS(id=10,status='active' if active else 'closed',phase_category='面接',current_phase='一次面接予定'),
                job=NS(company_name='テスト企業'), milestones=[NS(id=1,status=status,scheduled_date=(TODAY+timedelta(days=days)).isoformat(),title='面接',detail_name='',milestone_type='一次面接')])

class NextStepRulesTest(unittest.TestCase):
    def test_new_user_and_saved_basic(self):
        state={'counts':{},'drafts':[]}
        self.assertEqual(choose_next_step(state,[],TODAY).href,'?page=basic_info')
        state['counts']['basic_info']=1
        self.assertEqual(choose_next_step(state,[],TODAY).href,'?page=hope_conditions')

    def test_values_need_each_ranking_and_each_answer(self):
        state=complete_progress()
        state['counts']['rank_important_value']=2
        self.assertEqual(choose_next_step(state,[],TODAY).href,'?page=work_values')
        state['counts']['rank_important_value']=3
        del state['counts']['style_'+WORK_STYLE_QUESTIONS[0]['question_type']]
        self.assertEqual(choose_next_step(state,[],TODAY).href,'?page=work_values')

    def test_latest_saved_draft_resumes_even_when_formally_saved(self):
        state=complete_progress();state['drafts']=['unrelated','work_values','basic_info']
        self.assertEqual(choose_next_step(state,[],TODAY).href,'?page=work_values')

    def test_due_task_precedes_draft_and_oldest_due_wins(self):
        state=complete_progress();state['drafts']=['work_values']
        result=choose_next_step(state,[view(3),view(-2)],TODAY)
        self.assertEqual(result.reason,'deadline')
        self.assertIn('9/11',result.detail)
        self.assertIn('application_id=10',result.href)

    def test_today_seven_day_boundary_completed_and_closed(self):
        for days in (0,7):
            self.assertEqual(choose_next_step(complete_progress(),[view(days)],TODAY).reason,'deadline')
        for candidate in (view(8),view(-2,status='completed'),view(-2,status='cancelled'),view(-2,status='postponed')):
            self.assertEqual(choose_next_step(complete_progress(),[candidate],TODAY).reason,'application')
        self.assertEqual(choose_next_step(complete_progress(),[view(-2,active=False)],TODAY).reason,'register_job')

    def test_invalid_date_is_not_a_deadline(self):
        candidate=view();candidate['milestones'][0].scheduled_date='bad'
        self.assertEqual(choose_next_step(complete_progress(),[candidate],TODAY).reason,'application')

    def test_active_application_precedes_missing_profile(self):
        candidate=view(30);candidate['application'].current_phase='一次面接結果待ち'
        result=choose_next_step({'counts':{},'drafts':[]},[candidate],TODAY)
        self.assertEqual(result.reason,'application');self.assertIn('結果が届いたら',result.detail)

    def test_job_decision_and_history_branches(self):
        for counts,reason in [({},'register_job'),({'jobs':1,'undecided_jobs':1},'compare'),
            ({'jobs':1,'application_intents':1},'application_intent'),
            ({'jobs':1,'applications':2},'review'),({'jobs':1},'more_jobs')]:
            with self.subTest(reason=reason):self.assertEqual(choose_next_step(complete_progress(**counts),[],TODAY).reason,reason)

    def test_user_text_is_escaped(self):
        html=render_next_step_html(NextStep('x','<script>','" & <img>','<go>','?page=application_list&application_id=10'))
        self.assertNotIn('<script>',html);self.assertIn('&lt;img&gt;',html);self.assertIn('&amp;application_id=10',html)

class HomeProgressIsolationTest(unittest.TestCase):
    def setUp(self):
        from database.initialize import initialize_database
        from database.connection import get_connection
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        env=patch.dict(os.environ,{'METEA_DATABASE_BACKEND':'sqlite','METEA_DATABASE_PATH':str(Path(self.tmp.name)/'test.db'),'METEA_AUTH_MODE':'legacy','METEA_REQUIRE_AUTH':'true'})
        env.start();self.addCleanup(env.stop)
        initialize_database()
        db=get_connection();db.execute('INSERT INTO users(id) VALUES (2)');db.commit();db.close()

    def test_isolation_saved_drafts_decisions_and_deleted_jobs(self):
        from services.current_user_service import user_scope
        from database.access_control import DataAccessDenied
        from database.repositories.draft_repository import save_draft
        from database.repositories.job_repository import create_job
        from database.repositories.job_evaluation_repository import save_job_application_decision
        from database.connection import get_connection
        from models import Job, JobApplicationDecision
        with user_scope(1):
            job_id=create_job(1,Job(company_name='利用者1'))
            save_draft(1,'work_values',{'text':'本人の下書き'})
            result=get_home_progress(1)
            self.assertEqual(result['drafts'],['work_values'])
            self.assertEqual(result['counts']['undecided_jobs'],1)
            save_job_application_decision(1,JobApplicationDecision(job_id=job_id,decision_status='条件を確認して応募'))
            self.assertEqual(get_home_progress(1)['counts']['application_intents'],1)
            save_job_application_decision(1,JobApplicationDecision(job_id=job_id,decision_status='応募しない'))
            self.assertEqual(get_home_progress(1)['counts']['undecided_jobs'],0)
            with self.assertRaises(DataAccessDenied):get_home_progress(2)
        with user_scope(2):
            self.assertEqual(get_home_progress(2)['counts']['jobs'],0)
            self.assertEqual(get_home_progress(2)['drafts'],[])
        db=get_connection();db.execute("UPDATE user_jobs SET deleted_at=CURRENT_TIMESTAMP WHERE id=?",(job_id,));db.commit();db.close()
        with user_scope(1):self.assertEqual(get_home_progress(1)['counts']['jobs'],0)

if __name__=='__main__':unittest.main()
