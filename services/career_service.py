"""職務経歴の入力チェック・保存を担当する。"""

from models import (
    Career,
    CareerHistory,
)
from database.repositories.career_repository import (
    save_careers,
    get_careers,
)

from services.current_user_service import get_current_user_id


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

        if not histories:
            errors.append(
                f"{career.company_name}の職歴を1件以上入力してください。"
            )

        for history in histories:

            if not history.industry.strip():
                errors.append(
                    f"{career.company_name}：業種を入力してください。"
                )

            if not history.occupation.strip():
                errors.append(
                    f"{career.company_name}：職種を入力してください。"
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

    save_careers(
        user_id=get_current_user_id(),
        career_items=career_items,
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