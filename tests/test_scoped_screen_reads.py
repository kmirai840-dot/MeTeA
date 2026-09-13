"""実SQLiteで取得範囲・画面間反映・保存の原子性を確認。実DB/APIには触れない。"""
import unittest
from datetime import date
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import test_user_data_isolation as f
from services.current_user_service import user_scope
from services import application_management_service as management
from services import job_evaluation_service as evaluation
from services.profile_review_data_service import load_profile_review_data, load_profile_statuses
from database.repositories import application_repository as apps, job_repository as jobs
from database.repositories import job_evaluation_repository as evaluations, job_commute_repository as commutes
from database.connection import get_connection
from database.operation import database_operation
import models as m


class ScopedReadTest(unittest.TestCase):
    setUp = f.UserDataIsolationTest.setUp

    def test_selected_ids_never_expand_to_all_or_other_user(self):
        for uid in (1, 2):
            with user_scope(uid):
                own, other = self.records[uid]['job'], self.records[3-uid]['job']
                extra = jobs.create_job(uid, m.Job(company_name='not selected'))
                for loader in (jobs.get_jobs, evaluations.get_job_match_evaluations,
                               evaluations.get_job_application_decisions, commutes.get_job_commute_checks):
                    selected = loader(uid, job_ids=[other, own, own])
                    self.assertEqual(set(dict(selected)), {own})
                    self.assertFalse(loader(uid, job_ids=[]))
                    self.assertFalse(loader(uid, job_ids=[other, 99999]))
                self.assertEqual(dict(jobs.get_jobs(uid, job_ids=[own]))[own], jobs.get_job(uid, own))
                jobs.delete_job(uid, own)
                self.assertFalse(jobs.get_jobs(uid, job_ids=[own]))

    def test_status_and_category_are_fresh_and_share_one_connection(self):
        import database.connection as connection
        for uid in (1,2):
            with user_scope(uid), patch.object(connection, '_open_connection', wraps=connection._open_connection) as opened:
                snapshot = load_profile_review_data('career')
                opened.assert_called_once()
                self.assertIn(f'person-{uid}', str(snapshot['data']))
                self.assertNotIn(f'person-{3-uid}', str(snapshot))
                self.assertEqual(snapshot['statuses']['career'], (True, '1社'))
            with user_scope(uid):
                f.career.save_careers(uid, [])
                self.assertEqual(load_profile_statuses()['career'], (False, '未登録'))

    def test_decision_and_application_roll_back_together_then_save_once(self):
        with user_scope(1):
            jid = jobs.create_job(1, m.Job(company_name='atomic'))
            decision = m.JobApplicationDecision(job_id=jid, decision_status='応募する')
            with patch.object(management, 'save_activity', side_effect=RuntimeError('failure')):
                with self.assertRaises(RuntimeError):
                    evaluation.save_job_application_decision_data(decision)
            self.assertNotIn(jid, evaluations.get_job_application_decisions(1))
            self.assertFalse([a for a in apps.get_applications(1) if a.job_id == jid])
            evaluation.save_job_application_decision_data(decision)
            evaluation.save_job_application_decision_data(decision)
            saved = [a for a in apps.get_applications(1) if a.job_id == jid]
            self.assertEqual(len(saved), 1)
            self.assertEqual(len(apps.get_phase_history(saved[0].id)), 1)
            self.assertEqual(len(apps.get_activities(saved[0].id)), 1)
            self.assertIn(jid, [v['job'].id if hasattr(v['job'],'id') else v['application'].job_id for v in management.load_application_views()])

    def test_concurrent_application_creation_does_not_duplicate_history(self):
        with user_scope(1):
            jid = jobs.create_job(1, m.Job(company_name='concurrent'))
        def create():
            with user_scope(1):
                return management.ensure_application_from_decision(jid, '応募する')
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(ids[0], ids[1])
        with user_scope(1):
            self.assertEqual(len(apps.get_phase_history(ids[0])), 1)

    def test_preparation_defaults_preserve_edits_and_skip_second_read(self):
        with user_scope(1):
            aid = self.records[1]['application']
            items = management.load_preparation_items(aid, '一次面接')
            selected = next(i for i in items if not i.is_custom)
            selected.content = '保存した回答'
            apps.save_preparation(selected)
            # 競合した初期作成も回答を上書きしない。
            from dataclasses import replace
            apps.insert_preparation_defaults(aid, [replace(selected, content='')])
            with patch.object(management, 'get_preparations', wraps=apps.get_preparations) as read:
                again = management.load_preparation_items(aid, '一次面接')
                read.assert_called_once()
            self.assertEqual(next(i for i in again if i.id == selected.id).content, '保存した回答')
            templates = management.load_global_preparation_templates()
            with patch.object(management, 'get_user_preparation_templates', wraps=apps.get_user_preparation_templates) as read:
                self.assertEqual(management.load_global_preparation_templates(), templates)
                read.assert_called_once()
            with self.assertRaises(PermissionError):
                management.load_preparation_items(self.records[2]['application'], '一次面接')

    def test_report_filters_cohort_but_keeps_later_selection_events(self):
        with user_scope(1):
            aid = self.records[1]['application']
            app = apps.get_application(1, aid)
            app.application_date = '2026-08-05'
            apps.save_application(app)
            apps.add_phase_history(aid, '一次面接通過', '選考中', '通過', '一次面接')
            with patch.object(management, 'get_phase_history', wraps=apps.get_phase_history) as history:
                result = management.selection_pass_report(date(2026,8,1), date(2026,8,31))
                self.assertEqual(history.call_args.kwargs['application_ids'], {aid})
            with patch.object(management, 'get_phase_history', wraps=apps.get_phase_history) as history:
                management.selection_pass_report(date(2025,1,1), date(2025,1,31))
                self.assertEqual(history.call_args.kwargs['application_ids'], set())
            self.assertEqual(result['summary']['total'], 1)
            self.assertEqual(result['overall']['一次面接']['passed'], 1)

    def test_comparison_rule_results_match_previous_calculation(self):
        from services.job_comparison_data_service import load_comparison_data
        from pages.job_comparison import load_rule_comparison_data
        with user_scope(1), patch('services.job_comparison_data_service.load_hope_conditions_data', return_value=(None, [])), patch('pages.job_comparison.load_hope_conditions_data', return_value=(None, [])):
            jid = jobs.create_job(1, m.Job(company_name='second'))
            ids = [jid, self.records[1]['job'], self.records[2]['job']]
            snapshot = load_comparison_data(ids)
            self.assertEqual([jid for jid,_ in snapshot['selected_jobs']], ids[:2])
            self.assertEqual(snapshot['rule_data'], load_rule_comparison_data(snapshot['selected_jobs']))
