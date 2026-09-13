"""確認済みの数値条件を、保存済みAI意味判定と再合成する（AI呼出しなし）。"""
from dataclasses import asdict, replace
import hashlib
import json
from models import JobAISemanticEvaluation, AISemanticMatchItem
from services.job_matching_rule_service import EVALUATION_RULE_VERSION


def rebuild_numeric_evaluation(evaluation, job, basic, hope, hope_items, commute, confirmed_names):
    from services.job_matching_evaluation_service import build_complete_job_matching_result
    from services.job_matching_rule_evaluation_service import evaluate_rule_hope_groups
    from services.job_commute_service import validate_saved_commute_context
    try:
        payload=json.loads(evaluation.evaluation_result_json)
        semantic=JobAISemanticEvaluation(**{k:v for k,v in payload.items() if k in {'job_id','model_name','prompt_version','evaluated_at'}},
            items=[AISemanticMatchItem(**item) for item in payload['items']])
    except (ValueError,TypeError,KeyError,AttributeError):
        return evaluation
    if semantic.job_id != evaluation.job_id:
        return evaluation
    valid_commute=validate_saved_commute_context(commute,basic.nearest_station_place_id if basic else '',job.nearest_station,job)
    signature=hashlib.sha256(json.dumps([EVALUATION_RULE_VERSION,asdict(job),asdict(hope) if hope else None,
        [asdict(i) for i in hope_items],asdict(valid_commute) if valid_commute else None,sorted(confirmed_names)],
        ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
    if payload.get('_numeric_signature') == signature:
        return evaluation
    groups=evaluate_rule_hope_groups(job,hope,hope_items,valid_commute.duration_minutes if valid_commute else None)
    # 手動確認された意味判定を優先する。通勤・年収は確認済み数値から判定する。
    replacement_names={i.item_name for i in semantic.items if i.category=='hope_condition' and i.item_name in confirmed_names and i.item_name not in {'電車移動時間','年収'}}
    groups={key:[item for item in rows if item.item_name not in replacement_names] for key,rows in groups.items()}
    semantic=replace(semantic,items=[i for i in semantic.items if not (i.category=='hope_condition' and i.item_name in {'電車移動時間','年収'})])
    rebuilt=build_complete_job_matching_result(evaluation.job_id,groups,semantic).evaluation
    payload=json.loads(rebuilt.evaluation_result_json)
    payload['_numeric_signature']=signature
    return replace(rebuilt,evaluation_result_json=json.dumps(payload,ensure_ascii=False,sort_keys=True),
        evaluation_status=evaluation.evaluation_status,is_stale=evaluation.is_stale,stale_reason=evaluation.stale_reason,
        failure_reason=evaluation.failure_reason,failed_at=evaluation.failed_at,retry_count=evaluation.retry_count,
        result_notice_pending=evaluation.result_notice_pending)


def refresh_numeric_evaluations(evaluations, force_job_id=None):
    # プロフィール・求人の正式保存は既存の無効化処理で is_stale を立てる。
    # 通勤保存は force_job_id を渡す。変更のない画面表示では追加のDB取得をしない。
    candidates={jid:e for jid,e in evaluations.items() if e.evaluation_result_json and (
        jid == force_job_id or e.is_stale or e.rule_version != EVALUATION_RULE_VERSION
        or '"_numeric_signature"' not in e.evaluation_result_json)}
    if not candidates:
        return evaluations
    from services.current_user_service import get_current_user_id
    from services.basic_info_service import load_basic_info
    from services.hope_condition_service import load_hope_conditions_data
    from services.job_service import load_jobs
    from database.repositories.job_commute_repository import get_job_commute_checks
    from database.connection import get_connection
    from database.repositories.job_evaluation_repository import save_job_match_evaluation
    uid=get_current_user_id()
    basic=load_basic_info();hope,items=load_hope_conditions_data()
    from database.query_scope import id_scope
    ids = tuple(candidates)
    jobs=dict(load_jobs(job_ids=ids));commutes=get_job_commute_checks(uid, job_ids=ids)
    connection=get_connection()
    try:
        scope, parameters = id_scope('job_id', ids)
        records=connection.execute(f"SELECT job_id,item_name FROM user_job_confirmation_resolutions WHERE user_id=? AND status='confirmed'{scope}",(uid, *parameters)).fetchall()
    finally:
        connection.close()
    confirmed={}
    for row in records:
        confirmed.setdefault(row['job_id'],set()).add(row['item_name'])
    result=dict(evaluations)
    for jid,evaluation in candidates.items():
        if jid not in jobs:
            continue
        updated=rebuild_numeric_evaluation(evaluation,jobs[jid],basic,hope,items,commutes.get(jid),confirmed.get(jid,set()))
        result[jid]=updated
        if updated is not evaluation and evaluation.evaluation_status not in {'running','queued'}:
            save_job_match_evaluation(uid,updated)
    return result
