"""トップ画面へ表示するプロダクト横断活動のRepository。"""

from database.access_control import require_user_id
from database.connection import get_connection


def _local_time(connection, expression):
    # DBの更新日時はUTC。画面の活動時刻は日本時間に揃える。
    if getattr(connection, 'dialect', '') == 'postgresql':
        source = "now() AT TIME ZONE 'Asia/Tokyo'" if expression == "'now'" else f"CAST({expression} AS timestamp) + INTERVAL '9 hours'"
        return f"to_char({source}, 'YYYY-MM-DD HH24:MI:SS')"
    return f"datetime({expression}, '+9 hours')"


def save_general_activity(user_id: int, activity_type: str, title: str,
                          target_page: str = "home", target_id: int | None = None,
                          icon_name: str = "user.svg") -> int:
    user_id = require_user_id(user_id)
    connection = get_connection()
    try:
        cursor = connection.execute(
            f"""INSERT INTO user_general_activities
               (user_id, activity_type, title, occurred_at, target_page, target_id, icon_name)
               VALUES (?, ?, ?, {_local_time(connection, "'now'")}, ?, ?, ?)""",
            (user_id, activity_type, title, target_page, target_id, icon_name),
        )
        connection.commit()
        return int(cursor.lastrowid)
    finally:
        connection.close()


def get_home_activities(user_id: int, limit: int = 3) -> list[dict]:
    """自己理解・求人・比較・応募管理を横断して最近の活動を返す。"""
    user_id = require_user_id(user_id)
    connection = get_connection()
    try:
        rows = connection.execute(
            f"""
            SELECT title, occurred_at, target_page, target_id, icon_name FROM (
              SELECT *, ROW_NUMBER() OVER (
                PARTITION BY activity_group
                ORDER BY occurred_at DESC
              ) AS activity_rank
              FROM (
              SELECT title, occurred_at, target_page, target_id, icon_name,
                     activity_type AS activity_group
              FROM user_general_activities WHERE user_id = ?
              UNION ALL
              SELECT '基本情報を更新しました', {_local_time(connection, "updated_at")}, 'basic_info', NULL, 'user.svg', 'basic_info_updated'
              FROM user_profiles WHERE user_id = ? AND deleted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM user_general_activities g WHERE g.user_id = ? AND g.activity_type = 'basic_info_updated')
              UNION ALL
              SELECT '希望条件を更新しました', {_local_time(connection, "updated_at")}, 'hope_conditions', NULL, 'user.svg', 'hope_conditions_updated'
              FROM user_hope_conditions WHERE user_id = ? AND deleted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM user_general_activities g WHERE g.user_id = ? AND g.activity_type = 'hope_conditions_updated')
              UNION ALL
              SELECT '就活の軸を更新しました', {_local_time(connection, "MAX(updated_at)")}, 'job_hunting_axis', NULL, 'user.svg', 'job_hunting_axis_updated'
              FROM user_job_hunting_axes WHERE user_id = ? AND deleted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM user_general_activities g WHERE g.user_id = ? AND g.activity_type = 'job_hunting_axis_updated') HAVING COUNT(*) > 0
              UNION ALL
              SELECT '価値観を更新しました', {_local_time(connection, "MAX(updated_at)")}, 'work_values', NULL, 'user.svg', 'work_values_updated'
              FROM user_work_value_rankings WHERE user_id = ? AND deleted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM user_general_activities g WHERE g.user_id = ? AND g.activity_type = 'work_values_updated') HAVING COUNT(*) > 0
              UNION ALL
              SELECT '職務経歴・スキルを更新しました', {_local_time(connection, "MAX(updated_at)")}, 'career', NULL, 'user.svg', 'career_updated'
              FROM user_careers WHERE user_id = ? AND deleted_at IS NULL
                AND NOT EXISTS (SELECT 1 FROM user_general_activities g WHERE g.user_id = ? AND g.activity_type = 'career_updated') HAVING COUNT(*) > 0
              UNION ALL
              SELECT CASE WHEN company_name <> '' THEN company_name || 'の求人を登録しました'
                          ELSE '求人を登録しました' END,
                     {_local_time(connection, "created_at")}, 'job_detail', id, 'compare.svg', 'job_registered'
              FROM user_jobs WHERE user_id = ? AND deleted_at IS NULL
              UNION ALL
              SELECT x.title, x.occurred_at, 'application_detail', x.application_id, 'flag.svg', 'application_management'
              FROM application_activities x
              JOIN user_applications a ON a.id = x.application_id
              WHERE a.user_id = ? AND a.deleted_at IS NULL
              )
            ) WHERE activity_rank = 1
              ORDER BY occurred_at DESC LIMIT ?
            """,
            (user_id, user_id, user_id, user_id, user_id, user_id,
             user_id, user_id, user_id, user_id, user_id,
             user_id, user_id, limit),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]
