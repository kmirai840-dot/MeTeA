"""ホームの描画データを1回のDB操作で取得する。描画中は接続を保持しない。"""
from database.operation import database_operation
from database.repositories.home_activity_repository import get_home_activities
from services.application_management_service import load_application_views
from services.current_user_service import get_current_user_id
from services.home_next_step_service import load_next_step


@database_operation
def load_home_data():
    views = load_application_views(False)
    return dict(application_views=views, next_step=load_next_step(views),
                activities=get_home_activities(get_current_user_id(), limit=3))
