"""求人AIマッチングへ渡す入力情報を組み立てる。"""

from typing import Any

from constants.work_values import WORK_STYLE_QUESTIONS, WORK_STYLE_SCORE_LABELS

from models import (
    Career,
    CareerHistory,
    HopeCondition,
    HopeConditionItem,
    Job,
    JobHuntingAxis,
    WorkStyleAnswer,
    WorkValueDetail,
    WorkValueRanking,
)


def remove_empty_values(
    value: Any,
) -> Any:
    """空文字や空配列をAI入力から取り除く。"""

    if isinstance(value, dict):
        cleaned_dict = {}

        for key, item_value in value.items():
            cleaned_value = remove_empty_values(
                item_value
            )

            if cleaned_value not in (
                "",
                None,
                [],
                {},
            ):
                cleaned_dict[key] = cleaned_value

        return cleaned_dict

    if isinstance(value, list):
        cleaned_list = []

        for item_value in value:
            cleaned_value = remove_empty_values(
                item_value
            )

            if cleaned_value not in (
                "",
                None,
                [],
                {},
            ):
                cleaned_list.append(
                    cleaned_value
                )

        return cleaned_list

    if isinstance(value, str):
        return value.strip()

    return value


def build_job_context(
    job: Job,
) -> dict[str, Any]:
    """求人票のうち意味判定に必要な情報を作成する。"""

    context = {
        "company": {
            "company_name": job.company_name,
            "industry": job.industry,
            "business_description": (
                job.business_description
            ),
        },
        "position": {
            "job_title": job.job_title,
            "occupation": job.occupation,
            "department": job.department,
            "job_summary": job.job_summary,
            "job_details": job.job_details,
            "responsibility_scope": (
                job.responsibility_scope
            ),
            "customers": job.customers,
            "internal_stakeholders": (
                job.internal_stakeholders
            ),
            "external_partners": (
                job.external_partners
            ),
            "goals_kpi": job.goals_kpi,
            "expected_results": (
                job.expected_results
            ),
        },
        "required_conditions": {
            "required_experience": (
                job.required_experience
            ),
            "required_skills": (
                job.required_skills
            ),
            "required_qualifications": (
                job.required_qualifications
            ),
        },
        "preferred_conditions": {
            "preferred_experience": (
                job.preferred_experience
            ),
            "preferred_skills": (
                job.preferred_skills
            ),
            "desired_personality": (
                job.desired_personality
            ),
        },
        "organizational_culture": {
            "explicit_culture": (
                job.organizational_culture
            ),
        },
        "work_environment": {
            "employment_type": (
                job.employment_type
            ),
            "work_style": job.work_style,
            "flextime": job.flextime,
            "training_program": (
                job.training_program
            ),
            "qualification_support": (
                job.qualification_support
            ),
        },
    }

    return remove_empty_values(
        context
    )


def build_hope_condition_context(
    hope_condition: HopeCondition | None,
    hope_items: list[HopeConditionItem],
) -> dict[str, Any]:
    """利用者の希望条件のうち意味判定対象を作成する。"""

    condition_context: dict[str, Any] = {}

    if hope_condition is not None:
        condition_context = {
            "other_jobs": (
                hope_condition.other_jobs
            ),
            "other_conditions": (
                hope_condition.other_conditions
            ),
        }

    item_context = [
        {
            "condition_type": item.condition_type,
            "condition_value": (
                item.condition_value
            ),
            "priority": item.priority,
            "rank": item.rank,
            "detail_value": item.detail_value,
        }
        for item in hope_items
    ]

    return remove_empty_values(
        {
            "free_text_conditions": (
                condition_context
            ),
            "condition_items": item_context,
        }
    )


def build_work_value_context(
    rankings: list[WorkValueRanking],
    details: list[WorkValueDetail],
    work_style_answers: list[WorkStyleAnswer],
) -> dict[str, Any]:
    """利用者の価値観・仕事の進め方を作成する。"""

    ranking_context = [
        {
            "question_type": (
                ranking.question_type
            ),
            "selected_value": (
                ranking.selected_value
            ),
            "priority_rank": (
                ranking.priority_rank
            ),
            "custom_value": (
                ranking.custom_value
            ),
        }
        for ranking in rankings
    ]

    detail_context = [
        {
            "detail_type": detail.detail_type,
            "detail_text": detail.detail_text,
        }
        for detail in details
    ]

    work_style_context = [
        {
            "question_type": (
                answer.question_type
            ),
            "answer_score": (
                answer.answer_score
            ),
            "answer_label": WORK_STYLE_SCORE_LABELS.get(
                answer.answer_score,
                "",
            ),
            "question_title": next(
                (
                    question["title"]
                    for question in WORK_STYLE_QUESTIONS
                    if question["question_type"] == answer.question_type
                ),
                "",
            ),
            "left_text": next(
                (
                    question["left_text"]
                    for question in WORK_STYLE_QUESTIONS
                    if question["question_type"] == answer.question_type
                ),
                "",
            ),
            "right_text": next(
                (
                    question["right_text"]
                    for question in WORK_STYLE_QUESTIONS
                    if question["question_type"] == answer.question_type
                ),
                "",
            ),
        }
        for answer in work_style_answers
    ]

    return remove_empty_values(
        {
            "rankings": ranking_context,
            "details": detail_context,
            "work_style_answers": (
                work_style_context
            ),
        }
    )


def build_job_hunting_axis_context(
    axes: list[JobHuntingAxis],
) -> list[dict[str, Any]]:
    """利用者の就活の軸を順位付きで作成する。"""

    context = [
        {
            "axis_title": axis.axis_title,
            "axis_description": (
                axis.axis_description
            ),
            "priority_rank": (
                axis.priority_rank
            ),
        }
        for axis in axes
    ]

    return remove_empty_values(
        context
    )


def build_career_context(
    careers: list[
        tuple[
            Career,
            list[CareerHistory],
        ]
    ],
) -> list[dict[str, Any]]:
    """会社名を除外して職務経験を作成する。"""

    career_context = []

    for career, histories in careers:
        history_context = [
            {
                "department": history.department,
                "position": history.position,
                "occupation": history.occupation,
                "start_year": history.start_year,
                "start_month": history.start_month,
                "end_year": history.end_year,
                "end_month": history.end_month,
                "job_description": (
                    history.job_description
                ),
                "achievements": (
                    history.achievements
                ),
            }
            for history in histories
        ]

        career_context.append(
            {
                "employment_type": (
                    career.employment_type
                ),
                "industry": career.industry,
                "start_year": career.start_year,
                "start_month": career.start_month,
                "end_year": career.end_year,
                "end_month": career.end_month,
                "is_current": career.is_current,
                "histories": history_context,
            }
        )

    return remove_empty_values(
        career_context
    )


def build_ai_matching_context(
    job: Job,
    hope_condition: HopeCondition | None,
    hope_items: list[HopeConditionItem],
    work_value_rankings: list[
        WorkValueRanking
    ],
    work_value_details: list[WorkValueDetail],
    work_style_answers: list[WorkStyleAnswer],
    job_hunting_axes: list[JobHuntingAxis],
    careers: list[
        tuple[
            Career,
            list[CareerHistory],
        ]
    ],
) -> dict[str, Any]:
    """AIマッチングに渡す入力情報全体を作成する。"""

    return remove_empty_values(
        {
            "job": build_job_context(
                job
            ),
            "user_matching_information": {
                "hope_conditions": (
                    build_hope_condition_context(
                        hope_condition=(
                            hope_condition
                        ),
                        hope_items=hope_items,
                    )
                ),
                # 順位回答と自由記述は軸候補の材料に限定する。
                # 仕事の進め方10問だけは、確定軸と分けてAI採点する。
                "work_style_answers": (
                    build_work_value_context(
                        rankings=[],
                        details=[],
                        work_style_answers=work_style_answers,
                    ).get("work_style_answers", [])
                ),
                "job_hunting_axes": (
                    build_job_hunting_axis_context(
                        job_hunting_axes
                    )
                ),
                "career": (
                    build_career_context(
                        careers
                    )
                ),
            },
        }
    )
