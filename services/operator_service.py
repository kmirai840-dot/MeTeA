"""運営者専用の読取・出力。通常の本人用Repositoryとは入口を分離する。"""
import csv
import io
import json
import zipfile
from datetime import datetime, timezone

from database.connection import get_connection
from database.access_control import DataAccessDenied
from services.current_user_service import get_current_user_id
from services.google_auth_service import auth_mode, allowed_emails, require_account_enabled


def require_operator():
    import streamlit as st
    if auth_mode() != 'google' or not st.user.is_logged_in:
        raise DataAccessDenied('運営者としてのログインが必要です。')
    admins = allowed_emails({'access': {'allowed_emails': st.secrets.get('access', {}).get('admin_emails', [])}})
    uid = get_current_user_id()
    require_account_enabled(uid, allowed_emails(st.secrets))
    claims = dict(st.user)
    c = get_connection()
    try:
        row = c.execute('SELECT email, auth_subject FROM users WHERE id=?', (uid,)).fetchone()
        if (not row or str(row['email']).casefold() not in admins
                or claims.get('sub') != row['auth_subject']
                or str(claims.get('email', '')).strip().casefold() != str(row['email']).casefold()
                or claims.get('email_verified') is not True
                or claims.get('iss') not in {'accounts.google.com', 'https://accounts.google.com'}):
            raise DataAccessDenied('この画面を利用する権限がありません。')
        return uid
    finally:
        c.close()


def is_operator():
    try:
        require_operator()
        return True
    except (PermissionError, ValueError):
        return False


def list_users():
    require_operator()
    c = get_connection()
    try:
        return [dict(r) for r in c.execute('SELECT id, email, display_name, auth_provider, is_active, deleted_at, last_login_at FROM users ORDER BY id').fetchall()]
    finally:
        c.close()


# 固定された表名だけを使用する。ブラウザからSQLや表名を受け取らない。
DIRECT_TABLES = (
    'user_profiles', 'user_hope_conditions', 'user_hope_condition_items',
    'user_job_hunting_axes', 'form_drafts', 'user_work_value_rankings',
    'user_work_value_details', 'user_work_style_answers', 'user_careers',
    'user_jobs', 'user_job_commute_checks', 'user_job_match_evaluations',
    'user_job_application_decisions', 'user_job_confirmation_resolutions',
    'user_applications', 'user_preparation_templates', 'user_general_activities',
)
CHILD_TABLES = {
    'user_career_histories': ('user_careers', 'career_id'),
    'user_job_items': ('user_jobs', 'job_id'),
    'user_job_sources': ('user_jobs', 'job_id'),
    'application_phase_history': ('user_applications', 'application_id'),
    'application_milestones': ('user_applications', 'application_id'),
    'application_activities': ('user_applications', 'application_id'),
    'application_preparations': ('user_applications', 'application_id'),
}


def read_user_data(user_id):
    operator_id = require_operator()
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise ValueError('利用者を選択してください。')
    c = get_connection()
    try:
        if getattr(c, 'dialect', '') == 'postgresql':
            c.raw.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        else:
            c.execute('BEGIN')
        user = c.execute('SELECT id, email, display_name, auth_provider, is_active, created_at, updated_at, deleted_at, last_login_at FROM users WHERE id=?', (user_id,)).fetchone()
        if user is None:
            raise DataAccessDenied('利用者が見つかりません。')
        tables = {'users': [dict(user)]}
        for table in DIRECT_TABLES:
            tables[table] = [dict(r) for r in c.execute(f'SELECT * FROM {table} WHERE user_id=? ORDER BY id', (user_id,)).fetchall()]
        for table, (parent, key) in CHILD_TABLES.items():
            tables[table] = [dict(r) for r in c.execute(f'SELECT child.* FROM {table} child JOIN {parent} parent ON child.{key}=parent.id WHERE parent.user_id=? ORDER BY child.id', (user_id,)).fetchall()]
        return {'exported_at': datetime.now(timezone.utc).isoformat(), 'operator_id': operator_id,
                'user_id': user_id, 'tables': tables}
    finally:
        c.close()


def _csv_cell(value):
    # 表計算ソフトで利用者入力を数式として実行させない。原文はJSONに保持する。
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def export_user_data(user_id):
    data = read_user_data(user_id)  # 出力ごとに再認可。共有キャッシュに載せない。
    raw_json = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('data.json', raw_json)
        archive.writestr('README.txt', '選択利用者の保存データです。論理削除済みを含みます。\n空の表はdata.jsonで確認できます。CSVは数式起動を防ぐため一部のセル先頭にアポストロフィを付けています。原文はJSONに保持しています。\n認証subject・画像URL・接続秘密情報は含めません。個人データとして管理してください。')
        for table, rows in data['tables'].items():
            if not rows:
                continue
            text = io.StringIO(newline='')
            writer = csv.writer(text)
            writer.writerow(rows[0].keys())
            writer.writerows([_csv_cell(v) for v in row.values()] for row in rows)
            archive.writestr(table + '.csv', text.getvalue().encode('utf-8-sig'))
    return output.getvalue()
