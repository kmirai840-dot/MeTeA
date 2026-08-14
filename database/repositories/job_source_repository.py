"""求人の紹介経路を保存・取得する。"""

import sqlite3

from database.connection import get_connection
from models import JobSource


def _row_to_job_source(
    row: sqlite3.Row,
) -> JobSource:
    """DBの1行をJobSourceへ変換する。"""

    return JobSource(
        source_type=(
            row["source_type"]
            or ""
        ),
        source_name=(
            row["source_name"]
            or ""
        ),
        source_job_number=(
            row["source_job_number"]
            or ""
        ),
        source_url=(
            row["source_url"]
            or ""
        ),
        source_text=(
            row["source_text"]
            or ""
        ),
        acquired_at=(
            row["acquired_at"]
            or ""
        ),
        notes=(
            row["notes"]
            or ""
        ),
        is_primary=bool(
            row["is_primary"]
        ),
    )


def get_job_sources(
    user_id: int,
    job_id: int,
) -> list[tuple[int, JobSource]]:
    """指定求人に登録された紹介経路を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT source.*
            FROM user_job_sources AS source
            INNER JOIN user_jobs AS job
                ON job.id = source.job_id
            WHERE
                source.job_id = ?
                AND source.deleted_at IS NULL
                AND job.user_id = ?
                AND job.deleted_at IS NULL
            ORDER BY
                source.is_primary DESC,
                source.created_at ASC,
                source.id ASC
            """,
            (
                job_id,
                user_id,
            ),
        ).fetchall()

        return [
            (
                row["id"],
                _row_to_job_source(row),
            )
            for row in rows
        ]

    finally:
        connection.close()


def create_job_source(
    user_id: int,
    job_id: int,
    job_source: JobSource,
) -> int | None:
    """求人へ新しい紹介経路を追加する。"""

    connection = get_connection()

    try:
        job_exists = connection.execute(
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

        if job_exists is None:
            return None

        if job_source.is_primary:
            connection.execute(
                """
                UPDATE user_job_sources
                SET
                    is_primary = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    job_id = ?
                    AND deleted_at IS NULL
                """,
                (job_id,),
            )

        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO user_job_sources (
                job_id,
                source_type,
                source_name,
                source_job_number,
                source_url,
                source_text,
                acquired_at,
                notes,
                is_primary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                job_source.source_type.strip(),
                job_source.source_name.strip(),
                job_source.source_job_number.strip(),
                job_source.source_url.strip(),
                job_source.source_text.strip(),
                job_source.acquired_at.strip(),
                job_source.notes.strip(),
                int(job_source.is_primary),
            ),
        )

        if cursor.rowcount == 0:
            existing_row = connection.execute(
                """
                SELECT id
                FROM user_job_sources
                WHERE
                    job_id = ?
                    AND source_type = ?
                    AND source_name = ?
                    AND source_url = ?
                    AND deleted_at IS NULL
                """,
                (
                    job_id,
                    job_source.source_type.strip(),
                    job_source.source_name.strip(),
                    job_source.source_url.strip(),
                ),
            ).fetchone()

            connection.commit()

            if existing_row is None:
                return None

            return int(
                existing_row["id"]
            )

        source_id = cursor.lastrowid

        connection.commit()

        if source_id is None:
            return None

        return int(source_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def set_primary_job_source(
    user_id: int,
    job_id: int,
    source_id: int,
) -> bool:
    """指定した紹介経路を主経路にする。"""

    connection = get_connection()

    try:
        target = connection.execute(
            """
            SELECT source.id
            FROM user_job_sources AS source
            INNER JOIN user_jobs AS job
                ON job.id = source.job_id
            WHERE
                source.id = ?
                AND source.job_id = ?
                AND source.deleted_at IS NULL
                AND job.user_id = ?
                AND job.deleted_at IS NULL
            """,
            (
                source_id,
                job_id,
                user_id,
            ),
        ).fetchone()

        if target is None:
            return False

        connection.execute(
            """
            UPDATE user_job_sources
            SET
                is_primary = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                job_id = ?
                AND deleted_at IS NULL
            """,
            (job_id,),
        )

        connection.execute(
            """
            UPDATE user_job_sources
            SET
                is_primary = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = ?
                AND job_id = ?
                AND deleted_at IS NULL
            """,
            (
                source_id,
                job_id,
            ),
        )

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def sync_primary_job_source(
    user_id: int,
    job_id: int,
    job_source: JobSource,
) -> int | None:
    """求人の主な紹介経路を新しい内容へ同期する。"""

    connection = get_connection()

    try:
        job_exists = connection.execute(
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

        if job_exists is None:
            return None

        primary_source = connection.execute(
            """
            SELECT id
            FROM user_job_sources
            WHERE
                job_id = ?
                AND is_primary = 1
                AND deleted_at IS NULL
            ORDER BY
                id ASC
            LIMIT 1
            """,
            (job_id,),
        ).fetchone()

        if primary_source is None:
            cursor = connection.execute(
                """
                INSERT INTO user_job_sources (
                    job_id,
                    source_type,
                    source_name,
                    source_job_number,
                    source_url,
                    source_text,
                    acquired_at,
                    notes,
                    is_primary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    job_id,
                    job_source.source_type.strip(),
                    job_source.source_name.strip(),
                    job_source.source_job_number.strip(),
                    job_source.source_url.strip(),
                    job_source.source_text.strip(),
                    job_source.acquired_at.strip(),
                    job_source.notes.strip(),
                ),
            )

            source_id = cursor.lastrowid

        else:
            source_id = int(
                primary_source["id"]
            )

            connection.execute(
                """
                UPDATE user_job_sources
                SET
                    source_type = ?,
                    source_name = ?,
                    source_job_number = ?,
                    source_url = ?,
                    source_text = ?,
                    acquired_at = ?,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    id = ?
                    AND job_id = ?
                    AND deleted_at IS NULL
                """,
                (
                    job_source.source_type.strip(),
                    job_source.source_name.strip(),
                    job_source.source_job_number.strip(),
                    job_source.source_url.strip(),
                    job_source.source_text.strip(),
                    job_source.acquired_at.strip(),
                    job_source.notes.strip(),
                    source_id,
                    job_id,
                ),
            )

        connection.execute(
            """
            UPDATE user_job_sources
            SET
                is_primary = CASE
                    WHEN id = ? THEN 1
                    ELSE 0
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                job_id = ?
                AND deleted_at IS NULL
            """,
            (
                source_id,
                job_id,
            ),
        )

        connection.commit()

        if source_id is None:
            return None

        return int(source_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_job_source(
    user_id: int,
    job_id: int,
    source_id: int,
) -> bool:
    """紹介経路を論理削除する。"""

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE user_job_sources
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = ?
                AND job_id = ?
                AND deleted_at IS NULL
                AND EXISTS (
                    SELECT 1
                    FROM user_jobs
                    WHERE
                        id = ?
                        AND user_id = ?
                        AND deleted_at IS NULL
                )
            """,
            (
                source_id,
                job_id,
                job_id,
                user_id,
            ),
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return False

        connection.commit()

        return True

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()