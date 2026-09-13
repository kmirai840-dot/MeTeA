"""求人の確認項目に対する利用者判断を管理する。"""

from hashlib import sha256

from database.repositories.job_confirmation_repository import (
    delete_job_confirmation_resolution,
    get_job_confirmation_resolutions,
    save_job_confirmation_resolution,
)
from services.current_user_service import get_current_user_id
from database.operation import database_operation
from database.repositories.job_confirmation_repository import get_job_confirmation_records
from services.job_matching_cache_service import invalidate_current_user_job_evaluation
from database.connection import get_connection


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


@database_operation
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
    was_confirmed = any(row['item_key'] == item_key and row['status'] == 'confirmed' for row in load_confirmation_records(job_id))

    save_job_confirmation_resolution(
        user_id=get_current_user_id(),
        job_id=job_id,
        item_key=item_key,
        item_name=item_name.strip(),
        item_reason=item_reason.strip(),
        status=CONFIRMATION_STATUS_NOT_REQUIRED,
    )
    if was_confirmed:
        _invalidate_confirmation(job_id, '確認結果が取り消されました。')


@database_operation
def restore_confirmation_item(
    job_id: int,
    item_key: str,
) -> None:
    """確認不要判断を取り消して確認一覧へ戻す。"""

    was_confirmed = any(row['item_key'] == item_key and row['status'] == 'confirmed' for row in load_confirmation_records(job_id))
    delete_job_confirmation_resolution(
        user_id=get_current_user_id(),
        job_id=job_id,
        item_key=item_key,
    )
    if was_confirmed:
        _invalidate_confirmation(job_id, '確認結果が取り消されました。')


def load_confirmation_records(job_id):
    return get_job_confirmation_records(get_current_user_id(), job_id)


@database_operation
def save_confirmation_result(job_id, item_name, item_reason, result_text):
    text = result_text.strip()
    if not text or len(text) > 2000:
        raise ValueError('確認結果を1〜2000文字で入力してください。')
    key = build_confirmation_item_key(item_name, item_reason)
    previous = next((row for row in load_confirmation_records(job_id) if row['item_key'] == key), None)
    if previous and previous['status'] == 'confirmed' and previous['result_text'] == text:
        return False
    save_job_confirmation_resolution(get_current_user_id(), job_id, key, item_name.strip(), item_reason.strip(), 'confirmed', text)
    _invalidate_confirmation(job_id, '企業・求人元への確認結果が更新されました。')
    return True


def _invalidate_confirmation(job_id, reason):
    invalidate_current_user_job_evaluation(job_id, reason)
    # 確認情報が変わったときは、前回失敗した評価も自動更新できる状態へ戻す。
    connection = get_connection()
    try:
        connection.execute("UPDATE user_job_match_evaluations SET evaluation_status = 'ready' WHERE user_id = ? AND job_id = ? AND evaluation_status = 'failed'", (get_current_user_id(), job_id))
        connection.commit()
    finally:
        connection.close()

@database_operation
def save_confirmation_batch(job_id, changes):
    """一括保存を一つのトランザクションで行い、評価は一度だけ無効化する。"""
    user_id = get_current_user_id()
    previous = {row['item_key']: row for row in load_confirmation_records(job_id)}
    prepared = []
    seen = set()
    for change in changes:
        name, reason = change['item_name'].strip(), change['item_reason'].strip()
        key = build_confirmation_item_key(name, reason)
        status = change.get('status', 'confirmed')
        text = change.get('result_text', '').strip()
        if key in seen:
            raise ValueError('同じ確認項目が重複しています。')
        seen.add(key)
        if status not in {'confirmed', 'not_required', 'restore'}:
            raise ValueError('確認状態を確認してください。')
        if status == 'confirmed' and (not text or len(text) > 2000):
            raise ValueError(f'{name}：確認結果を1〜2000文字で入力してください。')
        prepared.append((key, name, reason, status, text))
    changed = 0
    needs_evaluation = False
    for key, name, reason, status, text in prepared:
        old = previous.get(key)
        if status == 'restore':
            if not old:
                continue
            delete_job_confirmation_resolution(user_id, job_id, key)
        else:
            if old and old['status'] == status and (status != 'confirmed' or old['result_text'] == text):
                continue
            save_job_confirmation_resolution(user_id, job_id, key, name, reason, status, text)
        changed += 1
        needs_evaluation |= status == 'confirmed' or bool(old and old['status'] == 'confirmed')
    if needs_evaluation:
        _invalidate_confirmation(job_id, '企業・求人元への確認結果がまとめて更新されました。')
    return changed
