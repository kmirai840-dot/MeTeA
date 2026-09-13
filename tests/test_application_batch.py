import unittest
from contextlib import ExitStack
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from models import ApplicationRecord,Job
from pages import application_management as page

class ApplicationBatchTest(unittest.TestCase):
 def test_table_opens_modal_with_its_own_row_snapshot(self):
  detail=dict(application=ApplicationRecord(id=9,job_id=3),job=Job(company_name='テスト'),milestones=[],next_milestone=None)
  page._test_table_views=[detail]
  try:
   with patch.object(page,'_render_application_detail_dialog') as opened:
    app=AppTest.from_string("import streamlit as st\nfrom pages import application_management as p\nst.session_state['schedule_dialog_application_id']=9\np._render_application_table(p._test_table_views,'week')",default_timeout=30).run()
    self.assertFalse(app.exception)
    opened.assert_called_once_with(9,[detail])
  finally:
   del page._test_table_views

 def test_modal_consumes_list_snapshot_once_then_reads_fresh(self):
  detail=dict(application=ApplicationRecord(id=9,job_id=3),job=Job(company_name='テスト'),milestones=[])
  holder=[detail]
  with patch.object(page,'load_application_detail',return_value=detail) as read, patch('ui.job_form_visibility.install_visibility'):
   # 同じholderを次回の実行にも渡す。初期情報が繰り返し使われないことを確認。
   page._test_snapshot_holder=holder
   try:
    app=AppTest.from_string('from pages import application_management as p\np.render_application_detail_page(9,embedded=True,snapshot_holder=p._test_snapshot_holder)',default_timeout=30).run()
    self.assertFalse(app.exception)
    read.assert_not_called()
    app.run()
    self.assertFalse(app.exception)
    read.assert_called_once_with(9)
   finally:
    del page._test_snapshot_holder

 def test_selection_and_schedule_submit_current_inputs_once(self):
  detail=dict(application=ApplicationRecord(id=9,job_id=3),job=Job(company_name='テスト'),milestones=[])
  with ExitStack() as stack:
   stack.enter_context(patch.object(page,'load_application_detail',return_value=detail))
   stack.enter_context(patch('ui.job_form_visibility.install_visibility'))
   stack.enter_context(patch.object(page,'_rerun_application_detail'))
   register=stack.enter_context(patch.object(page,'register_selection_result'))
   schedule=stack.enter_context(patch.object(page,'add_milestone_data'))
   app=AppTest.from_string('from pages.application_management import render_application_detail_page\nrender_application_detail_page(9,embedded=True)',default_timeout=30).run()
   self.assertFalse(app.exception)
   self.assertGreaterEqual(len(app.get('form')),3)
   app.selectbox(key='selection_result_9').set_value('通過')
   app.selectbox(key='selection_next_stage_9').set_value(page.SELECTION_STAGES[1])
   app.checkbox(key='next_date_decided_9').check()
   register.assert_not_called()
   next(b for b in app.button if b.label=='結果を登録').click().run()
   self.assertFalse(app.exception)
   register.assert_called_once()
   self.assertEqual(register.call_args.args[2],'通過')
   self.assertEqual(register.call_args.args[3],page.SELECTION_STAGES[1])
   self.assertTrue(register.call_args.args[4])
   app.text_input(key='unified_milestone_title_9').set_value('入力中の予定')
   schedule.assert_not_called()
   app.button(key='unified_milestone_add_9').click().run()
   self.assertFalse(app.exception)
   schedule.assert_called_once()
   self.assertEqual(schedule.call_args.args[0].title,'入力中の予定')
