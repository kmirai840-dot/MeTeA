"""詳細画面の初期データを1操作で取得。描画・ボタン保存はトランザクション外。"""
from database.operation import database_operation
from services.job_service import load_job
from services.job_evaluation_service import load_job_match_evaluations, load_job_application_decisions
from services.basic_info_service import load_basic_info
from services.job_commute_service import load_current_job_commute
from services.job_confirmation_service import load_job_confirmation_resolutions


@database_operation
def load_job_detail_data(job_id):
    job = load_job(job_id)
    if job is None:
        return None
    basic = load_basic_info()
    commute = None
    if basic and basic.nearest_station_place_id:
        commute = load_current_job_commute(job_id, basic.nearest_station_place_id, job.nearest_station, job=job)
    return dict(job=job, basic=basic, commute=commute,
                evaluations=load_job_match_evaluations(),
                resolutions=load_job_confirmation_resolutions(job_id),
                decisions=load_job_application_decisions())
