"""ホームの案内に必要な本人の保存状況だけを取得する。"""
from database.access_control import require_user_id
from database.connection import get_connection


def get_home_progress(user_id: int) -> dict:
    user_id = require_user_id(user_id)
    # テーブル・条件は固定値。入力内容そのものをホームへ運ばない。
    checks = [
        ("basic_info", "user_profiles", "deleted_at IS NULL AND last_name <> '' AND first_name <> '' AND birth_date <> '' AND prefecture <> '' AND municipality <> '' AND nearest_station <> ''"),
        ("hope_conditions", "user_hope_conditions", "deleted_at IS NULL AND minimum_salary > 0 AND desired_salary >= minimum_salary"),
        ("job_hunting_axis", "user_job_hunting_axes", "deleted_at IS NULL AND axis_title <> '' AND axis_description <> ''"),
        ("career", "user_careers", "deleted_at IS NULL AND company_name <> ''"),
        ("jobs", "user_jobs", "deleted_at IS NULL"),
        ("applications", "user_applications", "deleted_at IS NULL"),
    ]
    queries = [f"SELECT '{key}' AS kind, COUNT(*) AS total FROM {table} WHERE user_id = ? AND {where}" for key, table, where in checks]
    queries += [
        "SELECT 'hope_' || condition_type AS kind, COUNT(*) AS total FROM user_hope_condition_items WHERE user_id = ? AND condition_value <> '' GROUP BY condition_type",
        "SELECT 'rank_' || question_type AS kind, COUNT(DISTINCT priority_rank) AS total FROM user_work_value_rankings WHERE user_id = ? AND deleted_at IS NULL AND selected_value <> '' AND priority_rank BETWEEN 1 AND 3 GROUP BY question_type",
        "SELECT 'style_' || question_type AS kind, COUNT(*) AS total FROM user_work_style_answers WHERE user_id = ? AND deleted_at IS NULL AND answer_score BETWEEN 1 AND 5 GROUP BY question_type",
        "SELECT 'undecided_jobs' AS kind, COUNT(*) AS total FROM user_jobs j LEFT JOIN user_job_application_decisions d ON d.job_id=j.id AND d.user_id=j.user_id AND d.deleted_at IS NULL WHERE j.user_id = ? AND j.deleted_at IS NULL AND (d.id IS NULL OR d.decision_status IN ('', '未判断', '検討中', '保留', '条件を確認して応募'))",
        "SELECT 'application_intents' AS kind, COUNT(*) AS total FROM user_jobs j JOIN user_job_application_decisions d ON d.job_id=j.id AND d.user_id=j.user_id AND d.deleted_at IS NULL WHERE j.user_id = ? AND j.deleted_at IS NULL AND d.decision_status IN ('応募する', '他経路から応募する', '条件を確認して応募') AND NOT EXISTS (SELECT 1 FROM user_applications a WHERE a.user_id=j.user_id AND a.job_id=j.id AND a.deleted_at IS NULL)",
    ]
    db = get_connection()
    try:
        counts = {row['kind']: row['total'] for row in db.execute(' UNION ALL '.join(queries), (user_id,) * len(queries)).fetchall()}
        drafts = [row['form_name'] for row in db.execute("SELECT form_name FROM form_drafts WHERE user_id = ? ORDER BY updated_at DESC, id DESC", (user_id,)).fetchall()]
        return {'counts': counts, 'drafts': drafts}
    finally:
        db.close()
