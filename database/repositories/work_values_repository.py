"""価値観回答の保存・取得を担当する。"""

from database.connection import get_connection
from models import (
    WorkStyleAnswer,
    WorkValueDetail,
    WorkValueRanking,
)


def save_work_values(
    user_id: int,
    rankings: list[WorkValueRanking],
    details: list[WorkValueDetail],
    work_style_answers: list[WorkStyleAnswer],
    draft_form_name: str,
) -> None:
    """価値観回答を正式保存し、同じ処理内で下書きを削除する。"""

    connection = get_connection()

    try:
        # 現在有効な順位付き回答を論理削除する
        connection.execute(
            """
            UPDATE user_work_value_rankings
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND deleted_at IS NULL
            """,
            (user_id,),
        )

        # 現在有効な自由記述回答を論理削除する
        connection.execute(
            """
            UPDATE user_work_value_details
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND deleted_at IS NULL
            """,
            (user_id,),
        )

        # 現在有効な仕事の進め方回答を論理削除する
        connection.execute(
            """
            UPDATE user_work_style_answers
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND deleted_at IS NULL
            """,
            (user_id,),
        )

        # 順位付き回答を新しい正式データとして登録する
        for ranking in rankings:
            connection.execute(
                """
                INSERT INTO user_work_value_rankings (
                    user_id,
                    question_type,
                    selected_value,
                    priority_rank,
                    custom_value
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    ranking.question_type,
                    ranking.selected_value,
                    ranking.priority_rank,
                    ranking.custom_value,
                ),
            )

        # 自由記述回答を新しい正式データとして登録する
        for detail in details:
            connection.execute(
                """
                INSERT INTO user_work_value_details (
                    user_id,
                    detail_type,
                    detail_text
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    detail.detail_type,
                    detail.detail_text,
                ),
            )

        # 仕事の進め方回答を新しい正式データとして登録する
        for answer in work_style_answers:
            connection.execute(
                """
                INSERT INTO user_work_style_answers (
                    user_id,
                    question_type,
                    answer_score
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    answer.question_type,
                    answer.answer_score,
                ),
            )

        # 正式保存が成功したため、価値観画面の下書きを削除する
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


def get_work_values(
    user_id: int,
) -> tuple[
    list[WorkValueRanking],
    list[WorkValueDetail],
    list[WorkStyleAnswer],
]:
    """正式保存済みの価値観回答を取得する。"""

    connection = get_connection()

    try:
        ranking_rows = connection.execute(
            """
            SELECT
                question_type,
                selected_value,
                priority_rank,
                custom_value
            FROM user_work_value_rankings
            WHERE user_id = ?
              AND deleted_at IS NULL
            ORDER BY
                question_type,
                priority_rank
            """,
            (user_id,),
        ).fetchall()

        detail_rows = connection.execute(
            """
            SELECT
                detail_type,
                detail_text
            FROM user_work_value_details
            WHERE user_id = ?
              AND deleted_at IS NULL
            ORDER BY id
            """,
            (user_id,),
        ).fetchall()

        answer_rows = connection.execute(
            """
            SELECT
                question_type,
                answer_score
            FROM user_work_style_answers
            WHERE user_id = ?
              AND deleted_at IS NULL
            ORDER BY id
            """,
            (user_id,),
        ).fetchall()

    finally:
        connection.close()

    rankings = [
        WorkValueRanking(
            question_type=row["question_type"],
            selected_value=row["selected_value"],
            priority_rank=row["priority_rank"],
            custom_value=row["custom_value"],
        )
        for row in ranking_rows
    ]

    details = [
        WorkValueDetail(
            detail_type=row["detail_type"],
            detail_text=row["detail_text"],
        )
        for row in detail_rows
    ]

    work_style_answers = [
        WorkStyleAnswer(
            question_type=row["question_type"],
            answer_score=row["answer_score"],
        )
        for row in answer_rows
    ]

    return (
        rankings,
        details,
        work_style_answers,
    )