"""応募後管理に関するSQLite Repository。"""

from database.connection import get_connection
from models import (ApplicationActivity, ApplicationMilestone, ApplicationPreparation,
                    ApplicationRecord, UserPreparationTemplate)


def get_applications(user_id: int, include_closed: bool = True) -> list[ApplicationRecord]:
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT * FROM user_applications
            WHERE user_id = ? AND deleted_at IS NULL
              AND (? = 1 OR status = 'active')
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id, int(include_closed)),
        ).fetchall()
    finally:
        connection.close()
    return [_row_to_application(row) for row in rows]


def get_application(user_id: int, application_id: int) -> ApplicationRecord | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM user_applications WHERE user_id = ? AND id = ? AND deleted_at IS NULL",
            (user_id, application_id),
        ).fetchone()
    finally:
        connection.close()
    return _row_to_application(row) if row else None


def get_application_by_job_route(user_id: int, job_id: int, actual_route: str) -> ApplicationRecord | None:
    connection = get_connection()
    try:
        row = connection.execute(
            """SELECT * FROM user_applications
               WHERE user_id = ? AND job_id = ? AND actual_route = ? AND deleted_at IS NULL""",
            (user_id, job_id, actual_route),
        ).fetchone()
    finally:
        connection.close()
    return _row_to_application(row) if row else None


def save_application(application: ApplicationRecord) -> int:
    connection = get_connection()
    try:
        if application.id:
            connection.execute(
                """UPDATE user_applications SET actual_route = ?, current_phase = ?,
                   phase_category = ?, selection_stage = ?, selection_result = ?, application_date = ?, status = ?,
                   notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?""",
                (application.actual_route, application.current_phase, application.phase_category,
                 application.selection_stage, application.selection_result, application.application_date, application.status,
                 application.notes, application.id, application.user_id),
            )
            application_id = application.id
        else:
            cursor = connection.execute(
                """INSERT INTO user_applications
                   (user_id, job_id, actual_route, current_phase, phase_category,
                    selection_stage, selection_result, application_date, status, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, job_id, actual_route) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP, deleted_at = NULL""",
                (application.user_id, application.job_id, application.actual_route,
                 application.current_phase, application.phase_category, application.selection_stage,
                 application.selection_result, application.application_date,
                 application.status, application.notes),
            )
            application_id = int(cursor.lastrowid or 0)
            if not application_id:
                row = connection.execute(
                    "SELECT id FROM user_applications WHERE user_id = ? AND job_id = ? AND actual_route = ?",
                    (application.user_id, application.job_id, application.actual_route),
                ).fetchone()
                application_id = int(row["id"])
        connection.commit()
        return application_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_phase_history(application_id: int, phase: str, category: str, result: str = "",
                      selection_stage: str = "") -> None:
    connection = get_connection()
    try:
        connection.execute(
            """INSERT INTO application_phase_history
               (application_id, phase_name, phase_category, selection_result, selection_stage)
               VALUES (?, ?, ?, ?, ?)""",
            (application_id, phase, category, result, selection_stage),
        )
        connection.commit()
    finally:
        connection.close()


def get_milestones(application_id: int | None = None, user_id: int | None = None) -> list[ApplicationMilestone]:
    connection = get_connection()
    try:
        if application_id is not None:
            rows = connection.execute(
                "SELECT * FROM application_milestones WHERE application_id = ? AND deleted_at IS NULL ORDER BY scheduled_date, id",
                (application_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT m.* FROM application_milestones m
                   JOIN user_applications a ON a.id = m.application_id
                   WHERE a.user_id = ? AND a.deleted_at IS NULL AND m.deleted_at IS NULL
                   ORDER BY m.scheduled_date, m.id""",
                (user_id,),
            ).fetchall()
    finally:
        connection.close()
    return [_row_to_milestone(row) for row in rows]


def save_milestone(milestone: ApplicationMilestone) -> int:
    connection = get_connection()
    try:
        if milestone.id:
            connection.execute(
                """UPDATE application_milestones SET milestone_type = ?, detail_name = ?, title = ?,
                   schedule_kind = ?, scheduled_date = ?, start_time = ?, end_time = ?, status = ?,
                   rescheduled_from_id = ?, memo = ?, completed_at = ?, cancelled_at = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (milestone.milestone_type, milestone.detail_name, milestone.title,
                 milestone.schedule_kind, milestone.scheduled_date, milestone.start_time,
                 milestone.end_time, milestone.status, milestone.rescheduled_from_id,
                 milestone.memo, milestone.completed_at, milestone.cancelled_at, milestone.id),
            )
            milestone_id = milestone.id
        else:
            cursor = connection.execute(
                """INSERT INTO application_milestones
                   (application_id, milestone_type, detail_name, title, schedule_kind,
                    scheduled_date, start_time, end_time, status, rescheduled_from_id,
                    memo, completed_at, cancelled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (milestone.application_id, milestone.milestone_type, milestone.detail_name,
                 milestone.title, milestone.schedule_kind, milestone.scheduled_date,
                 milestone.start_time, milestone.end_time, milestone.status,
                 milestone.rescheduled_from_id, milestone.memo, milestone.completed_at,
                 milestone.cancelled_at),
            )
            milestone_id = int(cursor.lastrowid)
        connection.commit()
        return milestone_id
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_milestone(milestone_id: int) -> bool:
    """誤登録の予定を物理削除する。延期先からの参照は先に解除する。"""

    connection = get_connection()
    try:
        connection.execute(
            "UPDATE application_milestones SET rescheduled_from_id = NULL WHERE rescheduled_from_id = ?",
            (milestone_id,),
        )
        cursor = connection.execute("DELETE FROM application_milestones WHERE id = ?", (milestone_id,))
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_phase_history(application_id: int | None = None, user_id: int | None = None) -> list[dict]:
    connection = get_connection()
    try:
        if application_id is not None:
            rows = connection.execute(
                "SELECT * FROM application_phase_history WHERE application_id = ? ORDER BY changed_at, id",
                (application_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT h.* FROM application_phase_history h
                   JOIN user_applications a ON a.id = h.application_id
                   WHERE a.user_id = ? AND a.deleted_at IS NULL
                   ORDER BY h.changed_at, h.id""",
                (user_id,),
            ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def get_activities(application_id: int | None = None, user_id: int | None = None, limit: int = 100) -> list[ApplicationActivity]:
    connection = get_connection()
    try:
        if application_id is not None:
            rows = connection.execute(
                "SELECT * FROM application_activities WHERE application_id = ? ORDER BY occurred_at DESC, id DESC LIMIT ?",
                (application_id, limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT x.* FROM application_activities x JOIN user_applications a ON a.id = x.application_id
                   WHERE a.user_id = ? AND a.deleted_at IS NULL ORDER BY x.occurred_at DESC, x.id DESC LIMIT ?""",
                (user_id, limit),
            ).fetchall()
    finally:
        connection.close()
    return [_row_to_activity(row) for row in rows]


def save_activity(activity: ApplicationActivity) -> int:
    connection = get_connection()
    try:
        cursor = connection.execute(
            """INSERT INTO application_activities
               (application_id, activity_type, occurred_at, title, detail, is_automatic)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (activity.application_id, activity.activity_type, activity.occurred_at,
             activity.title, activity.detail, int(activity.is_automatic)),
        )
        connection.commit()
        return int(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_preparations(application_id: int) -> list[ApplicationPreparation]:
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM application_preparations WHERE application_id = ? ORDER BY scope, sort_order, id",
            (application_id,),
        ).fetchall()
    finally:
        connection.close()
    return [_row_to_preparation(row) for row in rows]


def save_preparation(item: ApplicationPreparation) -> int:
    connection = get_connection()
    try:
        cursor = connection.execute(
            """INSERT INTO application_preparations
               (application_id, scope, selection_type, theme_key, title, description,
                content, is_completed, is_custom, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(application_id, scope, selection_type, theme_key) DO UPDATE SET
                 title=excluded.title, description=excluded.description, content=excluded.content,
                 is_completed=excluded.is_completed, sort_order=excluded.sort_order,
                 updated_at=CURRENT_TIMESTAMP""",
            (item.application_id, item.scope, item.selection_type, item.theme_key,
             item.title, item.description, item.content, int(item.is_completed),
             int(item.is_custom), item.sort_order),
        )
        connection.commit()
        if cursor.lastrowid:
            return int(cursor.lastrowid)
        row = connection.execute(
            """SELECT id FROM application_preparations
               WHERE application_id=? AND scope=? AND selection_type=? AND theme_key=?""",
            (item.application_id, item.scope, item.selection_type, item.theme_key),
        ).fetchone()
        return int(row["id"])
    finally:
        connection.close()


def delete_preparation(preparation_id: int, application_id: int) -> bool:
    """応募に追加した準備テーマを物理削除する。"""
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM application_preparations WHERE id = ? AND application_id = ? AND is_custom = 1",
            (preparation_id, application_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_user_preparation_templates(user_id: int) -> list[UserPreparationTemplate]:
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM user_preparation_templates WHERE user_id = ? ORDER BY sort_order, id",
            (user_id,),
        ).fetchall()
    finally:
        connection.close()
    return [_row_to_user_preparation_template(row) for row in rows]


def save_user_preparation_template(item: UserPreparationTemplate) -> int:
    connection = get_connection()
    try:
        cursor = connection.execute(
            """INSERT INTO user_preparation_templates
               (user_id, theme_key, title, description, content, is_completed, is_custom, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, theme_key) DO UPDATE SET
                 title=excluded.title, description=excluded.description, content=excluded.content,
                 is_completed=excluded.is_completed, is_custom=excluded.is_custom,
                 sort_order=excluded.sort_order, updated_at=CURRENT_TIMESTAMP""",
            (item.user_id, item.theme_key, item.title, item.description, item.content,
             int(item.is_completed), int(item.is_custom), item.sort_order),
        )
        connection.commit()
        if cursor.lastrowid:
            return int(cursor.lastrowid)
        row = connection.execute(
            "SELECT id FROM user_preparation_templates WHERE user_id=? AND theme_key=?",
            (item.user_id, item.theme_key),
        ).fetchone()
        return int(row["id"])
    finally:
        connection.close()


def delete_user_preparation_template(template_id: int, user_id: int) -> bool:
    """利用者が追加した共通準備テーマを物理削除する。"""
    connection = get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM user_preparation_templates WHERE id = ? AND user_id = ? AND is_custom = 1",
            (template_id, user_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _row_to_application(row) -> ApplicationRecord:
    return ApplicationRecord(**{key: row[key] for key in (
        "id", "user_id", "job_id", "actual_route", "current_phase", "phase_category",
        "selection_stage", "selection_result", "application_date", "status", "notes", "created_at", "updated_at")})


def _row_to_milestone(row) -> ApplicationMilestone:
    return ApplicationMilestone(**{key: row[key] for key in (
        "id", "application_id", "milestone_type", "detail_name", "title", "schedule_kind",
        "scheduled_date", "start_time", "end_time", "status", "rescheduled_from_id",
        "memo", "completed_at", "cancelled_at",
        "created_at", "updated_at")})


def _row_to_activity(row) -> ApplicationActivity:
    values = {key: row[key] for key in (
        "id", "application_id", "activity_type", "occurred_at", "title", "detail", "created_at")}
    values["is_automatic"] = bool(row["is_automatic"])
    return ApplicationActivity(**values)


def _row_to_preparation(row) -> ApplicationPreparation:
    values = {key: row[key] for key in (
        "id", "application_id", "scope", "selection_type", "theme_key", "title",
        "description", "content", "sort_order", "created_at", "updated_at")}
    values["is_completed"] = bool(row["is_completed"])
    values["is_custom"] = bool(row["is_custom"])
    return ApplicationPreparation(**values)


def _row_to_user_preparation_template(row) -> UserPreparationTemplate:
    values = {key: row[key] for key in (
        "id", "user_id", "theme_key", "title", "description", "content", "sort_order",
        "created_at", "updated_at")}
    values["is_completed"] = bool(row["is_completed"])
    values["is_custom"] = bool(row["is_custom"])
    return UserPreparationTemplate(**values)
