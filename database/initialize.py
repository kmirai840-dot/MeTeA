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

        if "source_type" not in job_columns:
            connection.execute(
                """
                ALTER TABLE user_jobs
                ADD COLUMN source_type TEXT
                NOT NULL DEFAULT ''
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