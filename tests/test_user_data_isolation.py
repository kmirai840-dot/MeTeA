"""2利用者の保存・更新・削除・ID差替えを実SQLiteで検証する。実DB/APIは使わない。"""
from __future__ import annotations

import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import MISSING, fields
from datetime import date
from pathlib import Path
from unittest.mock import patch

import models as m
from database.access_control import DataAccessDenied
from database.connection import get_connection
from database.initialize import initialize_database
from database.repositories import (
    application_repository as app, career_repository as career,
    draft_repository as draft, home_activity_repository as home,
    hope_condition_repository as hope, job_commute_repository as commute,
    job_confirmation_repository as confirmation, job_evaluation_repository as evaluation,
    job_hunting_axis_repository as axis, job_repository as jobs,
    job_source_repository as source, user_repository as profile,
    work_values_repository as values,
)
from services import current_user_service as identity
from services import job_matching_auto_evaluation_service as background
from services import application_management_service as management
from services import job_evaluation_service


def model(cls, label, **overrides):
    data = {}
    for f in fields(cls):
        if f.default is not MISSING or f.default_factory is not MISSING:
            continue
        data[f.name] = (
            label if f.type is str else 1 if f.type is int else
            False if f.type is bool else date(2000, 1, 1) if f.type is date else None
        )
    data.update(overrides)
    return cls(**data)


class UserDataIsolationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {
            "METEA_DATABASE_BACKEND": getattr(self, 'database_backend', 'sqlite'),
            "METEA_DATABASE_PATH": str(Path(self.tmp.name) / "test.db"),
            "METEA_REQUIRE_AUTH": "true",
            "METEA_AUTH_MODE": "legacy",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        initialize_database()
        with get_connection() as db:
            db.execute("INSERT INTO users(id) VALUES (2)")
        db.close()
        self.records = {}
        for uid in (1, 2):
            with identity.user_scope(uid):
                label = f"person-{uid}"
                profile.save_user_profile(uid, model(m.BasicInfo, label), "basic")
                hope.save_hope_conditions(uid, model(m.HopeCondition, label),
                                          [model(m.HopeConditionItem, label)], "hope")
                axis.save_job_hunting_axes(uid, [model(m.JobHuntingAxis, label)], "axis")
                values.save_work_values(uid, [model(m.WorkValueRanking, label)],
                                        [model(m.WorkValueDetail, label)],
                                        [model(m.WorkStyleAnswer, label)], "values")
                career.save_careers(uid, [(model(m.Career, label),
                                          [model(m.CareerHistory, label)])])
                draft.save_draft(uid, "same-form", {"text": label})
                job = jobs.create_job(uid, m.Job(company_name=label, job_details=[label]))
                src = source.create_job_source(uid, job, m.JobSource(source_name=label))
                commute.save_job_commute_check(uid, model(m.JobCommuteCheck, label, job_id=job))
                confirmation.save_job_confirmation_resolution(uid, job, "key", label, label, "resolved")
                evaluation.save_job_match_evaluation(uid, m.JobMatchEvaluation(job_id=job, ai_comment=label))
                evaluation.save_job_application_decision(uid, m.JobApplicationDecision(job_id=job, memo=label))
                application = app.save_application(m.ApplicationRecord(user_id=uid, job_id=job, notes=label))
                milestone = app.save_milestone(m.ApplicationMilestone(application_id=application, title=label))
                preparation = app.save_preparation(m.ApplicationPreparation(
                    application_id=application, theme_key="same-key", content=label, is_custom=True))
                template = app.save_user_preparation_template(m.UserPreparationTemplate(
                    user_id=uid, theme_key="same-key", content=label, is_custom=True))
                app.add_phase_history(application, label, label)
                app.save_activity(m.ApplicationActivity(application_id=application, title=label))
                home.save_general_activity(uid, "test", label)
                self.records[uid] = dict(job=job, source=src, application=application,
                                         milestone=milestone, preparation=preparation, template=template)

    def dump(self):
        db = get_connection()
        try:
            return "\n".join(db.iterdump())
        finally:
            db.close()

    def test_all_25_tables_have_two_users_or_their_children(self):
        db = get_connection()
        try:
            tables = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            self.assertEqual(len(tables), 25)
            for table in tables:
                with self.subTest(table=table):
                    self.assertGreaterEqual(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], 2)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        finally:
            db.close()

    def test_personal_data_and_children_are_separate(self):
        for uid in (1, 2):
            with identity.user_scope(uid):
                label, other = f"person-{uid}", f"person-{3-uid}"
                results = [profile.get_user_profile(uid), hope.get_hope_condition(uid),
                           hope.get_hope_condition_items(uid), axis.get_job_hunting_axes(uid),
                           values.get_work_values(uid), career.get_careers(uid), draft.get_draft(uid, "same-form"),
                           jobs.get_jobs(uid), app.get_applications(uid), app.get_milestones(),
                           app.get_phase_history(), app.get_activities(), app.get_user_preparation_templates(uid)]
                for result in results:
                    with self.subTest(uid=uid, result=type(result).__name__):
                        self.assertIn(label, repr(result))
                        self.assertNotIn(other, repr(result))
                self.assertNotIn(other, repr(home.get_home_activities(uid, 100)))
                own = self.records[uid]
                self.assertIn(label, repr(source.get_job_sources(uid, own["job"])))
                self.assertIn(label, repr(commute.get_job_commute_check(uid, own["job"])))
                self.assertIn(label, repr(evaluation.get_job_match_evaluations(uid)))
                self.assertIn(label, repr(evaluation.get_job_application_decisions(uid)))
                self.assertEqual(set(confirmation.get_job_confirmation_resolutions(uid, own["job"])), {"key"})

    def test_forged_user_id_is_rejected_for_every_personal_domain(self):
        before = self.dump()
        with identity.user_scope(1):
            calls = [lambda: profile.get_user_profile(2), lambda: hope.get_hope_condition(2),
                     lambda: axis.get_job_hunting_axes(2), lambda: values.get_work_values(2),
                     lambda: career.get_careers(2), lambda: draft.get_draft(2, "same-form"),
                     lambda: draft.save_draft(2, "same-form", {"text": "attack"}),
                     lambda: draft.delete_draft(2, "same-form"), lambda: jobs.get_jobs(2),
                     lambda: jobs.create_job(2, m.Job()), lambda: app.get_applications(2),
                     lambda: app.get_user_preparation_templates(2), lambda: home.get_home_activities(2),
                     lambda: home.save_general_activity(2, "test", "attack"),
                     lambda: evaluation.get_job_match_evaluations(2)]
            for index, call in enumerate(calls):
                with self.subTest(index=index), self.assertRaises(DataAccessDenied):
                    call()
        self.assertEqual(before, self.dump())

    def test_other_users_job_cannot_be_read_updated_or_deleted(self):
        other = self.records[2]
        before = self.dump()
        with identity.user_scope(1):
            self.assertIsNone(jobs.get_job(1, other["job"]))
            self.assertFalse(jobs.update_job(1, other["job"], m.Job(company_name="attack")))
            self.assertFalse(jobs.delete_job(1, other["job"]))
            self.assertEqual(source.get_job_sources(1, other["job"]), [])
            self.assertIsNone(source.create_job_source(1, other["job"], m.JobSource()))
            self.assertFalse(source.set_primary_job_source(1, other["job"], other["source"]))
            self.assertFalse(source.delete_job_source(1, other["job"], other["source"]))
        self.assertEqual(before, self.dump())

    def test_other_job_cannot_be_linked_to_my_evaluation_or_application(self):
        other = self.records[2]["job"]
        before = self.dump()
        with identity.user_scope(1):
            calls = [lambda: evaluation.save_job_match_evaluation(1, m.JobMatchEvaluation(job_id=other)),
                     lambda: evaluation.save_job_application_decision(1, m.JobApplicationDecision(job_id=other)),
                     lambda: evaluation.set_job_match_evaluation_status(1, other, "running"),
                     lambda: commute.save_job_commute_check(1, model(m.JobCommuteCheck, "attack", job_id=other)),
                     lambda: confirmation.save_job_confirmation_resolution(1, other, "key", "x", "x", "x"),
                     lambda: app.save_application(m.ApplicationRecord(user_id=1, job_id=other))]
            for index, call in enumerate(calls):
                with self.subTest(index=index), self.assertRaises(DataAccessDenied):
                    call()
        self.assertEqual(before, self.dump())

    def test_other_application_children_cannot_be_read_or_created(self):
        other = self.records[2]["application"]
        before = self.dump()
        with identity.user_scope(1):
            self.assertIsNone(app.get_application(1, other))
            calls = [lambda: app.get_milestones(other), lambda: app.get_activities(other),
                     lambda: app.get_phase_history(other), lambda: app.get_preparations(other),
                     lambda: app.add_phase_history(other, "attack", "attack"),
                     lambda: app.save_milestone(m.ApplicationMilestone(application_id=other)),
                     lambda: app.save_activity(m.ApplicationActivity(application_id=other)),
                     lambda: app.save_preparation(m.ApplicationPreparation(application_id=other)),
                     lambda: management.load_preparation_items(other, "interview"),
                     lambda: management.add_manual_activity(other, "attack", "attack", "2026-09-10")]
            for index, call in enumerate(calls):
                with self.subTest(index=index), self.assertRaises(DataAccessDenied):
                    call()
        self.assertEqual(before, self.dump())

    def test_child_id_and_parent_id_cannot_be_swapped(self):
        own, other = self.records[1], self.records[2]
        before = self.dump()
        with identity.user_scope(1):
            calls = [lambda: app.save_milestone(m.ApplicationMilestone(
                        id=other["milestone"], application_id=own["application"])),
                     lambda: app.save_milestone(m.ApplicationMilestone(
                        application_id=own["application"], rescheduled_from_id=other["milestone"])),
                     lambda: app.delete_milestone(other["milestone"]),
                     lambda: app.save_preparation(m.ApplicationPreparation(
                        id=other["preparation"], application_id=own["application"])),
                     lambda: app.delete_preparation(other["preparation"], own["application"]),
                     lambda: app.save_application(m.ApplicationRecord(
                        id=other["application"], user_id=1, job_id=own["job"])),
                     lambda: app.save_user_preparation_template(m.UserPreparationTemplate(
                        id=other["template"], user_id=1, theme_key="same-key")),
                     lambda: app.delete_user_preparation_template(other["template"], 1),
                     lambda: management.delete_milestone_data(m.ApplicationMilestone(id=other["milestone"]))]
            for index, call in enumerate(calls):
                with self.subTest(index=index), self.assertRaises(DataAccessDenied):
                    call()
        self.assertEqual(before, self.dump())

    def test_personal_overwrite_and_delete_leave_other_user_unchanged(self):
        with identity.user_scope(1):
            profile.save_user_profile(1, model(m.BasicInfo, "changed"), "same-form")
            hope.save_hope_conditions(1, model(m.HopeCondition, "changed"), [], "same-form")
            axis.save_job_hunting_axes(1, [], "same-form")
            values.save_work_values(1, [], [], [], "same-form")
            career.save_careers(1, [])
            self.assertIsNone(draft.get_draft(1, "same-form"))
            self.assertEqual(axis.get_job_hunting_axes(1), [])
        with identity.user_scope(2):
            for result in [profile.get_user_profile(2), hope.get_hope_condition(2),
                           hope.get_hope_condition_items(2), axis.get_job_hunting_axes(2),
                           values.get_work_values(2), career.get_careers(2), draft.get_draft(2, "same-form")]:
                self.assertIn("person-2", repr(result))
                self.assertNotIn("changed", repr(result))

    def test_owner_can_update_and_delete_application_children(self):
        own, other = self.records[1], self.records[2]
        with identity.user_scope(1):
            milestone = app.get_milestones(own["application"])[0]
            milestone.title = "changed"
            app.save_milestone(milestone)
            self.assertEqual(app.get_milestones(own["application"])[0].title, "changed")
            self.assertTrue(app.delete_milestone(own["milestone"]))
            self.assertTrue(app.delete_preparation(own["preparation"], own["application"]))
            self.assertTrue(app.delete_user_preparation_template(own["template"], 1))
        with identity.user_scope(2):
            self.assertEqual(len(app.get_milestones(other["application"])), 1)
            self.assertEqual(len(app.get_preparations(other["application"])), 1)
            self.assertEqual(len(app.get_user_preparation_templates(2)), 1)

    def test_deleted_parent_is_not_accessible(self):
        own = self.records[1]
        with identity.user_scope(1):
            jobs.delete_job(1, own["job"])
            self.assertEqual(job_evaluation_service.load_job_match_evaluations(), {})
            self.assertEqual(evaluation.get_job_application_decisions(1), {})
            self.assertEqual(evaluation.get_stale_job_match_evaluation_ids(1), [])
            for call in [lambda: app.get_preparations(own["application"]),
                         lambda: app.save_milestone(m.ApplicationMilestone(application_id=own["application"])),
                         lambda: evaluation.set_job_match_evaluation_status(1, own["job"], "running")]:
                with self.assertRaises(DataAccessDenied):
                    call()

    def test_background_workers_use_correct_user_and_do_not_leak_context(self):
        def fake_evaluate(job_id):
            uid = identity.get_current_user_id()
            job = jobs.get_job(uid, job_id)
            self.assertIsNotNone(job)
            result = m.JobMatchEvaluation(job_id=job_id, ai_comment=f"evaluated-{uid}")
            evaluation.save_job_match_evaluation(uid, result)
            return result, ""

        with patch.object(background, "automatically_evaluate_and_save_job", side_effect=fake_evaluate):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(background._run_background_evaluation, uid, self.records[uid]["job"])
                           for uid in (1, 2)]
                for future in futures:
                    future.result()
                with self.assertRaises(identity.UserIdentityRequired):
                    pool.submit(identity.get_current_user_id).result()
        for uid in (1, 2):
            with identity.user_scope(uid):
                row = evaluation.get_job_match_evaluations(uid)[self.records[uid]["job"]]
                self.assertEqual(row.ai_comment, f"evaluated-{uid}")
                self.assertEqual(row.evaluation_status, "completed")

    def test_background_exception_resets_context(self):
        with patch.object(background, "automatically_evaluate_and_save_job", side_effect=RuntimeError("test")):
            background._run_background_evaluation(2, self.records[2]["job"])
        with self.assertRaises(identity.UserIdentityRequired):
            identity.get_current_user_id()
        with identity.user_scope(2):
            self.assertEqual(evaluation.get_job_match_evaluations(2)[self.records[2]["job"]].evaluation_status, "failed")

    def test_new_connection_and_initialization_preserve_saved_data(self):
        initialize_database()
        for uid in (1, 2):
            with identity.user_scope(uid):
                self.assertEqual(draft.get_draft(uid, "same-form"), {"text": f"person-{uid}"})
                self.assertEqual(len(jobs.get_jobs(uid)), 1)


class UserContextTest(unittest.TestCase):
    def test_user_switch_and_logout_clear_previous_forms(self):
        state = {identity.CURRENT_USER_SESSION_KEY: 1, "job_id": 99, "draft": "private", "app_authenticated": True}
        with patch.object(identity, "_streamlit_session_state", return_value=state):
            identity.set_current_user_id(2)
            self.assertEqual(state, {identity.CURRENT_USER_SESSION_KEY: 2, "app_authenticated": True})
            identity.clear_current_user_id()
            self.assertEqual(state, {})

    def test_same_user_keeps_form_state(self):
        state = {identity.CURRENT_USER_SESSION_KEY: 2, "draft": "keep"}
        with patch.object(identity, "_streamlit_session_state", return_value=state):
            identity.set_current_user_id(2)
            self.assertEqual(state["draft"], "keep")

    def test_strict_mode_never_defaults_to_user_one(self):
        with patch.dict(os.environ, {"METEA_REQUIRE_AUTH": "true"}), patch.object(identity, "_streamlit_session_state", return_value={}):
            with self.assertRaises(identity.UserIdentityRequired):
                identity.get_current_user_id()
            with identity.user_scope(2):
                self.assertEqual(identity.get_current_user_id(), 2)
            with self.assertRaises(identity.UserIdentityRequired):
                identity.get_current_user_id()

    def test_invalid_identity_is_rejected(self):
        for value in (0, -1, True, 1.5, "invalid"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                with identity.user_scope(value):
                    pass


if __name__ == "__main__":
    unittest.main()
