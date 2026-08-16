"""就活の軸の入力確認・保存・取得を担当する。"""

from database.repositories.draft_repository import (
    get_draft,
    save_draft,
)
from database.repositories.job_hunting_axis_repository import (
    get_job_hunting_axes,
    save_job_hunting_axes,
)
from models import JobHuntingAxis
from services.current_user_service import get_current_user_id
from services.job_matching_cache_service import (
    invalidate_current_user_job_evaluations,
)


JOB_HUNTING_AXIS_FORM_NAME = "job_hunting_axis"

MAX_AXIS_COUNT = 3
MAX_AXIS_TITLE_LENGTH = 50
MAX_AXIS_DESCRIPTION_LENGTH = 200


def validate_job_hunting_axes(
    axes: list[JobHuntingAxis],
) -> tuple[list[JobHuntingAxis] | None, list[str]]:
    """就活の軸を確認し、保存用に順位を整える。"""

    errors: list[str] = []

    if not axes:
        errors.append(
            "就活の軸を1件以上登録してください。"
        )

    if len(axes) > MAX_AXIS_COUNT:
        errors.append(
            "登録できる就活の軸は最大3件です。"
        )

    normalized_titles: list[str] = []
    validated_axes: list[JobHuntingAxis] = []

    for index, axis in enumerate(axes, start=1):
        axis_title = axis.axis_title.strip()
        axis_description = axis.axis_description.strip()

        if not axis_title:
            errors.append(
                f"{index}件目の軸の名称を入力してください。"
            )
            continue

        if len(axis_title) > MAX_AXIS_TITLE_LENGTH:
            errors.append(
                f"{index}件目の軸の名称は"
                f"{MAX_AXIS_TITLE_LENGTH}文字以内で"
                "入力してください。"
            )

        if (
            len(axis_description)
            > MAX_AXIS_DESCRIPTION_LENGTH
        ):
            errors.append(
                f"{index}件目の補足説明は"
                f"{MAX_AXIS_DESCRIPTION_LENGTH}文字以内で"
                "入力してください。"
            )

        duplicate_key = axis_title.casefold()

        if duplicate_key in normalized_titles:
            errors.append(
                f"「{axis_title}」は重複しています。"
            )
        else:
            normalized_titles.append(duplicate_key)

        validated_axes.append(
            JobHuntingAxis(
                axis_title=axis_title,
                axis_description=axis_description,
                priority_rank=index,
                source_type=axis.source_type,
            )
        )

    if errors:
        return None, errors

    return validated_axes, []


def save_job_hunting_axis_draft(
    draft_data: dict[str, object],
) -> None:
    """就活の軸の入力途中データを保存する。"""

    save_draft(
        user_id=get_current_user_id(),
        form_name=JOB_HUNTING_AXIS_FORM_NAME,
        draft_data=draft_data,
    )


def load_job_hunting_axis_draft(
) -> dict[str, object] | None:
    """就活の軸の入力途中データを取得する。"""

    return get_draft(
        user_id=get_current_user_id(),
        form_name=JOB_HUNTING_AXIS_FORM_NAME,
    )


def save_job_hunting_axis_data(
    axes: list[JobHuntingAxis],
) -> list[str]:
    """就活の軸を確認して正式保存する。"""

    validated_axes, errors = validate_job_hunting_axes(
        axes
    )

    if errors:
        return errors

    if validated_axes is None:
        return [
            "就活の軸の保存データを作成できませんでした。"
        ]

    user_id = get_current_user_id()

    saved_axes = get_job_hunting_axes(
        user_id
    )

    save_job_hunting_axes(
        user_id=user_id,
        axes=validated_axes,
        draft_form_name=JOB_HUNTING_AXIS_FORM_NAME,
    )

    if saved_axes != validated_axes:
        invalidate_current_user_job_evaluations(
            reason="就活の軸が変更されました。",
        )

    return []


def load_job_hunting_axis_data(
) -> list[JobHuntingAxis]:
    """正式保存済みの就活の軸を取得する。"""

    return get_job_hunting_axes(
        get_current_user_id()
    )


def move_axis_up(
    axes: list[JobHuntingAxis],
    target_index: int,
) -> list[JobHuntingAxis]:
    """指定された軸を1つ上へ移動する。"""

    if target_index <= 0:
        return axes

    if target_index >= len(axes):
        return axes

    reordered_axes = list(axes)

    reordered_axes[target_index - 1], reordered_axes[target_index] = (
        reordered_axes[target_index],
        reordered_axes[target_index - 1],
    )

    return _renumber_axes(reordered_axes)


def move_axis_down(
    axes: list[JobHuntingAxis],
    target_index: int,
) -> list[JobHuntingAxis]:
    """指定された軸を1つ下へ移動する。"""

    if target_index < 0:
        return axes

    if target_index >= len(axes) - 1:
        return axes

    reordered_axes = list(axes)

    reordered_axes[target_index], reordered_axes[target_index + 1] = (
        reordered_axes[target_index + 1],
        reordered_axes[target_index],
    )

    return _renumber_axes(reordered_axes)


def delete_axis(
    axes: list[JobHuntingAxis],
    target_index: int,
) -> list[JobHuntingAxis]:
    """指定された軸を一覧から削除する。"""

    if target_index < 0:
        return axes

    if target_index >= len(axes):
        return axes

    remaining_axes = [
        axis
        for index, axis in enumerate(axes)
        if index != target_index
    ]

    return _renumber_axes(remaining_axes)


def _renumber_axes(
    axes: list[JobHuntingAxis],
) -> list[JobHuntingAxis]:
    """一覧の上から順に優先順位を付け直す。"""

    return [
        JobHuntingAxis(
            axis_title=axis.axis_title,
            axis_description=axis.axis_description,
            priority_rank=index,
            source_type=axis.source_type,
        )
        for index, axis in enumerate(
            axes,
            start=1,
        )
    ]