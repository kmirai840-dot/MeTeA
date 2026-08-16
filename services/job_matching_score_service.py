"""AI意味判定結果のカテゴリ点数と減点を計算する。"""

from dataclasses import dataclass

from models import JobAISemanticEvaluation
from services.job_matching_rule_service import (
    CATEGORY_WEIGHTS,
    HOPE_CONDITION_GROUP_WEIGHTS,
    MatchItemResult,
    calculate_grouped_match_rate,
    calculate_overall_score,
    calculate_weighted_match_rate,
)


MAJOR_REQUIRED_MISMATCH_PENALTY = 20
MAX_MAJOR_REQUIRED_MISMATCH_PENALTY = 40


@dataclass(frozen=True)
class SemanticScoreSummary:
    category_scores: dict[str, int | None]
    overall_score_before_penalty: int | None
    major_required_mismatch_count: int
    major_required_mismatch_penalty: int
    final_score: int | None
    evaluation_coverage: int
    is_provisional: bool
    """AI意味判定部分の点数計算結果。"""

    category_scores: dict[
        str,
        int | None,
    ]
    overall_score_before_penalty: int | None
    major_required_mismatch_count: int
    major_required_mismatch_penalty: int
    final_score: int | None


def calculate_evaluation_coverage(
    category_scores: dict[str, int | None],
) -> int:
    """実際に採点できたカテゴリの配点割合を計算する。"""

    available_weight = sum(
        category_weight
        for category, category_weight
        in CATEGORY_WEIGHTS.items()
        if category_scores.get(category) is not None
    )

    total_weight = sum(
        CATEGORY_WEIGHTS.values()
    )

    if total_weight <= 0:
        return 0

    return round(
        available_weight
        / total_weight
        * 100
    )


def convert_semantic_items_by_category(
    evaluation: JobAISemanticEvaluation,
) -> dict[str, list[MatchItemResult]]:
    """AI意味判定をカテゴリ別の計算項目へ変換する。"""

    category_items = {
        category_name: []
        for category_name in CATEGORY_WEIGHTS
    }

    for item in evaluation.items:
        if item.category not in category_items:
            raise ValueError(
                "未対応のAI判定カテゴリです："
                f"{item.category}"
            )

        category_items[item.category].append(
            MatchItemResult(
                item_name=item.item_name,
                judgment=item.judgment,
                weight=item.weight,
                reason=item.reason,
            )
        )

    return category_items


def convert_semantic_hope_items_by_group(
    evaluation: JobAISemanticEvaluation,
) -> dict[str, list[MatchItemResult]]:
    """AI希望条件を内部配点グループ別に変換する。"""

    group_items = {
        group_name: []
        for group_name
        in HOPE_CONDITION_GROUP_WEIGHTS
    }

    for item in evaluation.items:
        if item.category != "hope_condition":
            continue

        if item.hope_group not in group_items:
            raise ValueError(
                "未対応の希望条件グループです："
                f"{item.hope_group}"
            )

        group_items[item.hope_group].append(
            MatchItemResult(
                item_name=item.item_name,
                judgment=item.judgment,
                weight=item.weight,
                reason=item.reason,
            )
        )

    return group_items


def calculate_semantic_hope_score(
    evaluation: JobAISemanticEvaluation,
) -> int | None:
    """AI希望条件を内部配点に従って計算する。"""

    group_items = (
        convert_semantic_hope_items_by_group(
            evaluation
        )
    )

    group_scores = {
        group_name: (
            calculate_weighted_match_rate(
                items
            )
        )
        for group_name, items
        in group_items.items()
    }

    return calculate_grouped_match_rate(
        group_scores=group_scores,
        group_weights=(
            HOPE_CONDITION_GROUP_WEIGHTS
        ),
    )


def calculate_semantic_category_scores(
    evaluation: JobAISemanticEvaluation,
) -> dict[str, int | None]:
    """AI意味判定のカテゴリ別一致率を計算する。"""

    category_items = (
        convert_semantic_items_by_category(
            evaluation
        )
    )

    category_scores = {
        category_name: (
            calculate_weighted_match_rate(
                items
            )
        )
        for category_name, items
        in category_items.items()
        if category_name != "hope_condition"
    }

    category_scores[
        "hope_condition"
    ] = calculate_semantic_hope_score(
        evaluation
    )

    return {
        category_name: category_scores.get(
            category_name
        )
        for category_name in CATEGORY_WEIGHTS
    }


def count_major_required_mismatches(
    evaluation: JobAISemanticEvaluation,
) -> int:
    """重大な求人側応募必須条件不一致を数える。"""

    return sum(
        1
        for item in evaluation.items
        if item.is_major_required_mismatch
    )


def calculate_major_required_penalty(
    mismatch_count: int,
) -> int:
    """重大必須条件不一致の追加減点を計算する。"""

    if mismatch_count < 0:
        raise ValueError(
            "重大必須条件不一致の件数は"
            "0以上である必要があります"
        )

    calculated_penalty = (
        mismatch_count
        * MAJOR_REQUIRED_MISMATCH_PENALTY
    )

    return min(
        calculated_penalty,
        MAX_MAJOR_REQUIRED_MISMATCH_PENALTY,
    )


def apply_major_required_penalty(
    score: int | None,
    penalty: int,
) -> int | None:
    """総合点へ重大必須条件の減点を適用する。"""

    if score is None:
        return None

    if score < 0 or score > 100:
        raise ValueError(
            "総合点は0から100の範囲で"
            "指定してください"
        )

    if penalty < 0:
        raise ValueError(
            "減点値は0以上である必要があります"
        )

    return max(
        0,
        score - penalty,
    )


def calculate_semantic_score_summary(
    evaluation: JobAISemanticEvaluation,
) -> SemanticScoreSummary:
    """AI意味判定部分の点数と減点をまとめて計算する。"""

    category_scores = (
        calculate_semantic_category_scores(
            evaluation
        )
    )

    overall_score_before_penalty = (
        calculate_overall_score(
            category_scores
        )
    )

    mismatch_count = (
        count_major_required_mismatches(
            evaluation
        )
    )

    penalty = (
        calculate_major_required_penalty(
            mismatch_count
        )
    )

    final_score = apply_major_required_penalty(
        score=overall_score_before_penalty,
        penalty=penalty,
    )

    evaluation_coverage = (
        calculate_evaluation_coverage(
            category_scores
        )
    )

    return SemanticScoreSummary(
        category_scores=category_scores,
        overall_score_before_penalty=(
            overall_score_before_penalty
        ),
        major_required_mismatch_count=(
            mismatch_count
        ),
        major_required_mismatch_penalty=(
            penalty
        ),
        final_score=final_score,
        evaluation_coverage=(
            evaluation_coverage
        ),
        is_provisional=(
            evaluation_coverage < 100
        ),
    )


def merge_rule_and_semantic_hope_groups(
    rule_group_items: dict[
        str,
        list[MatchItemResult],
    ],
    evaluation: JobAISemanticEvaluation,
) -> dict[str, list[MatchItemResult]]:
    """ルール判定とAI判定の希望条件を統合する。"""

    merged_groups = {
        group_name: list(
            rule_group_items.get(
                group_name,
                [],
            )
        )
        for group_name
        in HOPE_CONDITION_GROUP_WEIGHTS
    }

    semantic_groups = (
        convert_semantic_hope_items_by_group(
            evaluation
        )
    )

    for group_name in (
        HOPE_CONDITION_GROUP_WEIGHTS
    ):
        merged_groups[group_name].extend(
            semantic_groups.get(
                group_name,
                [],
            )
        )

    return merged_groups


def calculate_combined_hope_score(
    rule_group_items: dict[
        str,
        list[MatchItemResult],
    ],
    evaluation: JobAISemanticEvaluation,
) -> int | None:
    """ルールとAIを統合した希望条件一致率を計算する。"""

    merged_groups = (
        merge_rule_and_semantic_hope_groups(
            rule_group_items=(
                rule_group_items
            ),
            evaluation=evaluation,
        )
    )

    group_scores = {
        group_name: (
            calculate_weighted_match_rate(
                items
            )
        )
        for group_name, items
        in merged_groups.items()
    }

    return calculate_grouped_match_rate(
        group_scores=group_scores,
        group_weights=(
            HOPE_CONDITION_GROUP_WEIGHTS
        ),
    )


def calculate_combined_score_summary(
    rule_hope_group_items: dict[
        str,
        list[MatchItemResult],
    ],
    evaluation: JobAISemanticEvaluation,
) -> SemanticScoreSummary:
    """ルール判定とAI判定を統合して総合点を計算する。"""

    category_scores = (
        calculate_semantic_category_scores(
            evaluation
        )
    )

    category_scores[
        "hope_condition"
    ] = calculate_combined_hope_score(
        rule_group_items=(
            rule_hope_group_items
        ),
        evaluation=evaluation,
    )

    overall_score_before_penalty = (
        calculate_overall_score(
            category_scores
        )
    )

    mismatch_count = (
        count_major_required_mismatches(
            evaluation
        )
    )

    penalty = (
        calculate_major_required_penalty(
            mismatch_count
        )
    )

    final_score = apply_major_required_penalty(
        score=overall_score_before_penalty,
        penalty=penalty,
    )

    evaluation_coverage = (
        calculate_evaluation_coverage(
            category_scores
        )
    )

    return SemanticScoreSummary(
        category_scores=category_scores,
        overall_score_before_penalty=(
            overall_score_before_penalty
        ),
        major_required_mismatch_count=(
            mismatch_count
        ),
        major_required_mismatch_penalty=(
            penalty
        ),
        final_score=final_score,
        evaluation_coverage=(
            evaluation_coverage
        ),
        is_provisional=(
            evaluation_coverage < 100
        ),
    )