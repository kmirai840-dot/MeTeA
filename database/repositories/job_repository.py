"""求人情報のDB保存・取得・更新・削除を担当する。"""

import sqlite3

from models import Job
from database.connection import get_connection


# ========================================
# 複数値項目
# ========================================
    
MULTI_VALUE_FIELDS = (
    "job_details",
    "required_experience",
    "required_skills",
    "required_qualifications",
    "preferred_experience",
    "preferred_skills",
    "desired_personality",
    "not_listed_fields",
)


# ========================================
# user_jobs の通常項目
# ========================================

JOB_FIELDS = (
    "registration_method",
    "source_url",
    "source_text",
    "acquired_at",
    "source_type",
    "source_name",
    "company_name",
    "job_title",
    "job_number",
    "publication_start_date",
    "publication_end_date",
    "industry",
    "business_description",
    "employee_count_min",
    "employee_count_max",
    "employee_count",
    "established_date",
    "capital",
    "listing_status",
    "occupation",
    "department",
    "planned_hires",
    "recruitment_reason",
    "job_summary",
    "responsibility_scope",
    "customers",
    "internal_stakeholders",
    "external_partners",
    "goals_kpi",
    "expected_results",
    "employment_type",
    "probation_period_status",
    "probation_period_months",
    "probation_period",
    "prefecture",
    "municipality",
    "nearest_station",
    "transfer_required",
    "work_style",
    "start_time",
    "end_time",
    "break_minutes",
    "scheduled_work_hours",
    "flextime",
    "overtime",
    "holidays",
    "annual_holidays",
    "wage_type",
    "monthly_salary_min",
    "monthly_salary_max",
    "base_salary_min",
    "base_salary_max",
    "fixed_overtime_system",
    "fixed_overtime_pay_min",
    "fixed_overtime_pay_max",
    "overtime_extra_pay",
    "monthly_salary",
    "annual_salary",
    "expected_salary_min",
    "expected_salary_max",
    "fixed_overtime_hours",
    "fixed_overtime_pay",
    "bonus",
    "salary_increase",
    "incentive",
    "social_insurance",
    "commuting_allowance",
    "housing_allowance",
    "retirement_plan",
    "qualification_support",
    "training_program",
    "document_screening_status",
    "document_screening",
    "interview",
    "aptitude_test_status",
    "aptitude_test",
    "interview_count_min",
    "interview_count_max",
    "interview_count",
    "expected_join_date",
)


def _save_job_items(
    connection: sqlite3.Connection,
    job_id: int,
    job: Job,
) -> None:
    """求人の複数値項目を保存する。"""

    for field_name in MULTI_VALUE_FIELDS:
        values = getattr(
            job,
            field_name,
        )

        for display_order, value in enumerate(
            values,
            start=1,
        ):
            cleaned_value = str(value).strip()

            if not cleaned_value:
                continue

            connection.execute(
                """
                INSERT INTO user_job_items (
                    job_id,
                    item_type,
                    item_value,
                    display_order
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    job_id,
                    field_name,
                    cleaned_value,
                    display_order,
                ),
            )


def _get_job_items(
    connection: sqlite3.Connection,
    job_id: int,
) -> dict[str, list[str]]:
    """求人の複数値項目を取得する。"""

    result = {
        field_name: []
        for field_name in MULTI_VALUE_FIELDS
    }

    rows = connection.execute(
        """
        SELECT
            item_type,
            item_value
        FROM user_job_items
        WHERE
            job_id = ?
            AND deleted_at IS NULL
        ORDER BY
            item_type,
            display_order,
            id
        """,
        (job_id,),
    ).fetchall()

    for row in rows:
        item_type = row["item_type"]

        if item_type not in result:
            continue

        result[item_type].append(
            row["item_value"]
        )

    return result


def _row_to_job(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
) -> Job:
    """DBの1行をJobへ変換する。"""

    multi_values = _get_job_items(
        connection,
        row["id"],
    )

    normal_values = {
        field_name: row[field_name]
        or ""
        for field_name in JOB_FIELDS
    }

    return Job(
        **normal_values,
        **multi_values,
    )


def create_job(
    user_id: int,
    job: Job,
) -> int:
    """求人を新規登録し、求人IDを返す。"""

    connection = get_connection()

    try:
        columns = ", ".join(
            (
                "user_id",
                *JOB_FIELDS,
            )
        )

        placeholders = ", ".join(
            "?"
            for _ in range(
                len(JOB_FIELDS) + 1
            )
        )

        values = (
            user_id,
            *(
                getattr(job, field_name)
                for field_name in JOB_FIELDS
            ),
        )

        cursor = connection.execute(
            f"""
            INSERT INTO user_jobs (
                {columns}
            )
            VALUES (
                {placeholders}
            )
            """,
            values,
        )

        job_id = cursor.lastrowid

        if job_id is None:
            raise RuntimeError(
                "求人IDを取得できませんでした。"
            )

        _save_job_items(
            connection,
            job_id,
            job,
        )

        connection.commit()

        return int(job_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_jobs(
    user_id: int,
) -> list[tuple[int, Job]]:
    """利用者の登録済み求人を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM user_jobs
            WHERE
                user_id = ?
                AND deleted_at IS NULL
            ORDER BY
                created_at DESC,
                id DESC
            """,
            (user_id,),
        ).fetchall()

        return [
            (
                row["id"],
                _row_to_job(
                    connection,
                    row,
                ),
            )
            for row in rows
        ]

    finally:
        connection.close()


def get_job_list_rows(
    user_id: int,
) -> list[tuple[int, Job, str | None, str | None]]:
    """求人一覧表示用に、求人情報と登録日・更新日を取得する。"""

    jobs = get_jobs(user_id)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                created_at,
                updated_at
            FROM user_jobs
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    date_by_job_id = {
        row["id"]: (
            row["created_at"],
            row["updated_at"],
        )
        for row in rows
    }

    return [
        (
            job_id,
            job,
            date_by_job_id.get(job_id, (None, None))[0],
            date_by_job_id.get(job_id, (None, None))[1],
        )
        for job_id, job in jobs
    ]


def get_job(
    user_id: int,
    job_id: int,
) -> Job | None:
    """指定した求人を1件取得する。"""

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM user_jobs
            WHERE
                id = ?
                AND user_id = ?
                AND deleted_at IS NULL
            """,
            (
                job_id,
                user_id,
            ),
        ).fetchone()

        if row is None:
            return None

        return _row_to_job(
            connection,
            row,
        )

    finally:
        connection.close()


def find_jobs_by_company(
    user_id: int,
    company_name: str,
) -> list[tuple[int, Job]]:
    """同じ会社の登録済み求人を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM user_jobs
            WHERE
                user_id = ?
                AND company_name = ?
                AND deleted_at IS NULL
            ORDER BY
                id ASC
            """,
            (
                user_id,
                company_name.strip(),
            ),
        ).fetchall()

        return [
            (
                int(row["id"]),
                _row_to_job(
                    connection,
                    row,
                ),
            )
            for row in rows
        ]

    finally:
        connection.close()


def find_jobs_by_company_and_occupation(
    user_id: int,
    company_name: str,
    occupation: str,
) -> list[tuple[int, Job]]:
    """同じ会社・職種の登録済み求人を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM user_jobs
            WHERE
                user_id = ?
                AND company_name = ?
                AND occupation = ?
                AND deleted_at IS NULL
            ORDER BY
                updated_at DESC,
                id DESC
            """,
            (
                user_id,
                company_name.strip(),
                occupation.strip(),
            ),
        ).fetchall()

        return [
            (
                row["id"],
                _row_to_job(
                    connection,
                    row,
                ),
            )
            for row in rows
        ]

    finally:
        connection.close()

def update_job(
    user_id: int,
    job_id: int,
    job: Job,
) -> bool:
    """登録済み求人を更新する。"""

    connection = get_connection()

    try:
        exists = connection.execute(
            """
            SELECT id
            FROM user_jobs
            WHERE
                id = ?
                AND user_id = ?
                AND deleted_at IS NULL
            """,
            (
                job_id,
                user_id,
            ),
        ).fetchone()

        if exists is None:
            return False

        assignments = ", ".join(
            f"{field_name} = ?"
            for field_name in JOB_FIELDS
        )

        values = (
            *(
                getattr(job, field_name)
                for field_name in JOB_FIELDS
            ),
            job_id,
            user_id,
        )

        connection.execute(
            f"""
            UPDATE user_jobs
            SET
                {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = ?
                AND user_id = ?
                AND deleted_at IS NULL
            """,
            values,
        )

        connection.execute(
            """
            DELETE FROM user_job_items
            WHERE job_id = ?
            """,
            (job_id,),
        )

        _save_job_items(
            connection,
            job_id,
            job,
        )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_job(
    user_id: int,
    job_id: int,
) -> bool:
    """求人を論理削除する。"""

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE user_jobs
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = ?
                AND user_id = ?
                AND deleted_at IS NULL
            """,
            (
                job_id,
                user_id,
            ),
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return False

        connection.execute(
            """
            UPDATE user_job_items
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                job_id = ?
                AND deleted_at IS NULL
            """,
            (job_id,),
        )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()