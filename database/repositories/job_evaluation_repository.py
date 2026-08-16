"""求人のAI評価と応募判断を担当するRepository。"""

from database.connection import get_connection
from models import (
    JobApplicationDecision,
    JobMatchEvaluation,
)


# ========================================
# AIマッチング評価
# ========================================
def get_job_match_evaluations(
    user_id: int,
) -> dict[int, JobMatchEvaluation]:
    """利用者の全求人に対するAI評価を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                job_id,
                overall_score,
                hope_condition_score,
                work_value_score,
                career_skill_score,
                required_condition_score,
                evaluation_coverage,
                is_provisional,
                is_stale,
                stale_reason,
                matching_points,
                concern_points,
                confirmation_points,
                ai_comment,
                evaluated_at
            FROM user_job_match_evaluations
            WHERE
                user_id = ?
                AND deleted_at IS NULL
            ORDER BY
                overall_score DESC,
                evaluated_at DESC,
                id DESC
            """,
            (user_id,),
        ).fetchall()

    finally:
        connection.close()

    return {
        int(row["job_id"]): JobMatchEvaluation(
            job_id=int(row["job_id"]),
            overall_score=row["overall_score"],
            hope_condition_score=(
                row["hope_condition_score"]
            ),
            work_value_score=(
                row["work_value_score"]
            ),
            career_skill_score=(
                row["career_skill_score"]
            ),
            required_condition_score=(
                row["required_condition_score"]
            ),
            evaluation_coverage=int(
                row["evaluation_coverage"]
                or 0
            ),
            is_provisional=bool(
                row["is_provisional"]
            ),
            is_stale=bool(
                row["is_stale"]
            ),
            stale_reason=(
                row["stale_reason"]
                or ""
            ),
            matching_points=(
                row["matching_points"]
            ),
            concern_points=(
                row["concern_points"]
            ),
            confirmation_points=(
                row["confirmation_points"]
            ),
            ai_comment=row["ai_comment"],
            evaluated_at=row["evaluated_at"],
        )
        for row in rows
    }


def save_job_match_evaluation(
    user_id: int,
    evaluation: JobMatchEvaluation,
) -> None:
    """求人1件分のAI評価を登録または更新する。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO user_job_match_evaluations (
                user_id,
                job_id,
                overall_score,
                hope_condition_score,
                work_value_score,
                career_skill_score,
                required_condition_score,
                evaluation_coverage,
                is_provisional,
                is_stale,
                stale_reason,
                matching_points,
                concern_points,
                confirmation_points,
                ai_comment,
                evaluated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (
                user_id,
                job_id
            )
            DO UPDATE SET
                overall_score =
                    excluded.overall_score,
                hope_condition_score =
                    excluded.hope_condition_score,
                work_value_score =
                    excluded.work_value_score,
                career_skill_score =
                    excluded.career_skill_score,
                required_condition_score =
                    excluded.required_condition_score,
                evaluation_coverage =
                    excluded.evaluation_coverage,
                is_provisional =
                    excluded.is_provisional,
                is_stale =
                    excluded.is_stale,
                stale_reason =
                    excluded.stale_reason,
                matching_points =
                    excluded.matching_points,
                concern_points =
                    excluded.concern_points,
                confirmation_points =
                    excluded.confirmation_points,
                ai_comment =
                    excluded.ai_comment,
                evaluated_at =
                    excluded.evaluated_at,
                updated_at =
                    CURRENT_TIMESTAMP,
                deleted_at =
                    NULL
            """,
            (
                user_id,
                evaluation.job_id,
                evaluation.overall_score,
                evaluation.hope_condition_score,
                evaluation.work_value_score,
                evaluation.career_skill_score,
                evaluation.required_condition_score,
                evaluation.evaluation_coverage,
                int(evaluation.is_provisional),
                int(evaluation.is_stale),
                evaluation.stale_reason,
                evaluation.matching_points,
                evaluation.concern_points,
                evaluation.confirmation_points,
                evaluation.ai_comment,
                evaluation.evaluated_at,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def mark_job_match_evaluations_stale(
    user_id: int,
    stale_reason: str,
) -> int:
    """利用者の保存済みAI評価を再評価待ちにする。"""

    normalized_reason = stale_reason.strip()

    if not normalized_reason:
        normalized_reason = (
            "AI評価に使用する情報が変更されました。"
        )

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE user_job_match_evaluations
            SET
                is_stale = 1,
                stale_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                user_id = ?
                AND deleted_at IS NULL
            """,
            (
                normalized_reason,
                user_id,
            ),
        )

        connection.commit()

        return max(
            0,
            int(cursor.rowcount),
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def mark_job_match_evaluation_stale(
    user_id: int,
    job_id: int,
    stale_reason: str,
) -> bool:
    """指定求人の保存済みAI評価を再評価待ちにする。"""

    if user_id <= 0 or job_id <= 0:
        return False

    normalized_reason = stale_reason.strip()

    if not normalized_reason:
        normalized_reason = (
            "AI評価に使用する情報が変更されました。"
        )

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE user_job_match_evaluations
            SET
                is_stale = 1,
                stale_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                user_id = ?
                AND job_id = ?
                AND deleted_at IS NULL
            """,
            (
                normalized_reason,
                user_id,
                job_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_stale_job_match_evaluation_ids(
    user_id: int,
) -> list[int]:
    """再評価待ちになっている求人IDを取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT job_id
            FROM user_job_match_evaluations
            WHERE
                user_id = ?
                AND is_stale = 1
                AND deleted_at IS NULL
            ORDER BY
                updated_at ASC,
                job_id ASC
            """,
            (user_id,),
        ).fetchall()

    finally:
        connection.close()

    return [
        int(row["job_id"])
        for row in rows
    ]


# ========================================
# 応募判断
# ========================================
def get_job_application_decisions(
    user_id: int,
) -> dict[int, JobApplicationDecision]:
    """利用者の全求人に対する応募判断を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                job_id,
                decision_status,
                next_action,
                action_deadline,
                memo
            FROM user_job_application_decisions
            WHERE
                user_id = ?
                AND deleted_at IS NULL
            ORDER BY
                updated_at DESC,
                id DESC
            """,
            (user_id,),
        ).fetchall()

    finally:
        connection.close()

    return {
        int(row["job_id"]): JobApplicationDecision(
            job_id=int(row["job_id"]),
            decision_status=row["decision_status"],
            next_action=row["next_action"],
            action_deadline=row["action_deadline"],
            memo=row["memo"],
        )
        for row in rows
    }


def save_job_application_decision(
    user_id: int,
    decision: JobApplicationDecision,
) -> None:
    """求人1件分の応募判断を登録または更新する。"""

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO user_job_application_decisions (
                user_id,
                job_id,
                decision_status,
                next_action,
                action_deadline,
                memo
            )
            VALUES (
                ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (
                user_id,
                job_id
            )
            DO UPDATE SET
                decision_status =
                    excluded.decision_status,
                next_action =
                    excluded.next_action,
                action_deadline =
                    excluded.action_deadline,
                memo =
                    excluded.memo,
                updated_at =
                    CURRENT_TIMESTAMP,
                deleted_at =
                    NULL
            """,
            (
                user_id,
                decision.job_id,
                decision.decision_status,
                decision.next_action,
                decision.action_deadline,
                decision.memo,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()