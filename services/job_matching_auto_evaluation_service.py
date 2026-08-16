"""求人保存後のAIマッチング自動評価を管理する。"""

from models import JobMatchEvaluation
from services.job_evaluation_service import (
    save_job_match_evaluation_data,
)
from services.job_matching_cache_service import (
    load_current_user_stale_job_ids,
)
from services.job_matching_evaluation_service import (
    evaluate_complete_job_matching,
)


AI_EVALUATION_FAILURE_MESSAGE = (
    "求人情報は保存されましたが、"
    "AIマッチング評価を完了できませんでした。"
)


STALE_EVALUATION_BATCH_SIZE = 3


def automatically_evaluate_and_save_job(
    job_id: int,
) -> tuple[
    JobMatchEvaluation | None,
    str,
]:
    """求人を自動評価し、成功した評価を保存する。"""

    if job_id <= 0:
        return (
            None,
            AI_EVALUATION_FAILURE_MESSAGE,
        )

    try:
        complete_result = (
            evaluate_complete_job_matching(
                job_id=job_id
            )
        )

        evaluation = (
            complete_result.evaluation
        )

        save_errors = (
            save_job_match_evaluation_data(
                evaluation
            )
        )

    except Exception:
        return (
            None,
            AI_EVALUATION_FAILURE_MESSAGE,
        )

    if save_errors:
        return (
            None,
            AI_EVALUATION_FAILURE_MESSAGE,
        )

    return evaluation, ""


def automatically_refresh_stale_job_evaluations(
    max_jobs: int = STALE_EVALUATION_BATCH_SIZE,
) -> tuple[int, int, list[int]]:
    """再評価待ち求人を指定件数まで自動評価する。"""

    normalized_max_jobs = max(
        0,
        max_jobs,
    )

    stale_job_ids = (
        load_current_user_stale_job_ids()
    )

    target_job_ids = stale_job_ids[
        :normalized_max_jobs
    ]

    refreshed_count = 0
    failed_job_ids: list[int] = []

    for job_id in target_job_ids:
        evaluation, error_message = (
            automatically_evaluate_and_save_job(
                job_id=job_id,
            )
        )

        if (
            evaluation is None
            or error_message
        ):
            failed_job_ids.append(
                job_id
            )
            continue

        refreshed_count += 1

    remaining_count = len(
        load_current_user_stale_job_ids()
    )

    return (
        refreshed_count,
        remaining_count,
        failed_job_ids,
    )