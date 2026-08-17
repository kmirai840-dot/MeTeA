"""求人の確認項目に対する利用者判断を管理する。"""

from hashlib import sha256

from database.repositories.job_confirmation_repository import (
    delete_job_confirmation_resolution,
    get_job_confirmation_resolutions,
    save_job_confirmation_resolution,
)
from services.current_user_service import get_current_user_id


CONFIRMATION_STATUS_NOT_REQUIRED = "not_required"


def build_confirmation_item_key(
    item_name: str,
    item_reason: str,
) -> str:
    """項目名と理由から、再現可能な項目キーを作る。"""

    normalized_text = (
        f"{item_name.strip()}|{item_reason.strip()}"
    )

    return sha256(
        normalized_text.encode("utf-8")
    ).hexdigest()


def load_job_confirmation_resolutions(
    job_id: int,
) -> dict[str, str]:
    """現在の利用者が保存した判断状態を取得する。"""

    return get_job_confirmation_resolutions(
        user_id=get_current_user_id(),
        job_id=job_id,
    )


def mark_confirmation_not_required(
    job_id: int,
    item_name: str,
    item_reason: str,
) -> None:
    """指定項目を確認不要として保存する。"""

    item_key = build_confirmation_item_key(
        item_name,
        item_reason,
    )

    save_job_confirmation_resolution(
        user_id=get_current_user_id(),
        job_id=job_id,
        item_key=item_key,
        item_name=item_name.strip(),
        item_reason=item_reason.strip(),
        status=CONFIRMATION_STATUS_NOT_REQUIRED,
    )


def restore_confirmation_item(
    job_id: int,
    item_key: str,
) -> None:
    """確認不要判断を取り消して確認一覧へ戻す。"""

    delete_job_confirmation_resolution(
        user_id=get_current_user_id(),
        job_id=job_id,
        item_key=item_key,
    )