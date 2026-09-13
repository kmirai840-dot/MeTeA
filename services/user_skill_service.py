"""職歴とは独立した自己申告スキル。"""
from database.operation import database_operation
from database.repositories.user_skill_repository import get_user_skills, save_user_skills
from services.current_user_service import get_current_user_id
from services.job_matching_cache_service import invalidate_current_user_job_evaluations


def load_skills() -> str:
    return get_user_skills(get_current_user_id())


@database_operation
def save_skills(text: str) -> bool:
    text = text.strip()
    if len(text) > 3000:
        raise ValueError("使用できるツール・スキルは3,000文字以内で入力してください。")
    user_id = get_current_user_id()
    if get_user_skills(user_id) == text:
        return False
    save_user_skills(user_id, text)
    invalidate_current_user_job_evaluations("使用できるツール・スキルが変更されました。")
    return True
