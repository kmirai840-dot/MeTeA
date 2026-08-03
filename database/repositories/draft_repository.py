import json
from typing import Any

from database.connection import get_connection


def save_draft(
    user_id: int,
    form_name: str,
    draft_data: dict[str, Any],
) -> None:
    """入力途中の内容をSQLiteへ保存する。"""

    draft_json = json.dumps(
        draft_data,
        ensure_ascii=False,
    )
    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO form_drafts (
                user_id,
                form_name,
                draft_data
            )
            VALUES (?, ?, ?)
            ON CONFLICT (user_id, form_name)
            DO UPDATE SET
                draft_data = excluded.draft_data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                form_name,
                draft_json,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_draft(
    user_id: int,
    form_name: str,
) -> dict[str, Any] | None:
    """SQLiteから入力途中の内容を取得する。"""

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT draft_data
            FROM form_drafts
            WHERE user_id = ?
              AND form_name = ?
            """,
            (
                user_id,
                form_name,
            ),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    return json.loads(row["draft_data"])


def delete_draft(
    user_id: int,
    form_name: str,
) -> None:
    """正式保存後に不要となった下書きを削除する。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            DELETE FROM form_drafts
            WHERE user_id = ?
              AND form_name = ?
            """,
            (
                user_id,
                form_name,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()