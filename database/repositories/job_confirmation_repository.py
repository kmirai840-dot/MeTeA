"""求人ごとの確認不要判断を保存・取得する。"""

from database.connection import get_connection


def get_job_confirmation_resolutions(
    user_id: int,
    job_id: int,
) -> dict[str, str]:
    """項目キーごとの判断状態を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT item_key, status
            FROM user_job_confirmation_resolutions
            WHERE user_id = ? AND job_id = ?
            """,
            (user_id, job_id),
        ).fetchall()
    finally:
        connection.close()

    return {
        str(row["item_key"]): str(row["status"])
        for row in rows
    }


def save_job_confirmation_resolution(
    user_id: int,
    job_id: int,
    item_key: str,
    item_name: str,
    item_reason: str,
    status: str,
) -> None:
    """確認項目に対する利用者判断を保存する。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO user_job_confirmation_resolutions (
                user_id, job_id, item_key,
                item_name, item_reason, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, job_id, item_key)
            DO UPDATE SET
                item_name = excluded.item_name,
                item_reason = excluded.item_reason,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id, job_id, item_key,
                item_name, item_reason, status,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_job_confirmation_resolution(
    user_id: int,
    job_id: int,
    item_key: str,
) -> None:
    """確認不要判断を取り消す。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            DELETE FROM user_job_confirmation_resolutions
            WHERE user_id = ? AND job_id = ? AND item_key = ?
            """,
            (user_id, job_id, item_key),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()