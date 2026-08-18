"""職務経歴・スキル25点の3要素分割に関する回帰テスト。"""

import unittest

from models import AISemanticMatchItem, JobAISemanticEvaluation
from services.job_matching_ai_service import (
    JobMatchingAIResultError,
    filter_unavailable_categories,
    parse_ai_item,
)
from services.job_matching_score_service import calculate_semantic_score_summary


def career_item(group: str, judgment: str) -> AISemanticMatchItem:
    return AISemanticMatchItem(
        category="career_skill",
        evaluation_group=group,
        item_name=group,
        judgment=judgment,
        reason="判定理由",
    )


class JobMatchingCareerSkillTest(unittest.TestCase):
    def test_three_components_are_weighted_10_10_5(self) -> None:
        evaluation = JobAISemanticEvaluation(
            job_id=1,
            items=[
                career_item("direct_experience", "一致"),
                career_item("portable_skill", "一部一致"),
                career_item("achievement_reproducibility", "不一致"),
            ],
        )

        summary = calculate_semantic_score_summary(evaluation)

        self.assertEqual(summary.career_component_scores["direct_experience"], 100)
        self.assertEqual(summary.career_component_scores["portable_skill"], 60)
        self.assertEqual(summary.career_component_scores["achievement_reproducibility"], 0)
        self.assertEqual(summary.category_scores["career_skill"], 64)
        self.assertEqual(summary.evaluation_coverage, 25)

    def test_unknown_component_is_excluded_from_coverage(self) -> None:
        evaluation = JobAISemanticEvaluation(
            job_id=1,
            items=[
                career_item("direct_experience", "要確認"),
                career_item("portable_skill", "一致"),
                career_item("achievement_reproducibility", "一致"),
            ],
        )

        summary = calculate_semantic_score_summary(evaluation)

        self.assertEqual(summary.category_scores["career_skill"], 100)
        self.assertEqual(summary.evaluation_coverage, 15)

    def test_career_unknown_is_kept_for_confirmation(self) -> None:
        payload = {
            "items": [{
                "category": "career_skill",
                "evaluation_group": "direct_experience",
                "judgment": "要確認",
            }]
        }
        result = filter_unavailable_categories(
            payload,
            {"user_matching_information": {"career": [{"company": "A"}]}},
        )
        self.assertEqual(len(result["items"]), 1)

    def test_career_group_is_required(self) -> None:
        raw_item = {
            "category": "career_skill",
            "item_name": "業務改善",
            "judgment": "一致",
            "reason": "経験を活かせます",
            "evidence": "業務改善を担当",
        }
        with self.assertRaises(JobMatchingAIResultError):
            parse_ai_item(raw_item, 0)

        raw_item["evaluation_group"] = "portable_skill"
        self.assertEqual(
            parse_ai_item(raw_item, 0).evaluation_group,
            "portable_skill",
        )


if __name__ == "__main__":
    unittest.main()
