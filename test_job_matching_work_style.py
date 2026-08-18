"""確定軸25点＋仕事の進め方10点の回帰テスト。"""

import unittest

from models import AISemanticMatchItem, JobAISemanticEvaluation, WorkStyleAnswer
from services.job_hunting_axis_suggestion_service import _work_style_axis
from services.job_matching_context_service import build_work_value_context
from services.job_matching_score_service import calculate_semantic_score_summary


class JobMatchingWorkStyleTest(unittest.TestCase):
    def test_axis_and_work_style_are_weighted_25_and_10(self) -> None:
        evaluation = JobAISemanticEvaluation(
            job_id=1,
            items=[
                AISemanticMatchItem(
                    category="work_value",
                    evaluation_group="confirmed_axis",
                    item_name="確定軸",
                    judgment="一致",
                    reason="一致",
                ),
                AISemanticMatchItem(
                    category="work_value",
                    evaluation_group="work_style",
                    item_name="仕事の進め方",
                    judgment="不一致",
                    reason="不一致",
                ),
            ],
        )

        summary = calculate_semantic_score_summary(evaluation)

        self.assertEqual(summary.work_value_component_scores["confirmed_axis"], 100)
        self.assertEqual(summary.work_value_component_scores["work_style"], 0)
        self.assertEqual(summary.category_scores["work_value"], 71)
        self.assertEqual(summary.evaluation_coverage, 35)
        self.assertEqual(summary.final_score, 71)

    def test_unconfirmed_work_style_is_excluded_from_denominator(self) -> None:
        evaluation = JobAISemanticEvaluation(
            job_id=1,
            items=[
                AISemanticMatchItem(
                    category="work_value",
                    evaluation_group="confirmed_axis",
                    item_name="確定軸",
                    judgment="一致",
                    reason="一致",
                ),
                AISemanticMatchItem(
                    category="work_value",
                    evaluation_group="work_style",
                    item_name="並行作業",
                    judgment="要確認",
                    reason="複数案件をどの程度並行して担当しますか？",
                ),
            ],
        )

        summary = calculate_semantic_score_summary(evaluation)

        self.assertEqual(summary.category_scores["work_value"], 100)
        self.assertEqual(summary.evaluation_coverage, 25)

    def test_work_style_context_contains_both_ends_of_scale(self) -> None:
        context = build_work_value_context(
            rankings=[],
            details=[],
            work_style_answers=[WorkStyleAnswer("starting_method", 1)],
        )
        answer = context["work_style_answers"][0]
        self.assertEqual(answer["left_text"], "事前に計画を立ててから着手する")
        self.assertEqual(answer["right_text"], "まず着手してから調整する")

    def test_extreme_answers_create_only_one_work_style_axis(self) -> None:
        axis = _work_style_axis(
            [
                WorkStyleAnswer("task_management", 1),
                WorkStyleAnswer("consultation_timing", 5),
                WorkStyleAnswer("sharing_timing", 5),
            ]
        )
        self.assertIsNotNone(axis)
        self.assertEqual(axis.axis_title, "自分に合う仕事の進め方を実現する")


if __name__ == "__main__":
    unittest.main()
