"""運営者専用の読取・出力。通常の本人用Repositoryとは入口を分離する。"""
import csv
import io
import json
import zipfile
from datetime import datetime, timezone

from database.connection import get_connection
from database.operation import database_operation
from database.access_control import DataAccessDenied
from services.current_user_service import get_current_user_id
from services.google_auth_service import auth_mode, allowed_emails, access_invitations, require_account_enabled


@database_operation
def require_operator():
    import streamlit as st
    if auth_mode() != 'google' or not st.user.is_logged_in:
        raise DataAccessDenied('運営者としてのログインが必要です。')
    uid = get_current_user_id()
    return _require_operator_claims(uid, dict(st.user))


@database_operation
def _require_operator_claims(uid, claims):
    import streamlit as st
    if auth_mode() != 'google':
        raise DataAccessDenied('運営者としてのログインが必要です。')
    admins = allowed_emails({'access': {'allowed_emails': st.secrets.get('access', {}).get('admin_emails', [])}})
    require_account_enabled(uid, access_invitations(st.secrets))
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


@database_operation
def list_users():
    require_operator()
    c = get_connection()
    try:
        return [dict(r) for r in c.execute('SELECT id, email, display_name, auth_provider, is_active, deleted_at, last_login_at FROM users ORDER BY id').fetchall()]
    finally:
        c.close()


# 固定された表名だけを使用する。ブラウザからSQLや表名を受け取らない。
DIRECT_TABLES = (
    'user_skills',
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
    return _read_user_data(user_id, operator_id)


def _validate_user_id(user_id):
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise ValueError('利用者を選択してください。')


def _read_user_data(user_id, operator_id):
    _validate_user_id(user_id)
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
            order_key = 'user_id' if table == 'user_skills' else 'id'
            tables[table] = [dict(r) for r in c.execute(f'SELECT * FROM {table} WHERE user_id=? ORDER BY {order_key}', (user_id,)).fetchall()]
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
    return _zip_user_data(data)


def _zip_user_data(data):
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


def prepare_user_export(user_id):
    """本人セッションに結び付く遅延出力。登録時には業務データもZIPも取得しない。"""
    import streamlit as st
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    from services.current_user_service import CURRENT_USER_SESSION_KEY
    operator_id = require_operator()
    _validate_user_id(user_id)
    ctx = get_script_run_ctx()
    if ctx is None:
        raise DataAccessDenied('ログインした画面から出力してください。')
    session = ctx.session_state
    claims = dict(st.user)

    def download():
        # ログアウト・利用者切替・アカウント停止・運営者権限解除を確認する。
        if CURRENT_USER_SESSION_KEY not in session or session[CURRENT_USER_SESSION_KEY] != operator_id:
            raise DataAccessDenied('再ログインしてください。')
        _require_operator_claims(operator_id, claims)
        return _zip_user_data(_read_user_data(user_id, operator_id))
    return download


USER_EXPORT_COLUMNS = 'id, email, display_name, auth_provider, is_active, created_at, updated_at, deleted_at, last_login_at'


def _table_query(table, count=False):
    if table == 'users':
        return f"SELECT {'COUNT(*) AS total' if count else USER_EXPORT_COLUMNS} FROM users WHERE id=?"
    if table in DIRECT_TABLES:
        order = 'user_id' if table == 'user_skills' else 'id'
        return f"SELECT {'COUNT(*) AS total' if count else '*'} FROM {table} WHERE user_id=?" + ('' if count else f' ORDER BY {order}')
    if table in CHILD_TABLES:
        parent, key = CHILD_TABLES[table]
        return f"SELECT {'COUNT(*) AS total' if count else 'child.*'} FROM {table} child JOIN {parent} parent ON child.{key}=parent.id WHERE parent.user_id=?" + ('' if count else ' ORDER BY child.id')
    raise ValueError('未対応の保存先です。')


@database_operation
def list_user_table_counts(user_id):
    require_operator()
    _validate_user_id(user_id)
    tables = ('users', *DIRECT_TABLES, *CHILD_TABLES)
    c = get_connection()
    try:
        rows = c.execute(' UNION ALL '.join(f"SELECT '{table}' AS name, total FROM ({_table_query(table, True)}) counts" for table in tables), (user_id,)*len(tables)).fetchall()
        counts = {row['name']: row['total'] for row in rows}
        if not counts['users']:
            raise DataAccessDenied('利用者が見つかりません。')
        return counts
    finally:
        c.close()


@database_operation
def read_user_table(user_id, table):
    require_operator()
    _validate_user_id(user_id)
    query = _table_query(table)
    c = get_connection()
    try:
        if not c.execute('SELECT id FROM users WHERE id=?', (user_id,)).fetchone():
            raise DataAccessDenied('利用者が見つかりません。')
        return [dict(row) for row in c.execute(query, (user_id,)).fetchall()]
    finally:
        c.close()
