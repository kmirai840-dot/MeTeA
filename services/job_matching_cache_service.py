"""AIマッチング評価キャッシュの状態を管理する。"""

from database.repositories.job_evaluation_repository import (
    get_stale_job_match_evaluation_ids,
    mark_job_match_evaluation_stale,
    mark_job_match_evaluations_stale,
)
from services.current_user_service import (
    get_current_user_id,
)


def invalidate_current_user_job_evaluations(
    reason: str,
) -> int:
    """現在の利用者の保存済み評価を再評価待ちにする。"""

    return mark_job_match_evaluations_stale(
        user_id=get_current_user_id(),
        stale_reason=reason,
    )


def invalidate_current_user_job_evaluation(
    job_id: int,
    reason: str,
) -> bool:
    """現在の利用者の指定求人を再評価待ちにする。"""

    return mark_job_match_evaluation_stale(
        user_id=get_current_user_id(),
        job_id=job_id,
        stale_reason=reason,
    )


def load_current_user_stale_job_ids(
) -> list[int]:
    """現在の利用者の再評価待ち求人IDを取得する。"""

    return get_stale_job_match_evaluation_ids(
        user_id=get_current_user_id()
    )