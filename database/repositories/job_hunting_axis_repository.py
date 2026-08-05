from database.connection import get_connection
from models import JobHuntingAxis


def save_job_hunting_axes(
    user_id: int,
    axes: list[JobHuntingAxis],
    draft_form_name: str,
) -> None:
    """就活の軸を正式保存し、同じ処理内で下書きを削除する。"""

    connection = get_connection()

    try:
        # 現在有効な軸を一度論理削除する
        connection.execute(
            """
            UPDATE user_job_hunting_axes
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND deleted_at IS NULL
            """,
            (user_id,),
        )

        # 現在の画面内容を新しい正式データとして登録する
        for axis in axes:
            connection.execute(
                """
                INSERT INTO user_job_hunting_axes (
                    user_id,
                    axis_title,
                    axis_description,
                    priority_rank,
                    source_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    axis.axis_title,
                    axis.axis_description,
                    axis.priority_rank,
                    axis.source_type,
                ),
            )

        # 正式保存が成功したため、下書きを削除する
        connection.execute(
            """
            DELETE FROM form_drafts
            WHERE user_id = ?
              AND form_name = ?
            """,
            (
                user_id,
                draft_form_name,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_job_hunting_axes(
    user_id: int,
) -> list[JobHuntingAxis]:
    """保存済みの就活の軸を優先順位順に取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                axis_title,
                axis_description,
                priority_rank,
                source_type
            FROM user_job_hunting_axes
            WHERE user_id = ?
              AND deleted_at IS NULL
            ORDER BY priority_rank
            """,
            (user_id,),
        ).fetchall()

    finally:
        connection.close()

    return [
        JobHuntingAxis(
            axis_title=row["axis_title"],
            axis_description=row["axis_description"],
            priority_rank=row["priority_rank"],
            source_type=row["source_type"],
        )
        for row in rows
    ]