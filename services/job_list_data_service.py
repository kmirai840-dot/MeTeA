"""一覧のデータをまとめて読み、絞り込み・カード描画で再利用する。"""
from database.operation import database_operation
from database.repositories.job_source_repository import get_all_job_sources
from services.current_user_service import get_current_user_id
from services.job_service import load_jobs
from services.job_evaluation_service import load_job_match_evaluations, load_job_application_decisions


@database_operation
def load_job_list_data():
    return dict(jobs=load_jobs(), evaluations=load_job_match_evaluations(),
                decisions=load_job_application_decisions(),
                sources=get_all_job_sources(get_current_user_id()))
