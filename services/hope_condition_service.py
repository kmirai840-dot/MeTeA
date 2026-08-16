"""希望条件の下書き保存・正式保存・取得を担当する。"""

from database.repositories.draft_repository import (
    get_draft,
    save_draft,
)
from database.repositories.hope_condition_repository import (
    get_hope_condition,
    get_hope_condition_items,
    save_hope_conditions,
)
from models import HopeCondition, HopeConditionItem
from services.current_user_service import get_current_user_id
from services.job_matching_cache_service import (
    invalidate_current_user_job_evaluations,
)


HOPE_CONDITIONS_FORM_NAME = "hope_conditions"


def save_hope_conditions_draft(
    draft_data: dict[str, object],
) -> None:
    """希望条件の入力途中データを保存する。"""

    save_draft(
        user_id=get_current_user_id(),
        form_name=HOPE_CONDITIONS_FORM_NAME,
        draft_data=draft_data,
    )


def load_hope_conditions_draft() -> dict[str, object] | None:
    """希望条件の入力途中データを取得する。"""

    return get_draft(
        user_id=get_current_user_id(),
        form_name=HOPE_CONDITIONS_FORM_NAME,
    )


def save_hope_conditions_data(
    hope_condition: HopeCondition,
    items: list[HopeConditionItem],
) -> None:
    """希望条件を正式保存する。"""

    user_id = get_current_user_id()

    saved_hope_condition = get_hope_condition(
        user_id,
    )
    saved_items = get_hope_condition_items(
        user_id,
    )

    save_hope_conditions(
        user_id=user_id,
        hope_condition=hope_condition,
        items=items,
        draft_form_name=HOPE_CONDITIONS_FORM_NAME,
    )

    if (
        saved_hope_condition != hope_condition
        or saved_items != items
    ):
        invalidate_current_user_job_evaluations(
            reason="希望条件が変更されました。",
        )


def load_hope_conditions_data(
) -> tuple[HopeCondition | None, list[HopeConditionItem]]:
    """正式保存済みの希望条件を取得する。"""

    user_id = get_current_user_id()

    hope_condition = get_hope_condition(user_id)
    items = get_hope_condition_items(user_id)

    return hope_condition, items