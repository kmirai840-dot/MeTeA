from datetime import date

from database.connection import get_connection
from models import BasicInfo


def save_user_profile(
    user_id: int,
    basic_info: BasicInfo,
    draft_form_name: str,
) -> None:
    """基本情報を正式保存し、同じ処理内で下書きを削除する。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO user_profiles (
                user_id,
                last_name,
                first_name,
                gender,
                birth_date,
                prefecture,
                municipality
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id)
            DO UPDATE SET
                last_name = excluded.last_name,
                first_name = excluded.first_name,
                gender = excluded.gender,
                birth_date = excluded.birth_date,
                prefecture = excluded.prefecture,
                municipality = excluded.municipality,
                updated_at = CURRENT_TIMESTAMP,
                deleted_at = NULL
            """,
            (
                user_id,
                basic_info.family_name,
                basic_info.given_name,
                basic_info.gender,
                basic_info.birth_date.isoformat(),
                basic_info.prefecture,
                basic_info.municipality,
            ),
        )

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


def get_user_profile(
    user_id: int,
) -> BasicInfo | None:
    """保存済みの基本情報を取得する。"""

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                last_name,
                first_name,
                gender,
                birth_date,
                prefecture,
                municipality
            FROM user_profiles
            WHERE user_id = ?
              AND deleted_at IS NULL
            """,
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    return BasicInfo(
        family_name=row["last_name"],
        given_name=row["first_name"],
        gender=row["gender"],
        birth_date=date.fromisoformat(row["birth_date"]),
        prefecture=row["prefecture"],
        municipality=row["municipality"],
    )