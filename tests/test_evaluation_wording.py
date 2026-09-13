import unittest
from services.job_evaluation_display_service import normalize_matching_points as normalize

class EvaluationWordingTest(unittest.TestCase):
    def test_existing_summary_deduplicates_employment(self):
        text='・雇用形態：求人の雇用形態「正社員」は、希望する雇用形態に含まれています\n・正社員：求人の雇用形態は正社員であり、利用者の必須条件と合致します。\n・勤務地：福岡です。'
        result=normalize(text)
        self.assertEqual(len(result.splitlines()),2)
        self.assertIn('希望する雇用形態「正社員」と求人の雇用形態「正社員」が一致しています',result)
        self.assertEqual(normalize(result),result)
        self.assertEqual(normalize(text.replace('必須条件と合致します。','必要条件を満たすため。')),result)

    def test_preserves_distinct_or_uncertain_conditions(self):
        base='・雇用形態：希望する雇用形態「正社員」と求人の雇用形態「正社員」が一致しています'
        for extra in ('・正社員登用：登用の可能性があります','・正社員：雇用形態は一部一致です','・正社員：雇用形態は不一致です','・正社員：試用期間の雇用形態は一致です'):
            self.assertEqual(normalize(base+'\n'+extra),base+'\n'+extra)
        self.assertEqual(normalize('・正社員：求人の雇用形態と一致します'), '・正社員：求人の雇用形態と一致します')

    def test_no_employment_match_is_unchanged(self):
        self.assertEqual(normalize('・勤務地：一致です'), '・勤務地：一致です')
