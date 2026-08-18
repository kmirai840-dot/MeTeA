from pathlib import Path

from database.connection import get_connection


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def initialize_database() -> None:
    """必要なSQLiteテーブルを作成する。"""

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = get_connection()

    try:
        connection.executescript(schema)

        user_profile_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(user_profiles)"
            ).fetchall()
        }

        required_user_profile_columns = {
            "nearest_station": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "nearest_station_place_id": (
                "TEXT NOT NULL DEFAULT ''"
            ),
        }

        for (
            column_name,
            column_definition,
        ) in required_user_profile_columns.items():
            if column_name in user_profile_columns:
                continue

            connection.execute(
                f"""
                ALTER TABLE user_profiles
                ADD COLUMN {column_name}
                {column_definition}
                """
            )

        job_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(user_jobs)"
            ).fetchall()
        }

        required_job_columns = {
            "organizational_culture": (
                "TEXT NOT NULL DEFAULT ''"
            ),
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

        job_source_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(user_job_sources)"
            ).fetchall()
        }

        required_job_source_columns = {
            "source_job_number": (
                "TEXT NOT NULL DEFAULT ''"
            ),
        }

        for (
            column_name,
            column_definition,
        ) in required_job_source_columns.items():
            if column_name in job_source_columns:
                continue

            connection.execute(
                f"""
                ALTER TABLE user_job_sources
                ADD COLUMN {column_name}
                {column_definition}
                """
            )

        job_evaluation_columns = {
            row["name"]
            for row in connection.execute(
                """
                PRAGMA table_info(
                    user_job_match_evaluations
                )
                """
            ).fetchall()
        }

        required_job_evaluation_columns = {
            "evaluation_coverage": (
                "INTEGER NOT NULL DEFAULT 0"
            ),
            "is_provisional": (
                "INTEGER NOT NULL DEFAULT 1"
            ),
            "is_stale": (
                "INTEGER NOT NULL DEFAULT 0"
            ),
            "stale_reason": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "rule_version": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "prompt_version": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "model_name": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "evaluation_result_json": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "evaluation_status": (
                "TEXT NOT NULL DEFAULT 'ready'"
            ),
            "failure_reason": (
                "TEXT NOT NULL DEFAULT ''"
            ),
            "failed_at": "TEXT",
            "retry_count": (
                "INTEGER NOT NULL DEFAULT 0"
            ),
            "result_notice_pending": (
                "INTEGER NOT NULL DEFAULT 0"
            ),
            "status_updated_at": "TEXT",
        }

        for (
            column_name,
            column_definition,
        ) in (
            required_job_evaluation_columns.items()
        ):
            if (
                column_name
                in job_evaluation_columns
            ):
                continue

            connection.execute(
                f"""
                ALTER TABLE
                    user_job_match_evaluations
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

        application_table_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(user_applications)"
            ).fetchall()
        }
        if "deleted_at" not in application_table_columns:
            connection.execute(
                "ALTER TABLE user_applications ADD COLUMN deleted_at TEXT"
            )
        if "selection_stage" not in application_table_columns:
            connection.execute(
                "ALTER TABLE user_applications ADD COLUMN selection_stage TEXT NOT NULL DEFAULT ''"
            )

        milestone_table_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(application_milestones)"
            ).fetchall()
        }
        if "deleted_at" not in milestone_table_columns:
            connection.execute(
                "ALTER TABLE application_milestones ADD COLUMN deleted_at TEXT"
            )
        if "rescheduled_from_id" not in milestone_table_columns:
            connection.execute(
                "ALTER TABLE application_milestones ADD COLUMN rescheduled_from_id INTEGER"
            )
        if "cancelled_at" not in milestone_table_columns:
            connection.execute(
                "ALTER TABLE application_milestones ADD COLUMN cancelled_at TEXT"
            )

        phase_history_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(application_phase_history)"
            ).fetchall()
        }
        if "selection_result" not in phase_history_columns:
            connection.execute(
                """
                ALTER TABLE application_phase_history
                ADD COLUMN selection_result TEXT NOT NULL DEFAULT ''
                """
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
