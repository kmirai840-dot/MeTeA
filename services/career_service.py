"""職務経歴の入力チェック・保存を担当する。"""

from models import (
    Career,
    CareerHistory,
)
from database.repositories.career_repository import (
    save_careers,
    get_careers,
)
from database.repositories.home_activity_repository import save_general_activity

from services.current_user_service import get_current_user_id
from services.job_matching_cache_service import (
    invalidate_current_user_job_evaluations,
)


def validate_careers(
    career_items: list[
        tuple[
            Career,
            list[CareerHistory],
        ]
    ],
) -> list[str]:
    """職務経歴の入力内容をチェックする。"""

    errors: list[str] = []

    if not career_items:
        errors.append(
            "職務経歴を1件以上入力してください。"
        )

    for career, histories in career_items:

        if not career.company_name.strip():
            errors.append(
                "会社名を入力してください。"
            )

        if not (career.industry or "").strip():
            errors.append(
                f"{career.company_name}：業種を入力してください。"
            )

        if not histories:
            errors.append(
                f"{career.company_name}の職歴を1件以上入力してください。"
            )

        if (
            career.start_year is not None
            and career.start_month is not None
            and
            career.end_year is not None
            and career.end_month is not None
            and (career.end_year, career.end_month)
            < (career.start_year, career.start_month)
        ):
            errors.append(
                f"{career.company_name}：退社年月は入社年月以降を指定してください。"
            )

        for history in histories:

            if not history.occupation.strip():
                errors.append(
                    f"{career.company_name}：職種を入力してください。"
                )

            if (
                history.start_year is not None
                and history.start_month is not None
                and
                history.end_year is not None
                and history.end_month is not None
                and (history.end_year, history.end_month)
                < (history.start_year, history.start_month)
            ):
                errors.append(
                    f"{career.company_name}：部署・役割の終了年月は開始年月以降を指定してください。"
                )

    return errors


def save_career_data(
    career_items: list[
        tuple[
            Career,
            list[CareerHistory],
        ]
    ],
) -> list[str]:
    """職務経歴を確認して保存する。"""

    errors = validate_careers(
        career_items
    )

    if errors:
        return errors

    user_id = get_current_user_id()

    saved_career_items = get_careers(
        user_id
    )

    save_careers(
        user_id=user_id,
        career_items=career_items,
    )

    if saved_career_items != career_items:
        save_general_activity(
            user_id,
            "career_updated",
            "職務経歴・スキルを更新しました",
            target_page="career",
            icon_name="user.svg",
        )
        invalidate_current_user_job_evaluations(
            reason="職務経歴・スキルが変更されました。",
        )

    return []


def load_career_data(
) -> list[
    tuple[
        Career,
        list[CareerHistory],
    ]
]:
    """正式保存済みの職務経歴を取得する。"""

    return get_careers(
        get_current_user_id()
    )
