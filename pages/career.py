"""職務経歴入力画面。"""

from dataclasses import replace

import streamlit as st

from pages.self_discovery_theme import apply_self_discovery_theme

from models import (
    Career,
    CareerHistory,
)

from services.career_service import (
    load_career_data,
    save_career_data,
    validate_careers,
)

from services.career_document_service import (
    extract_text_from_docx,
    parse_career_document,
)


PAGE_TITLE = "職務経歴"


# ==========================================
# Session State Keys
# ==========================================

CAREER_LOADED_KEY = "career_loaded"
CAREER_ITEMS_KEY = "career_items"

CAREER_ENTRY_MODE_KEY = "career_entry_mode"

CAREER_EDIT_INDEX_KEY = "career_edit_index"

CAREER_HISTORIES_KEY = "career_histories"
CAREER_HISTORY_EDIT_INDEX_KEY = (
    "career_history_edit_index"
)

CAREER_MESSAGE_KEY = "career_message"
CAREER_ERRORS_KEY = "career_errors"

CAREER_FORM_RESET_KEY = "career_form_reset"

CAREER_AI_ITEMS_KEY = "career_ai_items"
CAREER_AI_REVIEW_INDEX_KEY = (
    "career_ai_review_index"
)

CAREER_SCROLL_TO_FORM_KEY = (
    "career_scroll_to_form"
)

CAREER_COMPLETE_KEY = "career_complete"
CAREER_REVIEW_CONFIRMED_KEY = "career_review_confirmed"

# ==========================================
# 初期化
# ==========================================

def initialize_career_state() -> None:
    """職務経歴画面で使用する状態を初期化する。"""

    if st.session_state.get(
        CAREER_LOADED_KEY
    ):
        return

    career_items = load_career_data()

    st.session_state[
        CAREER_ITEMS_KEY
    ] = list(career_items)

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = []

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = None

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = None

    st.session_state[
        CAREER_LOADED_KEY
    ] = True


# ==========================================
# フォーム初期化
# ==========================================

def reset_current_history_form_state() -> None:
    """部署・役割の通常入力フォームを初期化する。"""

    st.session_state[
        "career_department"
    ] = ""

    st.session_state[
        "career_position"
    ] = ""

    st.session_state[
        "career_occupation"
    ] = ""

    st.session_state[
        "career_job_description"
    ] = ""

    st.session_state[
        "career_achievements"
    ] = ""

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = None


def reset_current_career_form_state() -> None:
    """現在編集中の会社フォームを初期化する。"""

    st.session_state[
        "career_company_name"
    ] = ""

    st.session_state[
        "career_employment_type"
    ] = "正社員"

    st.session_state[
        "career_industry"
    ] = ""

    st.session_state[
        "career_start_year"
    ] = 2020

    st.session_state[
        "career_start_month"
    ] = 4

    st.session_state[
        "career_is_current"
    ] = False

    st.session_state[
        "career_end_year"
    ] = 2025

    st.session_state[
        "career_end_month"
    ] = 10

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = []

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = None

    reset_current_history_form_state()


# ==========================================
# 通常入力 → CareerHistory
# ==========================================

def build_current_history(
    display_order: int,
) -> CareerHistory:
    """通常入力フォームを部署・役割データへ変換する。"""

    is_current = st.session_state.get(
        "career_is_current",
        False,
    )

    end_year = None
    end_month = None

    if not is_current:
        end_year = st.session_state.get(
            "career_end_year"
        )

        end_month = st.session_state.get(
            "career_end_month"
        )

    return CareerHistory(
        department=st.session_state.get(
            "career_department",
            "",
        ),
        position=st.session_state.get(
            "career_position",
            "",
        ),
        occupation=st.session_state.get(
            "career_occupation",
            "",
        ),
        start_year=st.session_state.get(
            "career_start_year",
            2020,
        ),
        start_month=st.session_state.get(
            "career_start_month",
            1,
        ),
        end_year=end_year,
        end_month=end_month,
        job_description=st.session_state.get(
            "career_job_description",
            "",
        ),
        achievements=st.session_state.get(
            "career_achievements",
            "",
        ),
        display_order=display_order,
    )


# ==========================================
# 現在の会社フォーム → Career
# ==========================================

def build_current_career_item(
    display_order: int,
) -> tuple[
    Career,
    list[CareerHistory],
]:
    """現在の入力内容を会社＋部署履歴へ変換する。"""

    is_current = st.session_state.get(
        "career_is_current",
        False,
    )

    end_year = None
    end_month = None

    if not is_current:
        end_year = st.session_state.get(
            "career_end_year"
        )

        end_month = st.session_state.get(
            "career_end_month"
        )

    career = Career(
        company_name=st.session_state.get(
            "career_company_name",
            "",
        ),
        employment_type=st.session_state.get(
            "career_employment_type",
            "",
        ),
        industry=st.session_state.get(
            "career_industry",
            "",
        ),
        start_year=st.session_state.get(
            "career_start_year",
            2020,
        ),
        start_month=st.session_state.get(
            "career_start_month",
            1,
        ),
        end_year=end_year,
        end_month=end_month,
        is_current=is_current,
        display_order=display_order,
    )

    histories = list(
        st.session_state.get(
            CAREER_HISTORIES_KEY,
            [],
        )
    )

    history_edit_index = (
        st.session_state.get(
            CAREER_HISTORY_EDIT_INDEX_KEY
        )
    )

    history_form_has_input = any(
        [
            st.session_state.get(
                "career_department",
                "",
            ),
            st.session_state.get(
                "career_position",
                "",
            ),
            st.session_state.get(
                "career_occupation",
                "",
            ),
            st.session_state.get(
                "career_job_description",
                "",
            ),
            st.session_state.get(
                "career_achievements",
                "",
            ),
        ]
    )

    # 通常入力モードでフォームに入力がある場合のみ
    # CAREER_HISTORIES_KEYへ反映する。
    if history_form_has_input:

        current_history = (
            build_current_history(
                display_order=(
                    history_edit_index + 1
                    if history_edit_index
                    not in (None, -1)
                    else len(histories) + 1
                ),
            )
        )

        if history_edit_index in (
            None,
            -1,
        ):
            histories.append(
                current_history
            )

        elif (
            0
            <= history_edit_index
            < len(histories)
        ):
            histories[
                history_edit_index
            ] = current_history

    ordered_histories = [
        replace(
            history,
            display_order=index,
        )
        for index, history in enumerate(
            histories,
            start=1,
        )
    ]

    return (
        career,
        ordered_histories,
    )


# ==========================================
# AI解析結果 → MeTeAデータ
# ==========================================

def convert_parsed_careers(
    parsed_careers,
) -> list[
    tuple[
        Career,
        list[CareerHistory],
    ]
]:
    """AI解析結果をMeTeAの職務経歴形式へ変換する。"""

    career_items = []

    for career_index, parsed_career in enumerate(
        parsed_careers,
        start=1,
    ):

        career = Career(
            company_name=(
                parsed_career.company_name
            ),
            employment_type=(
                parsed_career.employment_type
            ),
            industry=parsed_career.industry,
            start_year=parsed_career.start_year,
            start_month=(
                parsed_career.start_month
            ),
            end_year=parsed_career.end_year,
            end_month=parsed_career.end_month,
            is_current=parsed_career.is_current,
            display_order=career_index,
        )

        histories = []

        for (
            history_index,
            parsed_history,
        ) in enumerate(
            parsed_career.histories,
            start=1,
        ):

            history = CareerHistory(
                department=(
                    parsed_history.department
                ),
                position=(
                    parsed_history.position
                ),
                occupation=(
                    parsed_history.occupation
                ),
                start_year=(
                    parsed_history.start_year
                    if (
                        parsed_history.start_year
                        is not None
                    )
                    else parsed_career.start_year
                ),
                start_month=(
                    parsed_history.start_month
                    if (
                        parsed_history.start_month
                        is not None
                    )
                    else parsed_career.start_month
                ),
                end_year=(
                    parsed_history.end_year
                ),
                end_month=(
                    parsed_history.end_month
                ),
                job_description=(
                    parsed_history.job_description
                ),
                achievements=(
                    parsed_history.achievements
                ),
                display_order=history_index,
            )

            histories.append(
                history
            )

        career_items.append(
            (
                career,
                histories,
            )
        )

    return career_items


# ==========================================
# AI確認状態
# ==========================================

def is_ai_career_reviewing() -> bool:
    """現在AI取込データを確認中か判定する。"""

    ai_items = st.session_state.get(
        CAREER_AI_ITEMS_KEY,
        [],
    )

    review_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY
    )

    return (
        bool(ai_items)
        and review_index is not None
        and 0
        <= review_index
        < len(ai_items)
    )


# ==========================================
# 既存会社検索
# ==========================================

def find_existing_company_index(
    company_name: str,
) -> int | None:
    """同名の登録済み会社の位置を返す。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    target_name = company_name.strip()

    for index, (
        career,
        _,
    ) in enumerate(
        career_items
    ):
        if (
            career.company_name.strip()
            == target_name
        ):
            return index

    return None


# ==========================================
# AIフォーム用Widget状態
# ==========================================

def clear_ai_history_form_state() -> None:
    """AI確認フォーム用Widgetの状態を削除する。"""

    prefixes = (
        "career_ai_department_",
        "career_ai_position_",
        "career_ai_occupation_",
        "career_ai_job_description_",
        "career_ai_achievements_",
    )

    keys_to_delete = [
        key
        for key in list(
            st.session_state.keys()
        )
        if key.startswith(prefixes)
    ]

    for key in keys_to_delete:
        del st.session_state[key]


def apply_ai_history_form_values() -> None:
    """AIフォームで修正された内容を履歴へ反映する。"""

    review_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY,
        0,
    )

    histories = list(
        st.session_state.get(
            CAREER_HISTORIES_KEY,
            [],
        )
    )

    updated_histories = []

    for index, history in enumerate(
        histories,
        start=1,
    ):

        updated_history = replace(
            history,
            department=st.session_state.get(
                (
                    "career_ai_department_"
                    f"{review_index}_{index}"
                ),
                history.department,
            ),
            position=st.session_state.get(
                (
                    "career_ai_position_"
                    f"{review_index}_{index}"
                ),
                history.position,
            ),
            occupation=st.session_state.get(
                (
                    "career_ai_occupation_"
                    f"{review_index}_{index}"
                ),
                history.occupation,
            ),
            job_description=(
                st.session_state.get(
                    (
                        "career_ai_job_description_"
                        f"{review_index}_{index}"
                    ),
                    history.job_description,
                )
            ),
            achievements=st.session_state.get(
                (
                    "career_ai_achievements_"
                    f"{review_index}_{index}"
                ),
                history.achievements,
            ),
        )

        updated_histories.append(
            updated_history
        )

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = updated_histories

# ==========================================
# 部署・役割：追加・更新
# ==========================================

def add_current_history() -> None:
    """現在入力中の部署・役割を追加または更新する。"""

    st.session_state.pop(
        CAREER_ERRORS_KEY,
        None,
    )

    histories = list(
        st.session_state.get(
            CAREER_HISTORIES_KEY,
            [],
        )
    )

    edit_index = st.session_state.get(
        CAREER_HISTORY_EDIT_INDEX_KEY
    )

    current_history = build_current_history(
        display_order=(
            edit_index + 1
            if edit_index not in (None, -1)
            else len(histories) + 1
        ),
    )

    if not (
        current_history.occupation or ""
    ).strip():
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "職種を入力してください。"
        ]
        return

    if edit_index in (None, -1):
        histories.append(
            current_history
        )

        message = (
            "部署・役割を追加しました。"
            "続けて次の部署・役割を入力できます。"
        )

    elif (
        0 <= edit_index < len(histories)
    ):
        histories[
            edit_index
        ] = current_history

        message = (
            "部署・役割を更新しました。"
        )

    else:
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "編集対象の部署・役割が"
            "見つかりませんでした。"
        ]
        return

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = histories

    reset_current_history_form_state()

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = message


# ==========================================
# 部署・役割：編集読込
# ==========================================

def load_history_for_edit(
    target_index: int,
) -> None:
    """選択した部署・役割を通常フォームへ復元する。"""

    histories = st.session_state.get(
        CAREER_HISTORIES_KEY,
        [],
    )

    if not (
        0 <= target_index < len(histories)
    ):
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "編集対象の部署・役割が"
            "見つかりませんでした。"
        ]
        return

    history = histories[
        target_index
    ]

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = target_index

    st.session_state[
        "career_department"
    ] = history.department

    st.session_state[
        "career_position"
    ] = history.position

    st.session_state[
        "career_occupation"
    ] = history.occupation

    st.session_state[
        "career_job_description"
    ] = history.job_description

    st.session_state[
        "career_achievements"
    ] = history.achievements

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = (
        f"部署・役割 {target_index + 1} "
        "を編集中です。"
    )


# ==========================================
# 部署・役割：削除
# ==========================================

def delete_history(
    target_index: int,
) -> None:
    """指定した部署・役割を一覧から削除する。"""

    histories = list(
        st.session_state.get(
            CAREER_HISTORIES_KEY,
            [],
        )
    )

    if not (
        0 <= target_index < len(histories)
    ):
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "削除対象の部署・役割が"
            "見つかりませんでした。"
        ]
        return

    histories.pop(
        target_index
    )

    updated_histories = [
        replace(
            history,
            display_order=index,
        )
        for index, history in enumerate(
            histories,
            start=1,
        )
    ]

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = updated_histories

    reset_current_history_form_state()

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = (
        "部署・役割を削除しました。"
    )


# ==========================================
# 会社：編集読込
# ==========================================

def load_company_for_edit(
    target_index: int,
) -> None:
    """登録済み会社を編集フォームへ復元する。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    if not (
        0 <= target_index < len(career_items)
    ):
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "編集対象の会社が"
            "見つかりませんでした。"
        ]
        return

    career, histories = career_items[
        target_index
    ]

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = target_index

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = list(histories)

    st.session_state[
        "career_company_name"
    ] = career.company_name

    st.session_state[
        "career_employment_type"
    ] = career.employment_type

    st.session_state[
        "career_industry"
    ] = career.industry

    st.session_state[
        "career_start_year"
    ] = career.start_year

    st.session_state[
        "career_start_month"
    ] = career.start_month

    st.session_state[
        "career_is_current"
    ] = career.is_current

    st.session_state[
        "career_end_year"
    ] = (
        career.end_year
        if career.end_year is not None
        else 2025
    )

    st.session_state[
        "career_end_month"
    ] = (
        career.end_month
        if career.end_month is not None
        else 10
    )

    reset_current_history_form_state()

    st.session_state[
        CAREER_SCROLL_TO_FORM_KEY
    ] = True

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = (
        f"「{career.company_name}」"
        "を編集中です。"
    )


def cancel_company_edit() -> None:
    """会社編集を中止して新規入力状態へ戻す。"""

    reset_current_career_form_state()

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = (
        "編集をキャンセルしました。"
    )


# ==========================================
# AI取込：確認開始
# ==========================================

def apply_ai_careers_to_form() -> None:
    """AI解析結果を確認用データへ変換する。"""

    parsed_careers = st.session_state.get(
        "career_ai_parsed",
        [],
    )

    if not parsed_careers:
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "AI解析結果が"
            "見つかりませんでした。"
        ]
        return

    ai_items = convert_parsed_careers(
        parsed_careers
    )

    st.session_state[
        CAREER_AI_ITEMS_KEY
    ] = ai_items

    st.session_state[
        CAREER_AI_REVIEW_INDEX_KEY
    ] = 0

    st.session_state[
        CAREER_ENTRY_MODE_KEY
    ] = "manual"

    load_ai_career_for_review()


# ==========================================
# AI取込：現在会社をフォームへロード
# ==========================================

def load_ai_career_for_review() -> None:
    """現在確認対象のAI会社をフォームへ反映する。"""

    ai_items = st.session_state.get(
        CAREER_AI_ITEMS_KEY,
        [],
    )

    review_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY,
        0,
    )

    if not (
        ai_items
        and 0 <= review_index < len(ai_items)
    ):
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "確認対象の会社が"
            "見つかりませんでした。"
        ]
        return

    career, histories = ai_items[
        review_index
    ]

    clear_ai_history_form_state()

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = None

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = list(histories)

    st.session_state[
        "career_company_name"
    ] = career.company_name

    st.session_state[
        "career_employment_type"
    ] = career.employment_type

    st.session_state[
        "career_industry"
    ] = career.industry

    st.session_state[
        "career_start_year"
    ] = career.start_year

    st.session_state[
        "career_start_month"
    ] = career.start_month

    st.session_state[
        "career_is_current"
    ] = career.is_current

    st.session_state[
        "career_end_year"
    ] = (
        career.end_year
        if career.end_year is not None
        else 2025
    )

    st.session_state[
        "career_end_month"
    ] = (
        career.end_month
        if career.end_month is not None
        else 10
    )

    reset_current_history_form_state()

    st.session_state[
        CAREER_ENTRY_MODE_KEY
    ] = "manual"

    st.session_state[
        CAREER_SCROLL_TO_FORM_KEY
    ] = True

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = (
        f"AIが整理した"
        f"「{career.company_name}」を"
        "確認しています。"
        "内容を確認・修正してください。"
    )


# ==========================================
# AI取込：次の会社へ
# ==========================================

def move_to_next_ai_career(
    action_message: str,
) -> None:
    """次のAI取込会社へ進む。最後なら確認を終了する。"""

    ai_items = st.session_state.get(
        CAREER_AI_ITEMS_KEY,
        [],
    )

    current_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY,
        0,
    )

    next_index = (
        current_index + 1
    )

    if next_index < len(ai_items):

        st.session_state[
            CAREER_AI_REVIEW_INDEX_KEY
        ] = next_index

        load_ai_career_for_review()

        next_career, _ = ai_items[
            next_index
        ]

        st.session_state[
            CAREER_MESSAGE_KEY
        ] = (
            action_message
            + f" 続けて"
            f"「{next_career.company_name}」"
            "を確認してください。"
        )

        return

    st.session_state.pop(
        CAREER_AI_ITEMS_KEY,
        None,
    )

    st.session_state.pop(
        CAREER_AI_REVIEW_INDEX_KEY,
        None,
    )

    st.session_state.pop(
        "career_ai_parsed",
        None,
    )

    clear_ai_history_form_state()

    reset_current_career_form_state()

    st.session_state[
        CAREER_COMPLETE_KEY
    ] = True

    st.session_state[
        CAREER_REVIEW_CONFIRMED_KEY
    ] = False

    st.session_state[
        CAREER_SCROLL_TO_FORM_KEY
    ] = True


def skip_ai_career() -> None:
    """現在のAI取込会社を保存せず次へ進む。"""

    move_to_next_ai_career(
        "現在の会社は保存せず"
        "スキップしました。"
    )


# ==========================================
# 会社：保存
# ==========================================

def save_current_company() -> None:
    """現在の会社を保存する。"""

    ai_reviewing = (
        is_ai_career_reviewing()
    )

    if ai_reviewing:
        apply_ai_history_form_values()

    career_items = list(
        st.session_state.get(
            CAREER_ITEMS_KEY,
            [],
        )
    )

    edit_index = st.session_state.get(
        CAREER_EDIT_INDEX_KEY
    )

    company_name = st.session_state.get(
        "career_company_name",
        "",
    )

    existing_index = (
        find_existing_company_index(
            company_name
        )
    )

    # AI確認中に同名会社が存在する場合は
    # 既存会社を更新対象にする。
    if (
        ai_reviewing
        and existing_index is not None
    ):
        target_index = existing_index

    elif edit_index is not None:
        target_index = edit_index

    else:
        target_index = None

    current_item = (
        build_current_career_item(
            display_order=(
                target_index + 1
                if target_index is not None
                else len(career_items) + 1
            ),
        )
    )

    validation_errors = validate_careers(
        [current_item]
    )

    if validation_errors:
        st.session_state[
            CAREER_ERRORS_KEY
        ] = validation_errors
        return

    if target_index is None:
        career_items.append(
            current_item
        )

    else:
        career_items[
            target_index
        ] = current_item

    # 表示順を必ず1から振り直す
    career_items = [
        (
            replace(
                career,
                display_order=index,
            ),
            histories,
        )
        for index, (
            career,
            histories,
        ) in enumerate(
            career_items,
            start=1,
        )
    ]

    save_errors = save_career_data(
        career_items
    )

    if save_errors:
        st.session_state[
            CAREER_ERRORS_KEY
        ] = save_errors
        return

    st.session_state[
        CAREER_ITEMS_KEY
    ] = career_items

    if ai_reviewing:

        if existing_index is not None:
            message = (
                "既存の会社情報を"
                "更新しました。"
            )
        else:
            message = (
                "現在の会社を"
                "保存しました。"
            )

        move_to_next_ai_career(
            message
        )

        return

    reset_current_career_form_state()

    st.session_state[
        CAREER_COMPLETE_KEY
    ] = True

    st.session_state[
        CAREER_REVIEW_CONFIRMED_KEY
    ] = False

    st.session_state[
        CAREER_SCROLL_TO_FORM_KEY
    ] = True


# ==========================================
# 会社：削除
# ==========================================

def delete_company(
    target_index: int,
) -> None:
    """指定した会社を削除する。"""

    career_items = list(
        st.session_state.get(
            CAREER_ITEMS_KEY,
            [],
        )
    )

    if not (
        0 <= target_index < len(career_items)
    ):
        st.session_state[
            CAREER_ERRORS_KEY
        ] = [
            "削除対象の会社が"
            "見つかりませんでした。"
        ]
        return

    deleted_career, _ = (
        career_items.pop(
            target_index
        )
    )

    updated_items = [
        (
            replace(
                career,
                display_order=index,
            ),
            histories,
        )
        for index, (
            career,
            histories,
        ) in enumerate(
            career_items,
            start=1,
        )
    ]

    save_errors = save_career_data(
        updated_items
    )

    if save_errors:
        st.session_state[
            CAREER_ERRORS_KEY
        ] = save_errors
        return

    st.session_state[
        CAREER_ITEMS_KEY
    ] = updated_items

    reset_current_career_form_state()

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = (
        f"「{deleted_career.company_name}」"
        "を削除しました。"
    )

# ==========================================
# 通常：部署・役割入力フォーム
# ==========================================

def render_history_form() -> None:
    """部署・役割の入力フォームを表示する。"""

    detail_columns = st.columns(2)

    with detail_columns[0]:
        st.text_input(
            "部署名",
            placeholder="例：法務渉外グループ",
            key="career_department",
        )

    with detail_columns[1]:
        st.text_input(
            "役職",
            placeholder="例：リーダー",
            key="career_position",
        )

    st.text_input(
        "職種",
        placeholder="例：業務企画",
        key="career_occupation",
    )

    st.text_area(
        "業務内容",
        placeholder=(
            "例：法務関連業務の運用改善、"
            "関係部署との調整、"
            "手順書整備など"
        ),
        max_chars=1000,
        height=160,
        key="career_job_description",
    )

    st.text_area(
        "実績・成果",
        placeholder=(
            "例：業務の自動化により、"
            "年間約1,400万円相当の"
            "工数を削減"
        ),
        max_chars=1000,
        height=160,
        key="career_achievements",
    )


# ==========================================
# 通常：登録済み部署・役割一覧
# ==========================================

def render_history_list() -> None:
    """現在の会社の部署・役割一覧を表示する。"""

    histories = st.session_state.get(
        CAREER_HISTORIES_KEY,
        [],
    )

    if not histories:
        return

    st.markdown(
        "#### 登録済みの部署・役割"
    )

    for index, history in enumerate(
        histories,
        start=1,
    ):

        with st.container(
            border=True
        ):

            department_name = (
                history.department
                or "部署名未入力"
            )

            st.markdown(
                f"**{index}. "
                f"{department_name}**"
            )

            detail_parts = [
                value
                for value in (
                    history.position,
                    history.occupation,
                )
                if value
            ]

            if detail_parts:
                st.caption(
                    " / ".join(
                        detail_parts
                    )
                )

            if history.job_description:
                st.write(
                    history.job_description
                )

            if history.achievements:
                st.caption(
                    "実績・成果"
                )

                st.write(
                    history.achievements
                )

            button_left, button_right = (
                st.columns(2)
            )

            with button_left:
                st.button(
                    "編集",
                    key=(
                        "career_history_edit_"
                        f"{index}"
                    ),
                    use_container_width=True,
                    on_click=(
                        load_history_for_edit
                    ),
                    args=(index - 1,),
                )

            with button_right:
                st.button(
                    "削除",
                    key=(
                        "career_history_delete_"
                        f"{index}"
                    ),
                    use_container_width=True,
                    on_click=delete_history,
                    args=(index - 1,),
                )

            edit_index = (
                st.session_state.get(
                    CAREER_HISTORY_EDIT_INDEX_KEY
                )
            )

            if edit_index == index - 1:

                st.divider()

                st.caption(
                    "この部署・役割を"
                    "編集中です"
                )

                render_history_form()

                st.button(
                    "✓ 変更を反映する",
                    key=(
                        "career_update_history_"
                        f"{index}"
                    ),
                    use_container_width=True,
                    on_click=(
                        add_current_history
                    ),
                )


# ==========================================
# AI：全部署・役割確認フォーム
# ==========================================

def render_ai_history_forms() -> None:
    """AI解析した全部署・役割を展開表示する。"""

    review_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY,
        0,
    )

    histories = st.session_state.get(
        CAREER_HISTORIES_KEY,
        [],
    )

    if not histories:
        st.info(
            "AIが読み取った"
            "部署・役割はありません。"
        )
        return

    st.caption(
        "AIが読み取った内容を"
        "確認してください。"
        "すべての項目をこの画面で"
        "直接修正できます。"
    )

    for index, history in enumerate(
        histories,
        start=1,
    ):

        with st.container(
            border=True
        ):

            department_name = (
                history.department
                or "部署名未入力"
            )

            st.markdown(
                f"#### {index}. "
                f"{department_name}"
            )

            st.text_input(
                "部署名",
                value=history.department,
                key=(
                    "career_ai_department_"
                    f"{review_index}_{index}"
                ),
            )

            st.text_input(
                "役職",
                value=history.position,
                key=(
                    "career_ai_position_"
                    f"{review_index}_{index}"
                ),
            )

            st.text_input(
                "職種",
                value=history.occupation,
                key=(
                    "career_ai_occupation_"
                    f"{review_index}_{index}"
                ),
            )

            st.text_area(
                "業務内容",
                value=(
                    history.job_description
                ),
                max_chars=1000,
                height=160,
                key=(
                    "career_ai_job_description_"
                    f"{review_index}_{index}"
                ),
            )

            st.text_area(
                "実績・成果",
                value=history.achievements,
                max_chars=1000,
                height=160,
                key=(
                    "career_ai_achievements_"
                    f"{review_index}_{index}"
                ),
            )


# ==========================================
# 登録済み会社一覧
# ==========================================

def render_company_list() -> None:
    """登録済み会社一覧を表示する。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    header_left, header_right = (
        st.columns(
            [4, 1]
        )
    )

    with header_left:
        st.subheader(
            "登録済みの会社"
        )

    with header_right:
        if st.button(
            "＋会社を追加",
            key="career_add_company_top",
            use_container_width=True,
        ):
            reset_current_career_form_state()

            st.session_state[
                CAREER_COMPLETE_KEY
            ] = False

            st.session_state[
                CAREER_SCROLL_TO_FORM_KEY
            ] = True

            st.rerun()

    if not career_items:
        st.info(
            "まだ会社は"
            "登録されていません。"
        )
        return

    for index, (
        career,
        histories,
    ) in enumerate(
        career_items,
        start=1,
    ):

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {career.company_name}"
            )

            if career.is_current:
                period = (
                    f"{career.start_year}/"
                    f"{career.start_month}"
                    " ～ 現在"
                )

            else:
                period = (
                    f"{career.start_year}/"
                    f"{career.start_month}"
                    " ～ "
                    f"{career.end_year}/"
                    f"{career.end_month}"
                )

            st.caption(
                period
            )

            detail_parts = [
                value
                for value in (
                    career.employment_type,
                    career.industry,
                )
                if value
            ]

            if detail_parts:
                st.write(
                    " / ".join(
                        detail_parts
                    )
                )

            st.caption(
                "部署・役割："
                f"{len(histories)}件"
            )

            button_left, button_right = (
                st.columns(2)
            )

            with button_left:
                st.button(
                    "編集",
                    key=(
                        "career_edit_"
                        f"{index}"
                    ),
                    use_container_width=True,
                    on_click=(
                        load_company_for_edit
                    ),
                    args=(index - 1,),
                )

            with button_right:
                st.button(
                    "削除",
                    key=(
                        "career_delete_"
                        f"{index}"
                    ),
                    use_container_width=True,
                    on_click=delete_company,
                    args=(index - 1,),
                )

def render_career_review_summary() -> None:
    """保存済みの職務経歴を確定前の確認用に表示する。"""

    career_items = st.session_state.get(CAREER_ITEMS_KEY, [])
    history_count = sum(len(histories) for _, histories in career_items)

    summary_columns = st.columns(2)
    summary_columns[0].metric("登録企業", f"{len(career_items)}社")
    summary_columns[1].metric("部署・役割", f"{history_count}件")

    for career, histories in career_items:
        with st.container(border=True):
            st.markdown(f"### {career.company_name}")
            period_end = (
                "現在"
                if career.is_current
                else f"{career.end_year}/{career.end_month}"
            )
            st.caption(
                f"{career.start_year}/{career.start_month} ～ {period_end}"
            )
            details = [
                value
                for value in (career.employment_type, career.industry)
                if value
            ]
            if details:
                st.write(" / ".join(details))

            for history in histories:
                heading = " / ".join(
                    value
                    for value in (
                        history.department,
                        history.position,
                        history.occupation,
                    )
                    if value
                )
                if heading:
                    st.markdown(f"**{heading}**")
                if history.job_description:
                    st.write(history.job_description)
                if history.achievements:
                    st.caption(f"実績・成果：{history.achievements}")

# ==========================================
# 職務経歴画面
# ==========================================

def show_page() -> None:
    """職務経歴入力画面を表示する。"""

    apply_self_discovery_theme(current_step=5)

    initialize_career_state()

    if st.session_state.pop(
        CAREER_FORM_RESET_KEY,
        False,
    ):
        reset_current_career_form_state()

    if st.button(
        "← 就活の軸へ戻る",
        key="career_back_top",
    ):
        st.query_params["page"] = "job_hunting_axis"
        st.rerun()

    st.title("職務経歴・スキル")

    st.progress(
        1.0,
        text="自分を知る 5 / 5　職務経歴・スキル",
    )

    st.caption(
        "これまでの職務経歴を"
        "会社ごとに登録します。"
    )

    st.divider()

    # ======================================
    # 登録方法選択
    # ======================================

    entry_mode = st.session_state.get(
        CAREER_ENTRY_MODE_KEY
    )

    if entry_mode is None:

        st.subheader(
            "登録方法を選択"
        )

        st.caption(
            "既に職務経歴書をお持ちの方は"
            "アップロード、"
            "初めて作成する方は"
            "手入力がおすすめです。"
        )

        upload_col, manual_col = (
            st.columns(2)
        )

        # ----------------------------------
        # Word / PDF取込
        # ----------------------------------

        with upload_col:

            with st.container(
                border=True
            ):

                st.markdown(
                    "<div class='metea-method-illustration metea-method-illustration--upload' "
                    "aria-hidden='true'>▤</div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "### 職務経歴書から取り込む"
                )

                st.write(
                    "PDF・Wordの職務経歴書を"
                    "読み込み、"
                    "AIが内容を整理します。"
                )

                st.caption(
                    "対応形式："
                    "PDF / Word（.docx）"
                )

                uploaded_career_file = (
                    st.file_uploader(
                        "PDFまたはWordファイルを"
                        "選択してください",
                        type=[
                            "pdf",
                            "docx",
                        ],
                        key="career_upload",
                    )
                )

                if (
                    uploaded_career_file
                    is not None
                ):

                    file_name = (
                        uploaded_career_file
                        .name
                        .lower()
                    )

                    if file_name.endswith(
                        ".docx"
                    ):

                        extracted_text = (
                            extract_text_from_docx(
                                uploaded_career_file
                            )
                        )

                        st.info(
                            "Wordファイルを"
                            "読み取りました。"
                        )

                        if st.button(
                            "AIで職務経歴を整理する",
                            key="career_ai_parse",
                            use_container_width=True,
                        ):

                            with st.spinner(
                                "AIが職務経歴を"
                                "整理しています..."
                            ):

                                parsed_careers = (
                                    parse_career_document(
                                        extracted_text
                                    )
                                )

                            st.session_state[
                                "career_ai_parsed"
                            ] = parsed_careers

                        parsed_careers = (
                            st.session_state.get(
                                "career_ai_parsed",
                                [],
                            )
                        )

                        if parsed_careers:

                            st.info(
                                "AIによる整理が"
                                "完了しました。"
                            )

                            for career in (
                                parsed_careers
                            ):

                                with st.container(
                                    border=True
                                ):

                                    st.markdown(
                                        f"**"
                                        f"{career.company_name}"
                                        f"**"
                                    )

                                    if career.industry:
                                        st.write(
                                            "業種："
                                            f"{career.industry}"
                                        )

                                    st.write(
                                        "部署・役割："
                                        f"{len(career.histories)}件"
                                    )

                            st.button(
                                "この内容を"
                                "入力フォームに反映する",
                                key="career_ai_apply",
                                use_container_width=True,
                                on_click=(
                                    apply_ai_careers_to_form
                                ),
                            )

                    else:

                        st.info(
                            "PDFの読み取りは"
                            "次のステップで対応します。"
                        )

        # ----------------------------------
        # 手入力
        # ----------------------------------

        with manual_col:

            with st.container(
                border=True
            ):

                st.markdown(
                    "<div class='metea-method-illustration metea-method-illustration--manual' "
                    "aria-hidden='true'>✎</div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "### 手入力する"
                )

                st.write(
                    "会社・部署・役割ごとに"
                    "職務経歴を入力します。"
                )

                st.caption(
                    "初めて職務経歴書を"
                    "作る方向け"
                )

                if st.button(
                    "入力を始める",
                    key="career_manual",
                    use_container_width=True,
                ):

                    st.session_state[
                        CAREER_ENTRY_MODE_KEY
                    ] = "manual"

                    reset_current_career_form_state()

                    st.rerun()

        guidance_columns = st.columns(2)

        with guidance_columns[0]:
            st.markdown(
                """
                <div class="metea-career-guide">
                  <div class="metea-career-guide__icon">✓</div>
                  <div>
                    <strong>登録のポイント</strong>
                    <ul>
                      <li>会社ごとに登録できます</li>
                      <li>複数の部署・役割も整理できます</li>
                      <li>保存後も編集・追加・削除できます</li>
                    </ul>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with guidance_columns[1]:
            st.markdown(
                """
                <div class="metea-career-guide metea-career-guide--ai">
                  <div class="metea-career-guide__icon">✦</div>
                  <div>
                    <strong>AI取り込みについて</strong>
                    <p>AIが会社名・部署・役割・実績などを整理します。抽出後に内容を確認し、必要に応じて修正してから保存してください。</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.stop()

    if st.session_state.get(
        CAREER_COMPLETE_KEY,
        False,
    ):
        st.subheader("入力内容の確認")
        st.caption(
            "登録内容を確認してください。修正が必要な場合は入力画面へ戻れます。"
        )
        render_career_review_summary()

        review_columns = st.columns([1, 2])
        with review_columns[0]:
            if st.button(
                "入力を修正する",
                key="career_review_back",
                use_container_width=True,
            ):
                st.session_state[CAREER_COMPLETE_KEY] = False
                st.rerun()

        with review_columns[1]:
            if st.button(
                "この内容で完了する",
                key="career_review_confirm",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = True

        if st.session_state.get(CAREER_REVIEW_CONFIRMED_KEY, False):
            st.success("プロフィールの登録が完了しました。")
            job_column, top_column = st.columns(2)
            with job_column:
                if st.button(
                    "求人票を登録する",
                    key="career_complete_job",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state[CAREER_COMPLETE_KEY] = False
                    st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = False
                    st.query_params["page"] = "job_list"
                    st.rerun()
            with top_column:
                if st.button(
                    "トップへ戻る",
                    key="career_complete_top",
                    use_container_width=True,
                ):
                    st.session_state[CAREER_COMPLETE_KEY] = False
                    st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = False
                    st.query_params.clear()
                    st.rerun()
        st.stop()

    render_company_list()

    # ======================================
    # フォーム先頭へ移動
    # ======================================

    if st.session_state.pop(
        CAREER_SCROLL_TO_FORM_KEY,
        False,
    ):

        st.components.v1.html(
            """
            <script>
                const main =
                    window.parent.document
                    .querySelector(
                        '[data-testid="stMain"]'
                    );

                if (main) {
                    main.scrollTo({
                        top: 0,
                        behavior: "smooth"
                    });
                }
            </script>
            """,
            height=0,
        )

    # ======================================
    # 現在の状態
    # ======================================

    edit_index = st.session_state.get(
        CAREER_EDIT_INDEX_KEY
    )

    ai_reviewing = (
        is_ai_career_reviewing()
    )

    existing_ai_company_index = None

    if ai_reviewing:

        current_company_name = (
            st.session_state.get(
                "career_company_name",
                "",
            )
        )

        existing_ai_company_index = (
            find_existing_company_index(
                current_company_name
            )
        )

    # ======================================
    # 画面見出し
    # ======================================

    if ai_reviewing:

        ai_items = st.session_state.get(
            CAREER_AI_ITEMS_KEY,
            [],
        )

        review_index = (
            st.session_state.get(
                CAREER_AI_REVIEW_INDEX_KEY,
                0,
            )
        )

        st.subheader(
            "AI取込内容を確認"
        )

        st.caption(
            f"{review_index + 1} / "
            f"{len(ai_items)} 社目"
        )

        if (
            existing_ai_company_index
            is not None
        ):

            company_name = (
                st.session_state.get(
                    "career_company_name",
                    "",
                )
            )

            st.warning(
                f"⚠️「{company_name}」は"
                "すでに登録されています。\n\n"
                "内容を確認したうえで、"
                "既存情報を更新するか、"
                "今回の取込を"
                "スキップしてください。"
            )

        else:

            st.info(
                "AIが整理した内容です。"
                "保存前に内容を"
                "確認・修正してください。"
            )

    elif edit_index is None:

        st.subheader(
            "会社情報を追加"
        )

    else:

        career_items = (
            st.session_state.get(
                CAREER_ITEMS_KEY,
                [],
            )
        )

        editing_company_name = (
            career_items[
                edit_index
            ][0].company_name
            if (
                0
                <= edit_index
                < len(career_items)
            )
            else "選択した会社"
        )

        st.warning(
            f"✏️「{editing_company_name}」"
            "を編集中です。"
            "内容を修正した後、"
            "「変更を保存する」を"
            "押してください。"
        )

        st.subheader(
            "会社情報を編集："
            f"{editing_company_name}"
        )

    # ======================================
    # 会社情報
    # ======================================

    st.text_input(
        "会社名",
        key="career_company_name",
    )

    employment_types = [
        "正社員",
        "契約社員",
        "派遣社員",
        "アルバイト",
        "その他",
    ]

    st.selectbox(
        "雇用形態",
        employment_types,
        key="career_employment_type",
    )

    st.text_input(
        "業種",
        placeholder=(
            "例：金融・"
            "クレジットカード"
        ),
        key="career_industry",
    )

    start_columns = st.columns(2)

    with start_columns[0]:

        st.number_input(
            "入社年",
            min_value=1950,
            max_value=2100,
            key="career_start_year",
        )

    with start_columns[1]:

        st.number_input(
            "入社月",
            min_value=1,
            max_value=12,
            key="career_start_month",
        )

    is_current = st.checkbox(
        "現在も在職中",
        key="career_is_current",
    )

    if not is_current:

        end_columns = st.columns(2)

        with end_columns[0]:

            st.number_input(
                "退社年",
                min_value=1950,
                max_value=2100,
                key="career_end_year",
            )

        with end_columns[1]:

            st.number_input(
                "退社月",
                min_value=1,
                max_value=12,
                key="career_end_month",
            )

    # ======================================
    # 部署・役割
    # ======================================

    st.divider()

    st.subheader(
        "部署・役割"
    )

    if ai_reviewing:

        render_ai_history_forms()

    else:

        render_history_list()

        history_edit_index = (
            st.session_state.get(
                CAREER_HISTORY_EDIT_INDEX_KEY
            )
        )

        if history_edit_index is None:

            if st.button(
                "＋ 新しい部署・役割を追加",
                key="career_history_new",
                use_container_width=True,
            ):

                st.session_state[
                    CAREER_HISTORY_EDIT_INDEX_KEY
                ] = -1

                st.rerun()

        elif history_edit_index == -1:

            with st.container(
                border=True
            ):

                st.caption(
                    "新しい部署・役割を"
                    "入力してください"
                )

                render_history_form()

                st.button(
                    "＋ 部署・役割を追加する",
                    key=(
                        "career_add_history_new"
                    ),
                    use_container_width=True,
                    on_click=(
                        add_current_history
                    ),
                )

    # ======================================
    # エラー
    # ======================================

    career_errors = (
        st.session_state.pop(
            CAREER_ERRORS_KEY,
            [],
        )
    )

    for error in career_errors:
        st.error(
            error
        )

    # ======================================
    # メッセージ
    # ======================================

    st.divider()

    career_message = (
        st.session_state.pop(
            CAREER_MESSAGE_KEY,
            None,
        )
    )

    if career_message:
        st.success(
            career_message
        )

    # ======================================
    # 最終操作ボタン
    # ======================================

    if ai_reviewing:

        if (
            existing_ai_company_index
            is not None
        ):

            update_column, skip_column = (
                st.columns(2)
            )

            with update_column:

                st.button(
                    "既存情報を更新する",
                    key="career_ai_update",
                    type="primary",
                    use_container_width=True,
                    on_click=(
                        save_current_company
                    ),
                )

            with skip_column:

                st.button(
                    "この会社をスキップする",
                    key="career_ai_skip",
                    use_container_width=True,
                    on_click=(
                        skip_ai_career
                    ),
                )

        else:

            action_columns = st.columns(
                [1, 1, 1]
            )

            with action_columns[1]:

                st.button(
                    "保存して次へ",
                    key="career_ai_save",
                    type="primary",
                    use_container_width=True,
                    on_click=(
                        save_current_company
                    ),
                )

    elif edit_index is None:

        action_columns = st.columns(
            [1, 1, 1]
        )

        with action_columns[1]:

            st.button(
                "保存する",
                key="career_save",
                type="primary",
                use_container_width=True,
                on_click=(
                    save_current_company
                ),
            )

    else:

        cancel_column, save_column = (
            st.columns(2)
        )

        with cancel_column:

            st.button(
                "編集をキャンセル",
                key="career_edit_cancel",
                use_container_width=True,
                on_click=(
                    cancel_company_edit
                ),
            )

        with save_column:

            st.button(
                "変更を保存する",
                key="career_update",
                type="primary",
                use_container_width=True,
                on_click=(
                    save_current_company
                ),
            )