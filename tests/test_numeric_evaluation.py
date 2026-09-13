import unittest,json
from dataclasses import asdict,replace,fields
from datetime import date
from models import Job,HopeCondition,BasicInfo,JobCommuteCheck,JobAISemanticEvaluation,AISemanticMatchItem,JobMatchEvaluation
from services.job_matching_rule_service import evaluate_salary_values,evaluate_salary_condition,MATCH,PARTIAL_MATCH,MISMATCH,NEEDS_CONFIRMATION
from services.job_numeric_evaluation_service import rebuild_numeric_evaluation
from services.job_commute_service import commute_job_context

class NumericEvaluationTest(unittest.TestCase):
 def test_salary_ranges(self):
  for lo,hi,expected in [(395,660,PARTIAL_MATCH),(395,449,MISMATCH),(395,450,PARTIAL_MATCH),(500,660,MATCH),(395,None,NEEDS_CONFIRMATION),(660,395,NEEDS_CONFIRMATION)]:
   with self.subTest(lo=lo,hi=hi):self.assertEqual(evaluate_salary_values(lo,450,500,600,hi).judgment,expected)
 def test_explicit_annual_range_beats_monthly_conversion(self):
  j=Job(source_text='報酬(給与賞与) 想定年収:485万円〜660万円',monthly_salary_min='329167',monthly_salary_max='445834')
  result=evaluate_salary_condition(j,450,500,600)
  self.assertEqual(result.judgment,PARTIAL_MATCH);self.assertIn('485〜660',result.reason);self.assertNotIn('395',result.reason)
 def test_explicit_fields_take_precedence_over_source(self):
  j=Job(expected_salary_min='700',expected_salary_max='800',source_text='想定年収:485万円〜660万円')
  self.assertEqual(evaluate_salary_condition(j,450,500,600).judgment,MATCH)
 def test_salary_example_not_used_as_range(self):
  result=evaluate_salary_condition(Job(source_text='年収例:485万円〜660万円'),450,500,600)
  self.assertEqual(result.judgment,NEEDS_CONFIRMATION)
 def test_saved_commute_rebuild_is_idempotent_and_keeps_failure_and_semantics(self):
  values={f.name:('no_preference' if f.name.endswith('_priority') else '') for f in fields(HopeCondition)}
  values.update(minimum_salary=450,desired_salary=500,ideal_salary=600,commute_minutes=50,commute_priority='must',overtime_limit=0,annual_holidays=0,available_date=None)
  h=HopeCondition(**values);j=Job(nearest_station='到着',expected_salary_min='485',expected_salary_max='660')
  b=BasicInfo('試験','利用者','',date(2000,1,1),'','','出発','origin')
  c=JobCommuteCheck(1,'出発','origin','到着',50,commute_job_context(j),'2026-09-13')
  semantic=JobAISemanticEvaluation(1,items=[AISemanticMatchItem('required_condition','Excel',MATCH,'登録済みのスキルが一致')])
  old=JobMatchEvaluation(1,evaluation_result_json=json.dumps(asdict(semantic)),evaluation_status='failed',failure_reason='AI timeout')
  updated=rebuild_numeric_evaluation(old,j,b,h,[],c,set())
  self.assertIn('片道50分',updated.matching_points);self.assertNotIn('電車移動時間',updated.confirmation_points)
  self.assertEqual(updated.failure_reason,'AI timeout');self.assertEqual(updated.evaluation_status,'failed')
  self.assertEqual(json.loads(updated.evaluation_result_json)['items'],asdict(semantic)['items'])
  self.assertIs(rebuild_numeric_evaluation(updated,j,b,h,[],c,set()),updated)
  changed=rebuild_numeric_evaluation(updated,j,replace(b,nearest_station_place_id='other'),h,[],c,set())
  self.assertIn('電車移動時間',changed.confirmation_points)
 def test_invalid_cache_is_preserved(self):
  for payload in ['[]','{}','bad']:
   e=JobMatchEvaluation(1,evaluation_result_json=payload)
   self.assertIs(rebuild_numeric_evaluation(e,Job(),None,None,[],None,set()),e)

 def test_unchanged_view_does_not_reload_numeric_inputs(self):
  from services.job_numeric_evaluation_service import refresh_numeric_evaluations
  from services.job_matching_rule_service import EVALUATION_RULE_VERSION
  from unittest.mock import patch
  e=JobMatchEvaluation(1,rule_version=EVALUATION_RULE_VERSION,evaluation_result_json='{"_numeric_signature":"cached"}')
  with patch('services.basic_info_service.load_basic_info') as load:
   self.assertIs(refresh_numeric_evaluations({1:e})[1],e)
   load.assert_not_called()
