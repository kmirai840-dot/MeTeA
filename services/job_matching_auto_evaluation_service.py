"""求人保存後のAIマッチングをバックグラウンドで管理する。"""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

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
from database.repositories.job_evaluation_repository import (
    get_job_match_evaluations,
    set_job_match_evaluation_status,
)
from services.current_user_service import get_current_user_id


AI_EVALUATION_FAILURE_MESSAGE = (
    "求人情報は保存されましたが、"
    "AIマッチング評価を完了できませんでした。"
)


STALE_EVALUATION_BATCH_SIZE = 3
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="metea-ai")
_submission_lock = Lock()
_submitted_jobs: set[tuple[int, int]] = set()


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


def _run_background_evaluation(user_id: int, job_id: int) -> None:
    """1求人を評価し、完了または失敗状態を永続化する。"""

    job_key = (user_id, job_id)
    try:
        set_job_match_evaluation_status(user_id, job_id, "running")
        evaluation, error_message = automatically_evaluate_and_save_job(job_id)
        if evaluation is None or error_message:
            set_job_match_evaluation_status(
                user_id,
                job_id,
                "failed",
                failure_reason=error_message or AI_EVALUATION_FAILURE_MESSAGE,
                increment_retry=True,
            )
            return
        set_job_match_evaluation_status(
            user_id,
            job_id,
            "completed",
            result_notice_pending=True,
        )
    except Exception:
        set_job_match_evaluation_status(
            user_id,
            job_id,
            "failed",
            failure_reason=AI_EVALUATION_FAILURE_MESSAGE,
            increment_retry=True,
        )
    finally:
        with _submission_lock:
            _submitted_jobs.discard(job_key)


def enqueue_job_evaluation(job_id: int, retry: bool = False) -> bool:
    """評価を重複させずバックグラウンドへ登録する。"""

    if job_id <= 0:
        return False
    user_id = get_current_user_id()
    job_key = (user_id, job_id)
    with _submission_lock:
        if job_key in _submitted_jobs:
            return False
        current = get_job_match_evaluations(user_id).get(job_id)
        if current and current.evaluation_status in {"queued", "running"}:
            return False
        if current and current.evaluation_status == "failed" and not retry:
            return False
        _submitted_jobs.add(job_key)
        set_job_match_evaluation_status(user_id, job_id, "queued")
        _executor.submit(_run_background_evaluation, user_id, job_id)
    return True


def enqueue_stale_job_evaluations(
    max_jobs: int = STALE_EVALUATION_BATCH_SIZE,
) -> int:
    """再評価待ち求人を画面を止めずに指定件数まで登録する。"""

    queued = 0
    for job_id in load_current_user_stale_job_ids()[:max(0, max_jobs)]:
        if enqueue_job_evaluation(job_id):
            queued += 1
    return queued


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
