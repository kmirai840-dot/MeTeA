"""見直し画面の登録状況と選択カテゴリだけを取得する。"""
from database.operation import database_operation
from database.access_control import require_user_id
from database.connection import get_connection
from services.basic_info_service import load_basic_info, load_basic_info_updated_at
from services.hope_condition_service import load_hope_conditions_data
from services.work_values_service import load_work_values_data
from services.job_hunting_axis_service import load_job_hunting_axis_data
from services.career_service import load_career_data
from services.user_skill_service import load_skills


@database_operation
def load_profile_statuses():
    uid = require_user_id()
    tables = dict(basic='user_profiles', hope='user_hope_conditions',
                  hope_items='user_hope_condition_items', ranks='user_work_value_rankings',
                  details='user_work_value_details', styles='user_work_style_answers',
                  axis='user_job_hunting_axes', career='user_careers')
    queries = [f"SELECT '{key}' AS kind, COUNT(*) AS total FROM {table} WHERE user_id = ?"
               + ('' if key == 'hope_items' else ' AND deleted_at IS NULL') for key, table in tables.items()]
    c = get_connection()
    try:
        counts = {r['kind']: r['total'] for r in c.execute(' UNION ALL '.join(queries), (uid,)*len(queries)).fetchall()}
    finally:
        c.close()
    values = counts['ranks'] + counts['details'] + counts['styles']
    return dict(basic=(bool(counts['basic']), '登録済み' if counts['basic'] else '未登録'),
                hope=(bool(counts['hope'] and counts['hope_items']), f"{counts['hope_items']}件の条件" if counts['hope'] else '未登録'),
                values=(bool(values), f'{values}件の回答' if values else '未登録'),
                axis=(bool(counts['axis']), f"{counts['axis']}件の軸" if counts['axis'] else '未登録'),
                career=(bool(counts['career']), f"{counts['career']}社" if counts['career'] else '未登録'))


@database_operation
def load_profile_review_data(category):
    snapshot = dict(statuses=load_profile_statuses())
    loaders = dict(basic=load_basic_info, hope=load_hope_conditions_data,
                   values=load_work_values_data, axis=load_job_hunting_axis_data, career=load_career_data)
    if category in loaders:
        snapshot['data'] = loaders[category]()
    if category == 'basic':
        snapshot['updated_at'] = load_basic_info_updated_at()
    if category == 'career':
        snapshot['skills'] = load_skills()
    return snapshot
