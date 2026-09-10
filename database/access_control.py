"""Repository境界で、操作中の本人と親データの所有者を確認する。"""
from __future__ import annotations

from services.current_user_service import get_current_user_id


class DataAccessDenied(PermissionError):
    """存在の有無を区別せず、他人・削除済みデータへのアクセスを拒否する。"""


def require_user_id(user_id: int | None = None) -> int:
    current = get_current_user_id()
    if user_id is not None and user_id != current:
        raise DataAccessDenied("このデータを操作する権限がありません。")
    from services.google_auth_service import auth_mode, allowed_emails, require_account_enabled
    if auth_mode() == "google":
        import streamlit as st
        require_account_enabled(current, allowed_emails(st.secrets))
    return current


def require_job_owner(connection, job_id: int, user_id: int) -> None:
    row = connection.execute(
        "SELECT id FROM user_jobs WHERE id = ? AND user_id = ? AND deleted_at IS NULL",
        (job_id, user_id),
    ).fetchone()
    if row is None:
        raise DataAccessDenied("求人が見つからないか、操作する権限がありません。")


def require_application_owner(connection, application_id: int, user_id: int) -> None:
    row = connection.execute(
        """SELECT a.id FROM user_applications a JOIN user_jobs j ON j.id = a.job_id
           WHERE a.id = ? AND a.user_id = ? AND j.user_id = a.user_id
             AND a.deleted_at IS NULL AND j.deleted_at IS NULL""",
        (application_id, user_id),
    ).fetchone()
    if row is None:
        raise DataAccessDenied("応募情報が見つからないか、操作する権限がありません。")


def require_child_owner(connection, table: str, record_id: int, user_id: int,
                        application_id: int | None = None) -> None:
    if table not in {"application_milestones", "application_preparations"}:
        raise ValueError("未対応の所有者確認です。")
    active = "AND child.deleted_at IS NULL" if table == "application_milestones" else ""
    row = connection.execute(
        f"""SELECT child.application_id FROM {table} child
            JOIN user_applications a ON a.id = child.application_id
            JOIN user_jobs j ON j.id = a.job_id
            WHERE child.id = ? AND a.user_id = ? AND j.user_id = a.user_id
              AND a.deleted_at IS NULL AND j.deleted_at IS NULL {active}""",
        (record_id, user_id),
    ).fetchone()
    if row is None or (application_id is not None and row[0] != application_id):
        raise DataAccessDenied("対象が見つからないか、操作する権限がありません。")


def require_template_owner(connection, template_id: int, user_id: int) -> None:
    if connection.execute(
        "SELECT id FROM user_preparation_templates WHERE id = ? AND user_id = ?",
        (template_id, user_id),
    ).fetchone() is None:
        raise DataAccessDenied("準備テーマが見つからないか、操作する権限がありません。")
