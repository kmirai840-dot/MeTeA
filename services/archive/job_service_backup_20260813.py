"""求人情報の入力チェックと保存処理を担当する。"""

from models import Job

from database.repositories.job_repository import (
    create_job,
    get_job,
    get_jobs,
    update_job,
    delete_job,
)

from services.current_user_service import (
    get_current_user_id,
)


# ========================================
# 入力チェック
# ========================================

def validate_job(
    job: Job,
) -> list[str]:
    """求人情報の入力内容をチェックする。"""

    errors: list[str] = []

    # 求人を識別するための最低限の情報
    if (
        not job.company_name.strip()
        and not job.job_title.strip()
    ):
        errors.append(
            "会社名または求人名を入力してください。"
        )

    return errors


def find_duplicate_job_id(
    job: Job,
) -> int | None:
    """同一求人として扱う登録済み求人を探す。"""

    jobs = get_jobs(
        get_current_user_id()
    )

    for job_id, saved_job in jobs:
        same_company = (
            saved_job.company_name.strip()
            == job.company_name.strip()
        )

        same_occupation = (
            saved_job.occupation.strip()
            == job.occupation.strip()
        )

        same_source = (
            saved_job.source_name.strip()
            == job.source_name.strip()
        )

        if (
            same_company
            and same_occupation
            and same_source
        ):
            return job_id

    return None


# ========================================
# 新規保存
# ========================================

def save_job_data(
    job: Job,
) -> tuple[int | None, list[str]]:
    """求人情報を確認して新規保存する。"""

    errors = validate_job(job)

    if errors:
        return None, errors

    duplicate_job_id = find_duplicate_job_id(
        job
    )

    if duplicate_job_id is not None:
        updated = update_job(
            user_id=get_current_user_id(),
            job_id=duplicate_job_id,
            job=job,
        )

        if not updated:
            return None, [
                "既存求人を更新できませんでした。"
            ]

        return duplicate_job_id, []

    job_id = create_job(
        user_id=get_current_user_id(),
        job=job,
    )

    return job_id, []


# ========================================
# 一覧取得
# ========================================

def load_jobs(
) -> list[tuple[int, Job]]:
    """登録済み求人を取得する。"""

    return get_jobs(
        get_current_user_id()
    )


# ========================================
# 1件取得
# ========================================

def load_job(
    job_id: int,
) -> Job | None:
    """指定した求人を取得する。"""

    return get_job(
        user_id=get_current_user_id(),
        job_id=job_id,
    )


# ========================================
# 更新
# ========================================

def update_job_data(
    job_id: int,
    job: Job,
) -> list[str]:
    """求人情報を確認して更新する。"""

    errors = validate_job(job)

    if errors:
        return errors

    updated = update_job(
        user_id=get_current_user_id(),
        job_id=job_id,
        job=job,
    )

    if not updated:
        return [
            "更新対象の求人が見つかりませんでした。"
        ]

    return []


# ========================================
# 削除
# ========================================

def delete_job_data(
    job_id: int,
) -> bool:
    """指定した求人を削除する。"""

    return delete_job(
        user_id=get_current_user_id(),
        job_id=job_id,
    )