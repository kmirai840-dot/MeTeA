"""求人AIマッチング評価全体の流れを管理する。"""

import json
from dataclasses import asdict, dataclass
from typing import Any

from models import (
    JobAISemanticEvaluation,
    JobMatchEvaluation,
)
from services.career_service import (
    load_career_data,
)
from services.hope_condition_service import (
    load_hope_conditions_data,
)
from services.job_hunting_axis_service import (
    load_job_hunting_axis_data,
)
from services.job_matching_ai_service import (
    DEFAULT_AI_MODEL,
    request_ai_semantic_evaluation,
)
from services.job_matching_context_service import (
    build_ai_matching_context,
)
from services.job_service import load_job
from services.work_values_service import (
    load_work_values_data,
)
from services.basic_info_service import (
    load_basic_info,
)
from services.job_commute_service import (
    load_current_job_commute,
)
from services.job_matching_rule_evaluation_service import (
    evaluate_rule_hope_groups,
)
from services.job_matching_rule_service import (
    EVALUATION_RULE_VERSION,
    MATCH,
    MISMATCH,
    NEEDS_CONFIRMATION,
    MatchItemResult,
)
from services.job_matching_score_service import (
    SemanticScoreSummary,
    calculate_combined_score_summary,
    convert_semantic_items_by_category,
    merge_rule_and_semantic_hope_groups,
)


class JobMatchingEvaluationError(ValueError):
    """AIマッチング評価を開始できない場合のエラー。"""


def load_ai_matching_context(
    job_id: int,
) -> dict[str, Any]:
    """求人IDからAI評価用の入力情報を作成する。"""

    if job_id <= 0:
        raise JobMatchingEvaluationError(
            "求人IDが正しくありません"
        )

    job = load_job(
        job_id
    )

    if job is None:
        raise JobMatchingEvaluationError(
            "指定された求人が見つかりません"
        )

    (
        hope_condition,
        hope_items,
    ) = load_hope_conditions_data()

    (
        work_value_rankings,
        work_value_details,
        work_style_answers,
    ) = load_work_values_data()

    job_hunting_axes = (
        load_job_hunting_axis_data()
    )

    careers = load_career_data()

    return build_ai_matching_context(
        job=job,
        hope_condition=hope_condition,
        hope_items=hope_items,
        work_value_rankings=(
            work_value_rankings
        ),
        work_value_details=(
            work_value_details
        ),
        work_style_answers=(
            work_style_answers
        ),
        job_hunting_axes=job_hunting_axes,
        careers=careers,
    )


def evaluate_job_semantics(
    job_id: int,
    model_name: str = DEFAULT_AI_MODEL,
) -> JobAISemanticEvaluation:
    """入力情報を集めてOpenAIの意味判定を実行する。"""

    matching_context = load_ai_matching_context(
        job_id
    )

    return request_ai_semantic_evaluation(
        job_id=job_id,
        matching_context=matching_context,
        model_name=model_name,
    )


@dataclass(frozen=True)
class CompleteJobMatchingResult:
    """求人のルール判定・AI判定・点数をまとめた結果。"""

    evaluation: JobMatchEvaluation
    semantic_evaluation: (
        JobAISemanticEvaluation
    )
    rule_hope_groups: dict[
        str,
        list[MatchItemResult],
    ]
    score_summary: SemanticScoreSummary


def format_result_items(
    items: list[MatchItemResult],
    judgment: str,
) -> str:
    """指定された判定の表示文章を作成する。"""

    matched_items = [
        item
        for item in items
        if (
            item.weight > 0
            and item.judgment == judgment
        )
    ]

    return "\n".join(
        f"・{item.item_name}：{item.reason}"
        for item in matched_items
    )


def collect_complete_match_items(
    rule_hope_groups: dict[
        str,
        list[MatchItemResult],
    ],
    semantic_evaluation: (
        JobAISemanticEvaluation
    ),
) -> list[MatchItemResult]:
    """ルール判定とAI判定の表示項目を1つにまとめる。"""

    merged_hope_groups = (
        merge_rule_and_semantic_hope_groups(
            rule_group_items=(
                rule_hope_groups
            ),
            evaluation=(
                semantic_evaluation
            ),
        )
    )

    complete_items = []

    for group_items in (
        merged_hope_groups.values()
    ):
        complete_items.extend(
            group_items
        )

    semantic_category_items = (
        convert_semantic_items_by_category(
            semantic_evaluation
        )
    )

    for category_name, category_items in (
        semantic_category_items.items()
    ):
        if category_name == "hope_condition":
            continue

        complete_items.extend(
            category_items
        )

    return complete_items


def build_complete_job_matching_result(
    job_id: int,
    rule_hope_groups: dict[
        str,
        list[MatchItemResult],
    ],
    semantic_evaluation: (
        JobAISemanticEvaluation
    ),
) -> CompleteJobMatchingResult:
    """判定済みデータから画面表示用の最終結果を作成する。"""

    score_summary = (
        calculate_combined_score_summary(
            rule_hope_group_items=(
                rule_hope_groups
            ),
            evaluation=(
                semantic_evaluation
            ),
        )
    )

    complete_items = (
        collect_complete_match_items(
            rule_hope_groups=(
                rule_hope_groups
            ),
            semantic_evaluation=(
                semantic_evaluation
            ),
        )
    )

    matching_points = (
        format_result_items(
            complete_items,
            MATCH,
        )
    )

    partial_matching_points = (
        format_result_items(
            complete_items,
            "一部一致",
        )
    )

    if partial_matching_points:
        if matching_points:
            matching_points = (
                f"{matching_points}\n"
                f"{partial_matching_points}"
            )
        else:
            matching_points = (
                partial_matching_points
            )

    concern_points = format_result_items(
        complete_items,
        MISMATCH,
    )

    confirmation_points = (
        format_result_items(
            complete_items,
            NEEDS_CONFIRMATION,
        )
    )

    category_scores = (
        score_summary.category_scores
    )

    penalty = (
        score_summary
        .major_required_mismatch_penalty
    )

    evaluation_coverage = (
        score_summary.evaluation_coverage
    )

    if score_summary.is_provisional:
        ai_comment = (
            "暫定評価です。"
            "全評価カテゴリの配点のうち、"
            f"現在採点できた割合は"
            f"{evaluation_coverage}%です。"
        )
    else:
        ai_comment = (
            "必要な評価カテゴリをすべて採点した"
            "総合評価です。"
        )

    if penalty > 0:
        ai_comment = (
            f"{ai_comment}\n"
            "求人側重大必須条件の不一致により"
            f"{penalty}点を減点しています。"
        )

    evaluation = JobMatchEvaluation(
        job_id=job_id,
        overall_score=(
            score_summary.final_score
        ),
        hope_condition_score=(
            category_scores.get(
                "hope_condition"
            )
        ),
        work_value_score=(
            category_scores.get(
                "work_value"
            )
        ),
        career_skill_score=(
            category_scores.get(
                "career_skill"
            )
        ),
        required_condition_score=(
            category_scores.get(
                "required_condition"
            )
        ),
        matching_points=matching_points,
        concern_points=concern_points,
        confirmation_points=(
            confirmation_points
        ),
        ai_comment=ai_comment,
        evaluated_at=(
            semantic_evaluation.evaluated_at
        ),
        evaluation_coverage=(
            evaluation_coverage
        ),
        is_provisional=(
            score_summary.is_provisional
        ),
        rule_version=EVALUATION_RULE_VERSION,
        prompt_version=(
            semantic_evaluation.prompt_version
        ),
        model_name=semantic_evaluation.model_name,
        evaluation_result_json=json.dumps(
            asdict(semantic_evaluation),
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    return CompleteJobMatchingResult(
        evaluation=evaluation,
        semantic_evaluation=(
            semantic_evaluation
        ),
        rule_hope_groups=rule_hope_groups,
        score_summary=score_summary,
    )


def evaluate_complete_job_matching(
    job_id: int,
    model_name: str = DEFAULT_AI_MODEL,
) -> CompleteJobMatchingResult:
    """求人IDから最新の総合マッチング評価を実行する。"""

    job = load_job(
        job_id
    )

    if job is None:
        raise JobMatchingEvaluationError(
            "指定された求人が見つかりません"
        )

    (
        hope_condition,
        hope_items,
    ) = load_hope_conditions_data()

    commute_minutes = None

    basic_info = load_basic_info()

    if (
        basic_info is not None
        and basic_info.nearest_station_place_id
        and job.nearest_station
    ):
        commute_check = (
            load_current_job_commute(
                job_id=job_id,
                current_origin_station_place_id=(
                    basic_info
                    .nearest_station_place_id
                ),
                current_destination_station_name=(
                    job.nearest_station
                ),
            )
        )

        if commute_check is not None:
            commute_minutes = (
                commute_check.duration_minutes
            )

    rule_hope_groups = (
        evaluate_rule_hope_groups(
            job=job,
            hope_condition=hope_condition,
            hope_items=hope_items,
            commute_minutes=commute_minutes,
        )
    )

    semantic_evaluation = (
        evaluate_job_semantics(
            job_id=job_id,
            model_name=model_name,
        )
    )

    return build_complete_job_matching_result(
        job_id=job_id,
        rule_hope_groups=(
            rule_hope_groups
        ),
        semantic_evaluation=(
            semantic_evaluation
        ),
    )
