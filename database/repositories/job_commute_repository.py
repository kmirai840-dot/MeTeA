"""求人ごとの電車移動時間の保存・取得を担当する。"""

from database.connection import get_connection
from models import JobCommuteCheck


def save_job_commute_check(
    user_id: int,
    commute_check: JobCommuteCheck,
) -> None:
    """電車移動時間を新規保存または更新する。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO user_job_commute_checks (
                user_id,
                job_id,
                origin_station_name,
                origin_station_place_id,
                destination_station_name,
                duration_minutes,
                source_type,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, job_id)
            DO UPDATE SET
                origin_station_name = (
                    excluded.origin_station_name
                ),
                origin_station_place_id = (
                    excluded.origin_station_place_id
                ),
                destination_station_name = (
                    excluded.destination_station_name
                ),
                duration_minutes = (
                    excluded.duration_minutes
                ),
                source_type = excluded.source_type,
                checked_at = excluded.checked_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                commute_check.job_id,
                commute_check.origin_station_name,
                commute_check.origin_station_place_id,
                commute_check.destination_station_name,
                commute_check.duration_minutes,
                commute_check.source_type,
                commute_check.checked_at,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_job_commute_check(
    user_id: int,
    job_id: int,
) -> JobCommuteCheck | None:
    """保存済みの電車移動時間を取得する。"""

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                job_id,
                origin_station_name,
                origin_station_place_id,
                destination_station_name,
                duration_minutes,
                source_type,
                checked_at
            FROM user_job_commute_checks
            WHERE
                user_id = ?
                AND job_id = ?
            """,
            (
                user_id,
                job_id,
            ),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return None

    return JobCommuteCheck(
        job_id=int(row["job_id"]),
        origin_station_name=row[
            "origin_station_name"
        ],
        origin_station_place_id=row[
            "origin_station_place_id"
        ],
        destination_station_name=row[
            "destination_station_name"
        ],
        duration_minutes=int(
            row["duration_minutes"]
        ),
        source_type=row["source_type"],
        checked_at=row["checked_at"],
    )


def delete_job_commute_check(
    user_id: int,
    job_id: int,
) -> None:
    """指定求人の電車移動時間を削除する。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            DELETE FROM user_job_commute_checks
            WHERE
                user_id = ?
                AND job_id = ?
            """,
            (
                user_id,
                job_id,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()