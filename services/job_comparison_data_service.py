"""比較対象だけを1操作で取得。描画・AI待機は含めない。"""
from database.operation import database_operation
from services.current_user_service import get_current_user_id
from services.job_service import load_jobs
from services.job_evaluation_service import load_job_match_evaluations
from services.basic_info_service import load_basic_info
from services.hope_condition_service import load_hope_conditions_data
from services.job_commute_service import validate_saved_commute_context
from database.repositories.job_commute_repository import get_job_commute_checks
from services.job_matching_rule_evaluation_service import evaluate_rule_hope_groups


@database_operation
def load_comparison_data(job_ids):
    ids = tuple(dict.fromkeys(job_ids))
    jobs = dict(load_jobs(job_ids=ids))
    selected = [(jid, jobs[jid]) for jid in ids if jid in jobs]
    evaluations = load_job_match_evaluations(job_ids=tuple(jobs))
    rules = {}
    if 2 <= len(selected) <= 3:
        hope, items = load_hope_conditions_data()
        basic = load_basic_info()
        commutes = get_job_commute_checks(get_current_user_id(), job_ids=tuple(jobs)) if basic and basic.nearest_station_place_id else {}
        for jid, job in selected:
            commute = validate_saved_commute_context(commutes.get(jid), basic.nearest_station_place_id, job.nearest_station, job) if basic else None
            minutes = commute.duration_minutes if commute else None
            groups = evaluate_rule_hope_groups(job=job, hope_condition=hope, hope_items=items, commute_minutes=minutes)
            rules[jid] = dict(items={item.item_name: item for group in groups.values() for item in group}, commute_minutes=minutes)
    return dict(selected_jobs=selected, evaluations=evaluations, rule_data=rules)
