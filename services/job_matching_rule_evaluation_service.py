"""求人と希望条件をPythonルールでまとめて判定する。"""

from models import (
    HopeCondition,
    HopeConditionItem,
    Job,
)
from services.job_matching_rule_service import (
    HOPE_CONDITION_GROUP_WEIGHTS,
    MatchItemResult,
    calculate_grouped_match_rate,
    calculate_weighted_match_rate,
    evaluate_annual_holidays_condition,
    evaluate_commute_time,
    evaluate_employment_type_condition,
    evaluate_end_time_condition,
    evaluate_holiday_pattern_condition,
    evaluate_location_condition,
    evaluate_night_work_condition,
    evaluate_overtime_condition,
    evaluate_salary_condition,
    evaluate_shift_work_condition,
    evaluate_start_time_condition,
    evaluate_transfer_condition,
)


def build_job_schedule_description(
    job: Job,
) -> str:
    """シフト・夜勤判定に使う求人記載をまとめる。"""

    description_parts = [
        job.work_style,
        job.holidays,
        job.start_time,
        job.end_time,
        job.job_summary,
        *job.job_details,
    ]

    return "\n".join(
        part.strip()
        for part in description_parts
        if (
            isinstance(part, str)
            and part.strip()
        )
    )


def create_empty_hope_groups(
) -> dict[str, list[MatchItemResult]]:
    """空の希望条件グループを作成する。"""

    return {
        group_name: []
        for group_name
        in HOPE_CONDITION_GROUP_WEIGHTS
    }


def evaluate_rule_hope_groups(
    job: Job,
    hope_condition: HopeCondition | None,
    hope_items: list[HopeConditionItem],
    commute_minutes: int | None,
) -> dict[str, list[MatchItemResult]]:
    """ルール判定結果を希望条件グループ別に作成する。"""

    group_items = create_empty_hope_groups()

    if hope_condition is None:
        return group_items

    schedule_description = (
        build_job_schedule_description(
            job
        )
    )

    group_items[
        "location_transfer"
    ].extend(
        [
            evaluate_location_condition(
                job_prefecture=job.prefecture,
                job_municipality=(
                    job.municipality
                ),
                hope_condition_items=(
                    hope_items
                ),
            ),
            evaluate_commute_time(
                duration_minutes=(
                    commute_minutes
                ),
                commute_limit_minutes=(
                    hope_condition.commute_minutes
                ),
                priority=(
                    hope_condition.commute_priority
                ),
            ),
            evaluate_transfer_condition(
                job_transfer_required=(
                    job.transfer_required
                ),
                desired_transfer_condition=(
                    hope_condition.transfer_condition
                ),
                priority=(
                    hope_condition.transfer_priority
                ),
            ),
        ]
    )

    group_items[
        "salary_employment"
    ].extend(
        [
            evaluate_salary_condition(
                job=job,
                minimum_salary=(
                    hope_condition.minimum_salary
                ),
                desired_salary=(
                    hope_condition.desired_salary
                ),
                ideal_salary=(
                    hope_condition.ideal_salary
                ),
            ),
            evaluate_employment_type_condition(
                job_employment_type=(
                    job.employment_type
                ),
                hope_condition_items=(
                    hope_items
                ),
            ),
        ]
    )

    group_items[
        "working_time_holiday"
    ].extend(
        [
            evaluate_overtime_condition(
                job_overtime=job.overtime,
                overtime_limit=(
                    hope_condition.overtime_limit
                ),
                priority=(
                    hope_condition.overtime_priority
                ),
            ),
            evaluate_start_time_condition(
                job_start_time=job.start_time,
                desired_start_time=(
                    hope_condition.start_time
                ),
                priority=(
                    hope_condition.start_time_priority
                ),
                job_flextime=job.flextime,
            ),
            evaluate_end_time_condition(
                job_end_time=job.end_time,
                desired_end_time=(
                    hope_condition.end_time
                ),
                priority=(
                    hope_condition.end_time_priority
                ),
                job_flextime=job.flextime,
            ),
            evaluate_shift_work_condition(
                job_description=(
                    schedule_description
                ),
                desired_condition=(
                    hope_condition.shift_work
                ),
                priority=(
                    hope_condition.shift_work_priority
                ),
            ),
            evaluate_night_work_condition(
                job_description=(
                    schedule_description
                ),
                desired_condition=(
                    hope_condition.night_work
                ),
                priority=(
                    hope_condition.night_work_priority
                ),
            ),
            evaluate_annual_holidays_condition(
                job_annual_holidays=(
                    job.annual_holidays
                ),
                desired_annual_holidays=(
                    hope_condition.annual_holidays
                ),
                priority=(
                    hope_condition.annual_holiday_priority
                ),
            ),
            evaluate_holiday_pattern_condition(
                job_holidays=job.holidays,
                hope_condition_items=(
                    hope_items
                ),
            ),
        ]
    )

    return group_items


def calculate_rule_hope_group_scores(
    group_items: dict[
        str,
        list[MatchItemResult],
    ],
) -> dict[str, int | None]:
    """希望条件グループごとの一致率を計算する。"""

    return {
        group_name: (
            calculate_weighted_match_rate(
                group_items.get(
                    group_name,
                    [],
                )
            )
        )
        for group_name
        in HOPE_CONDITION_GROUP_WEIGHTS
    }


def calculate_rule_hope_score(
    group_items: dict[
        str,
        list[MatchItemResult],
    ],
) -> int | None:
    """ルール判定による希望条件一致率を計算する。"""

    group_scores = (
        calculate_rule_hope_group_scores(
            group_items
        )
    )

    return calculate_grouped_match_rate(
        group_scores=group_scores,
        group_weights=(
            HOPE_CONDITION_GROUP_WEIGHTS
        ),
    )