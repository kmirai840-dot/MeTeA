from pathlib import Path

from database.connection import get_connection


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def initialize_database() -> None:
    """必要なSQLiteテーブルを作成する。"""

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = get_connection()

    try:
        connection.executescript(schema)

        job_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(user_jobs)"
            ).fetchall()
        }

        required_job_columns = {
            "employee_count_min": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "employee_count_max": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "interview_count_min": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "interview_count_max": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "document_screening_status": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "aptitude_test_status": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "probation_period_status": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "probation_period_months": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "source_type": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "wage_type": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "monthly_salary_min": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "monthly_salary_max": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "base_salary_min": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "base_salary_max": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "fixed_overtime_system": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "fixed_overtime_pay_min": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "fixed_overtime_pay_max": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "overtime_extra_pay": (
                "TEXT NOT NULL DEFAULT ''"
            ),
        }

        for (
            column_name,
            column_definition,
        ) in required_job_columns.items():
            if column_name in job_columns:
                continue

            connection.execute(
                f"""
                ALTER TABLE user_jobs
                ADD COLUMN {column_name}
                {column_definition}
                """
            )

        connection.execute(
            """
            INSERT OR IGNORE INTO user_job_sources (
                job_id,
                source_type,
                source_name,
                source_url,
                source_text,
                acquired_at,
                is_primary
            )
            SELECT
                id,
                source_type,
                source_name,
                source_url,
                source_text,
                acquired_at,
                1
            FROM user_jobs
            WHERE
                source_type <> ''
                OR source_name <> ''
                OR source_url <> ''
                OR source_text <> ''
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()