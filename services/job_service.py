"""求人情報の入力チェック・重複判定・保存処理を担当する。"""

from dataclasses import fields

from models import (
    Job,
    JobSource,
)

from database.repositories.job_repository import (
    create_job,
    delete_job,
    find_jobs_by_company,
    get_job,
    get_jobs,
    update_job,
)

from services.current_user_service import (
    get_current_user_id,
)

from database.repositories.job_source_repository import (
    create_job_source,
    get_job_sources,
    sync_primary_job_source,
)

# ========================================
# 重複判定結果
# ========================================

DUPLICATE_NONE = "none"
DUPLICATE_EXACT = "exact"
DUPLICATE_DIFFERENT_SOURCE = "different_source"
DUPLICATE_POSSIBLE = "possible"


# ========================================
# 求人同一性の判定結果
# ========================================

JOB_MATCH_SAME = "same"
JOB_MATCH_POSSIBLE = "possible"
JOB_MATCH_NO_MATCH = "no_match"

# ========================================
# 比較表示用ラベル
# ========================================

JOB_FIELD_LABELS = {
    "registration_method": "登録方法",
    "source_url": "求人URL",
    "source_text": "求人票本文",
    "acquired_at": "取得日時",
    "source_type": "紹介経路の種別",
    "source_name": "紹介経路の具体名",
    "company_name": "会社名",
    "job_title": "求人名",
    "job_number": "求人番号",
    "publication_start_date": "掲載開始日",
    "publication_end_date": "掲載終了日",
    "industry": "業種",
    "business_description": "事業内容",
    "employee_count_min": "従業員数（下限）",
    "employee_count_max": "従業員数（上限）",
    "employee_count": "従業員数",
    "established_date": "設立",
    "capital": "資本金",
    "listing_status": "上場区分",
    "occupation": "職種",
    "department": "配属部署",
    "planned_hires": "採用予定人数",
    "recruitment_reason": "募集背景・採用理由",
    "job_summary": "仕事内容・業務概要",
    "job_details": "具体的な業務内容",
    "responsibility_scope": "担当範囲・役割",
    "customers": "顧客・対象者",
    "internal_stakeholders": "社内の関係者",
    "external_partners": "社外の関係者",
    "goals_kpi": "目標・KPI",
    "expected_results": "期待される成果",
    "organizational_culture": "組織風土・企業文化",
    "required_experience": "必須経験",
    "required_skills": "必須スキル",
    "required_qualifications": "必須資格",
    "preferred_experience": "歓迎経験",
    "preferred_skills": "歓迎スキル",
    "desired_personality": "求める人物像",
    "employment_type": "雇用形態",
    "probation_period_status": "試用期間の有無",
    "probation_period_months": "試用期間の月数",
    "probation_period": "試用期間の補足",
    "prefecture": "都道府県",
    "municipality": "市区町村",
    "nearest_station": "最寄駅",
    "transfer_required": "転勤",
    "work_style": "勤務形態・働き方",
    "start_time": "始業時間",
    "end_time": "終業時間",
    "break_minutes": "休憩時間",
    "scheduled_work_hours": "所定労働時間",
    "flextime": "フレックスタイム",
    "overtime": "残業",
    "holidays": "休日・休暇",
    "annual_holidays": "年間休日数",
    "wage_type": "賃金形態",
    "monthly_salary_min": "月給最低額",
    "monthly_salary_max": "月給最高額",
    "base_salary_min": "基本給最低額",
    "base_salary_max": "基本給最高額",
    "fixed_overtime_system": "固定残業制",
    "fixed_overtime_pay_min": "固定残業代最低額",
    "fixed_overtime_pay_max": "固定残業代最高額",
    "overtime_extra_pay": "超過分の追加支給",
    "monthly_salary": "月給",
    "annual_salary": "年収",
    "expected_salary_min": "想定年収（下限）",
    "expected_salary_max": "想定年収（上限）",
    "fixed_overtime_hours": "固定残業時間",
    "fixed_overtime_pay": "固定残業代",
    "bonus": "賞与",
    "salary_increase": "昇給",
    "incentive": "インセンティブ",
    "social_insurance": "社会保険",
    "commuting_allowance": "通勤手当",
    "housing_allowance": "住宅手当",
    "retirement_plan": "退職金制度",
    "qualification_support": "資格取得支援",
    "training_program": "研修制度",
    "document_screening_status": "書類選考の有無",
    "document_screening": "書類選考の補足",
    "interview": "面接",
    "aptitude_test_status": "適性検査の有無",
    "aptitude_test": "適性検査の補足",
    "interview_count_min": "面接回数（下限）",
    "interview_count_max": "面接回数（上限）",
    "interview_count": "面接回数",
    "expected_join_date": "入社予定・入社可能時期",
    "not_listed_fields": "求人票に記載がない項目",
}


# ========================================
# 入力チェック
# ========================================

def validate_job(
    job: Job,
) -> list[str]:
    """求人情報の必須項目をチェックする。"""

    errors: list[str] = []

    required_fields = (
        (
            job.company_name,
            "会社名",
        ),
        (
            job.occupation,
            "募集ポジション（職種）",
        ),
        (
            job.source_name,
            "紹介経路の具体名",
        ),
        (
            job.job_summary,
            "仕事内容",
        ),
    )

    for value, label in required_fields:
        if not value.strip():
            errors.append(
                f"{label}を入力してください。"
            )

    if (
        not job.source_type.strip()
        or job.source_type
        == "選択してください"
    ):
        errors.append(
            "紹介経路の種別を選択してください。"
        )

    return errors


# ========================================
# 文字列正規化
# ========================================

def _normalize(
    value: str,
) -> str:
    """重複判定用に文字列と空白を整える。"""

    return "".join(
        value.split()
    ).casefold()


def _is_same_source(
    saved_source: JobSource,
    new_job: Job,
) -> bool:
    """既存の紹介経路と今回の紹介経路が同じか確認する。"""

    return (
        _normalize(saved_source.source_type)
        == _normalize(new_job.source_type)
        and _normalize(saved_source.source_name)
        == _normalize(new_job.source_name)
    )


def _has_same_source_job_number(
    saved_sources: list[tuple[int, JobSource]],
    new_job: Job,
) -> bool:
    """同じ紹介経路に同じ求人番号があるか確認する。"""

    if not new_job.job_number.strip():
        return False

    return any(
        _is_same_source(
            source,
            new_job,
        )
        and source.source_job_number.strip()
        and _normalize(source.source_job_number)
        == _normalize(new_job.job_number)
        for _, source in saved_sources
    )


def _get_job_match_type(
    saved_job: Job,
    saved_sources: list[tuple[int, JobSource]],
    new_job: Job,
) -> str:
    """既存求人と今回求人の同一性を3段階で判定する。"""

    if _has_same_source_job_number(
        saved_sources,
        new_job,
    ):
        return JOB_MATCH_SAME

    if (
        saved_job.source_url.strip()
        and new_job.source_url.strip()
        and _normalize(saved_job.source_url)
        == _normalize(new_job.source_url)
    ):
        return JOB_MATCH_SAME

    if (
        saved_job.source_text.strip()
        and new_job.source_text.strip()
        and _normalize(saved_job.source_text)
        == _normalize(new_job.source_text)
    ):
        return JOB_MATCH_SAME

    if (
        saved_job.job_title.strip()
        and new_job.job_title.strip()
        and _normalize(saved_job.job_title)
        == _normalize(new_job.job_title)
    ):
        return JOB_MATCH_POSSIBLE

    if (
        saved_job.occupation.strip()
        and new_job.occupation.strip()
        and saved_job.job_summary.strip()
        and new_job.job_summary.strip()
        and _normalize(saved_job.occupation)
        == _normalize(new_job.occupation)
        and _normalize(saved_job.job_summary)
        == _normalize(new_job.job_summary)
    ):
        return JOB_MATCH_POSSIBLE

    return JOB_MATCH_NO_MATCH


# ========================================
# 重複判定
# ========================================

def check_duplicate_job(
    job: Job,
    exclude_job_id: int | None = None,
) -> tuple[str, int | None]:
    """複数の識別情報から求人の重複状態を判定する。"""

    user_id = get_current_user_id()

    candidates = find_jobs_by_company(
        user_id=user_id,
        company_name=job.company_name,
    )

    different_source_job_id = None
    possible_job_id = None

    for job_id, saved_job in candidates:
        if (
            exclude_job_id is not None
            and job_id == exclude_job_id
        ):
            continue

        saved_sources = get_job_sources(
            user_id=user_id,
            job_id=job_id,
        )

        match_type = _get_job_match_type(
            saved_job,
            saved_sources,
            job,
        )

        if match_type == JOB_MATCH_NO_MATCH:
            continue

        if match_type == JOB_MATCH_POSSIBLE:
            if possible_job_id is None:
                possible_job_id = job_id

            continue

        same_source = any(
            _is_same_source(
                source,
                job,
            )
            for _, source in saved_sources
        )

        if not saved_sources:
            same_source = (
                _normalize(saved_job.source_type)
                == _normalize(job.source_type)
                and _normalize(saved_job.source_name)
                == _normalize(job.source_name)
            )

        if same_source:
            return (
                DUPLICATE_EXACT,
                job_id,
            )

        if different_source_job_id is None:
            different_source_job_id = job_id

    if different_source_job_id is not None:
        return (
            DUPLICATE_DIFFERENT_SOURCE,
            different_source_job_id,
        )

    if possible_job_id is not None:
        return (
            DUPLICATE_POSSIBLE,
            possible_job_id,
        )

    return (
        DUPLICATE_NONE,
        None,
    )


# ========================================
# 差分比較
# ========================================

def compare_jobs(
    old_job: Job,
    new_job: Job,
) -> list[tuple[str, str, str]]:
    """既存求人と今回入力した求人の差分を返す。"""

    differences: list[
        tuple[str, str, str]
    ] = []

    for job_field in fields(Job):
        field_name = job_field.name

        old_value = getattr(
            old_job,
            field_name,
        )

        new_value = getattr(
            new_job,
            field_name,
        )

        if old_value == new_value:
            continue

        if isinstance(old_value, list):
            old_text = "\n".join(
                str(value)
                for value in old_value
            )
        else:
            old_text = str(
                old_value or ""
            )

        if isinstance(new_value, list):
            new_text = "\n".join(
                str(value)
                for value in new_value
            )
        else:
            new_text = str(
                new_value or ""
            )

        differences.append(
            (
                JOB_FIELD_LABELS.get(
                    field_name,
                    field_name,
                ),
                old_text,
                new_text,
            )
        )

    return differences


def _job_to_source(
    job: Job,
) -> JobSource:
    """求人情報から主紹介経路を作成する。"""

    return JobSource(
        source_type=job.source_type,
        source_name=job.source_name,
        source_job_number=job.job_number,
        source_url=job.source_url,
        source_text=job.source_text,
        acquired_at=job.acquired_at,
        notes="",
        is_primary=True,
    )


# ========================================
# 新規保存
# ========================================

def create_job_data(
    job: Job,
) -> tuple[int | None, list[str]]:
    """求人と主紹介経路を新規保存する。"""

    errors = validate_job(job)

    if errors:
        return None, errors

    user_id = get_current_user_id()

    job_id = create_job(
        user_id=user_id,
        job=job,
    )

    source_id = sync_primary_job_source(
        user_id=user_id,
        job_id=job_id,
        job_source=_job_to_source(job),
    )

    if source_id is None:
        return (
            job_id,
            [
                "求人は保存されましたが、"
                "紹介経路を保存できませんでした。"
            ],
        )

    return job_id, []


def save_job_data(
    job: Job,
) -> tuple[
    str,
    int | None,
    list[str],
]:
    """新規保存前に重複状態を判定する。"""

    errors = validate_job(job)

    if errors:
        return (
            DUPLICATE_NONE,
            None,
            errors,
        )

    duplicate_type, existing_job_id = (
        check_duplicate_job(job)
    )

    return (
        duplicate_type,
        existing_job_id,
        [],
    )


def add_job_source_data(
    job_id: int,
    job: Job,
) -> list[str]:
    """登録済み求人へ別の紹介経路を追加する。"""

    errors = validate_job(job)

    if errors:
        return errors

    job_source = _job_to_source(job)
    job_source.is_primary = False

    source_id = create_job_source(
        user_id=get_current_user_id(),
        job_id=job_id,
        job_source=job_source,
    )

    if source_id is None:
        return [
            "紹介経路を追加できませんでした。"
        ]

    return []


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

def load_job_sources(
    job_id: int,
) -> list[tuple[int, JobSource]]:
    """指定求人に登録された紹介経路を取得する。"""

    return get_job_sources(
        get_current_user_id(),
        job_id,
    )


# ========================================
# 更新
# ========================================

def update_job_data(
    job_id: int,
    job: Job,
) -> list[str]:
    """求人情報と主紹介経路を更新する。"""

    errors = validate_job(job)

    if errors:
        return errors

    user_id = get_current_user_id()

    updated = update_job(
        user_id=user_id,
        job_id=job_id,
        job=job,
    )

    if not updated:
        return [
            "更新対象の求人が見つかりませんでした。"
        ]

    source_id = sync_primary_job_source(
        user_id=user_id,
        job_id=job_id,
        job_source=_job_to_source(job),
    )

    if source_id is None:
        return [
            "求人情報は更新されましたが、"
            "紹介経路を更新できませんでした。"
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
