"""職務経歴の保存・取得を担当する。"""

from database.connection import get_connection
from models import (
    Career,
    CareerHistory,
)


def save_careers(
    user_id: int,
    career_items: list[
        tuple[
            Career,
            list[CareerHistory],
        ]
    ],
) -> None:
    """複数社の職務経歴をまとめて正式保存する。"""

    connection = get_connection()

    try:
        # 現在有効な会社情報を論理削除する
        connection.execute(
            """
            UPDATE user_careers
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND deleted_at IS NULL
            """,
            (user_id,),
        )

        # 現在有効な部署・役割情報を論理削除する
        connection.execute(
            """
            UPDATE user_career_histories
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE career_id IN (
                SELECT id
                FROM user_careers
                WHERE user_id = ?
            )
              AND deleted_at IS NULL
            """,
            (user_id,),
        )

        for career, histories in career_items:
            cursor = connection.execute(
                """
                INSERT INTO user_careers (
                    user_id,
                    company_name,
                    employment_type,
                    industry,
                    start_year,
                    start_month,
                    end_year,
                    end_month,
                    is_current,
                    display_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    career.company_name,
                    career.employment_type,
                    career.industry,
                    career.start_year,
                    career.start_month,
                    career.end_year,
                    career.end_month,
                    int(career.is_current),
                    career.display_order,
                ),
            )

            career_id = cursor.lastrowid

            for history in histories:
                connection.execute(
                    """
                INSERT INTO user_career_histories (
                    career_id,
                    department,
                    position,
                    occupation,
                    start_year,
                    start_month,
                    end_year,
                    end_month,
                    job_description,
                    achievements,
                    display_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    career_id,
                    history.department,
                    history.position,
                    history.occupation,
                    history.start_year,
                    history.start_month,
                    history.end_year,
                    history.end_month,
                    history.job_description,
                    history.achievements,
                    history.display_order,
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_careers(
    user_id: int,
) -> list[
    tuple[
        Career,
        list[CareerHistory],
    ]
]:
    """利用者の職務経歴を取得する。"""

    connection = get_connection()

    try:
        careers = connection.execute(
            """
            SELECT
                id,
                company_name,
                employment_type,
                industry,
                start_year,
                start_month,
                end_year,
                end_month,
                is_current,
                display_order
            FROM user_careers
            WHERE user_id = ?
              AND deleted_at IS NULL
            ORDER BY display_order
            """,
            (user_id,),
        ).fetchall()

        results = []

        for career_row in careers:

            histories = connection.execute(
                """
                SELECT
                    department,
                    position,
                    occupation,
                    start_year,
                    start_month,
                    end_year,
                    end_month,
                    job_description,
                    achievements,
                    display_order
                FROM user_career_histories
                WHERE career_id = ?
                  AND deleted_at IS NULL
                ORDER BY display_order
                """,
                (
                    career_row["id"],
                ),
            ).fetchall()

            career = Career(
                company_name=career_row["company_name"],
                employment_type=career_row["employment_type"],
                industry=career_row["industry"] or "",
                start_year=career_row["start_year"],
                start_month=career_row["start_month"],
                end_year=career_row["end_year"],
                end_month=career_row["end_month"],
                is_current=bool(
                    career_row["is_current"]
                ),
                display_order=career_row["display_order"],
            )

            history_list = []

            for history_row in histories:

                history_list.append(
                    CareerHistory(
                        department=history_row["department"],
                        position=history_row["position"],
                        occupation=history_row["occupation"],
                        start_year=history_row["start_year"],
                        start_month=history_row["start_month"],
                        end_year=history_row["end_year"],
                        end_month=history_row["end_month"],
                        job_description=history_row["job_description"],
                        achievements=history_row["achievements"],
                        display_order=history_row["display_order"],
                    )
                )

            results.append(
                (
                    career,
                    history_list,
                )
            )

        return results

    finally:
        connection.close()