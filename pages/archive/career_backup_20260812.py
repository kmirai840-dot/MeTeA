"""職務経歴入力画面。"""

from dataclasses import replace

import streamlit as st

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

CAREER_LOADED_KEY = "career_loaded"
CAREER_ITEMS_KEY = "career_items"
CAREER_FORM_RESET_KEY = "career_form_reset"
CAREER_MESSAGE_KEY = "career_message"
CAREER_ERRORS_KEY = "career_errors"
CAREER_ENTRY_MODE_KEY = "career_entry_mode"
CAREER_EDIT_INDEX_KEY = "career_edit_index"
CAREER_HISTORIES_KEY = "career_histories"
CAREER_HISTORY_EDIT_INDEX_KEY = "career_history_edit_index"
CAREER_AI_ITEMS_KEY = "career_ai_items"
CAREER_AI_REVIEW_INDEX_KEY = "career_ai_review_index"
CAREER_SCROLL_TO_FORM_KEY = "career_scroll_to_form"


def initialize_career_state() -> None:
    """保存済みの職務経歴を画面と一覧へ復元する。"""

    if st.session_state.get(CAREER_LOADED_KEY):
        return

    career_items = load_career_data()

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = []

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = None

    # 複数社分を、そのまま画面内の一覧として保持する
    st.session_state[CAREER_ITEMS_KEY] = list(
        career_items
    )

    # 現在の入力フォームには、先頭の1社を表示する
    if career_items:
        career, histories = career_items[0]

        st.session_state["career_company_name"] = (
            career.company_name
        )
        st.session_state["career_employment_type"] = (
            career.employment_type
        )
        st.session_state["career_start_year"] = (
            career.start_year
        )
        st.session_state["career_start_month"] = (
            career.start_month
        )
        st.session_state["career_is_current"] = (
            career.is_current
        )

        if career.end_year is not None:
            st.session_state["career_end_year"] = (
                career.end_year
            )

        if career.end_month is not None:
            st.session_state["career_end_month"] = (
                career.end_month
            )

        if histories:
            st.session_state[
                CAREER_HISTORIES_KEY
            ] = list(histories)

            st.session_state[
                CAREER_HISTORY_EDIT_INDEX_KEY
            ] = 0

            history = histories[0]

            st.session_state["career_department"] = (
                history.department
            )
            st.session_state["career_position"] = (
                history.position
            )

            st.session_state["career_occupation"] = (
                history.occupation
            )
            st.session_state["career_job_description"] = (
                history.job_description
            )
            st.session_state["career_achievements"] = (
                history.achievements
            )

    st.session_state[CAREER_LOADED_KEY] = True



def reset_current_career_form_state() -> None:
    """次の会社を入力するため、現在のフォーム内容を初期化する。"""

    st.session_state["career_company_name"] = ""
    st.session_state["career_employment_type"] = "正社員"

    st.session_state["career_start_year"] = 2020
    st.session_state["career_start_month"] = 4

    st.session_state["career_is_current"] = False

    st.session_state["career_end_year"] = 2025
    st.session_state["career_end_month"] = 10

    st.session_state["career_department"] = ""
    st.session_state["career_position"] = ""
    st.session_state["career_industry"] = ""
    st.session_state["career_occupation"] = ""

    st.session_state["career_job_description"] = ""
    st.session_state["career_achievements"] = ""

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = []

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = None


def reset_current_history_form_state() -> None:
    """次の部署・役割を入力するため、関連項目だけ初期化する。"""

    st.session_state["career_department"] = ""
    st.session_state["career_position"] = ""
    st.session_state["career_occupation"] = ""

    st.session_state[
        "career_job_description"
    ] = ""

    st.session_state["career_achievements"] = ""

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = None


def build_current_history(
    display_order: int,
) -> CareerHistory:
    """現在の入力フォームを1件の部署・役割へ変換する。"""

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


def build_current_career_item(
    display_order: int,
) -> tuple[
    Career,
    list[CareerHistory],
]:
    """現在の入力内容を1社分の職務経歴へ変換する。"""

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

    history_edit_index = st.session_state.get(
        CAREER_HISTORY_EDIT_INDEX_KEY
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

    if history_form_has_input:
        current_history = build_current_history(
            display_order=(
                history_edit_index + 1
                if history_edit_index not in (None, -1)
                else len(histories) + 1
            ),
        )

        if history_edit_index in (None, -1):
            histories.append(
                current_history
            )

        elif (
            0
            <= history_edit_index
            < len(histories)
        ):
            histories[history_edit_index] = (
                current_history
            )

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
            if edit_index is not None
            else len(histories) + 1
        ),
    )

    if not (
        current_history.occupation or ""
    ).strip():
        st.session_state[CAREER_ERRORS_KEY] = [
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
        histories[edit_index] = (
            current_history
        )

        message = (
            "部署・役割を更新しました。"
        )

    else:
        st.session_state[CAREER_ERRORS_KEY] = [
            "編集対象の部署・役割が見つかりませんでした。"
        ]
        return

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = histories

    reset_current_history_form_state()

    st.session_state[CAREER_MESSAGE_KEY] = (
        message
    )


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
            company_name=parsed_career.company_name,
            employment_type=parsed_career.employment_type,
            industry=parsed_career.industry,
            start_year=parsed_career.start_year,
            start_month=parsed_career.start_month,
            end_year=parsed_career.end_year,
            end_month=parsed_career.end_month,
            is_current=parsed_career.is_current,
            display_order=career_index,
        )

        histories = []

        for history_index, parsed_history in enumerate(
            parsed_career.histories,
            start=1,
        ):
            history = CareerHistory(
                department=parsed_history.department,
                position=parsed_history.position,
                occupation=parsed_history.occupation,
                start_year=(
                    parsed_history.start_year
                    if parsed_history.start_year is not None
                    else parsed_career.start_year
                ),
                start_month=(
                    parsed_history.start_month
                    if parsed_history.start_month is not None
                    else parsed_career.start_month
                ),
                end_year=parsed_history.end_year,
                end_month=parsed_history.end_month,
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


def add_current_company() -> None:
    """現在入力中の会社を一覧へ追加する。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    new_item = build_current_career_item(
        display_order=len(career_items) + 1,
    )

    validation_errors = validate_careers(
        [new_item]
    )

    if validation_errors:
        st.session_state[CAREER_ERRORS_KEY] = (
            validation_errors
        )
        return

    st.session_state[CAREER_ITEMS_KEY] = [
        *career_items,
        new_item,
    ]

    reset_current_career_form_state()

    st.session_state[CAREER_MESSAGE_KEY] = (
        "1社分を追加しました。"
        "続けて次の会社を入力してください。"
    )


def is_ai_career_reviewing() -> bool:
    """AI取込した職務経歴を確認中か判定する。"""

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
        and 0 <= review_index < len(ai_items)
    )


def save_current_company() -> None:
    """現在の入力内容を一覧とDBへ保存する。"""

    if is_ai_career_reviewing():
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

    current_item = build_current_career_item(
        display_order=(
            edit_index + 1
            if edit_index is not None
            else len(career_items) + 1
        ),
    )

    validation_errors = validate_careers(
        [current_item]
    )

    if validation_errors:
        st.session_state[CAREER_ERRORS_KEY] = (
            validation_errors
        )
        return

    if edit_index is None:
        career_items.append(
            current_item
        )
    else:
        career_items[edit_index] = (
            current_item
        )

    save_errors = save_career_data(
        career_items
    )

    if save_errors:
        st.session_state[CAREER_ERRORS_KEY] = (
            save_errors
        )
        return

    st.session_state[CAREER_ITEMS_KEY] = (
        career_items
    )

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = None

    if is_ai_career_reviewing():
        ai_items = st.session_state.get(
            CAREER_AI_ITEMS_KEY,
            [],
        )

        current_review_index = (
            st.session_state.get(
                CAREER_AI_REVIEW_INDEX_KEY,
                0,
            )
        )

        next_review_index = (
            current_review_index + 1
        )

        if next_review_index < len(ai_items):
            st.session_state[
                CAREER_AI_REVIEW_INDEX_KEY
            ] = next_review_index

            st.session_state[
                CAREER_SCROLL_TO_FORM_KEY
            ] = True

            load_ai_career_for_review()

            next_career, _ = ai_items[
                next_review_index
            ]

            st.session_state[
                CAREER_MESSAGE_KEY
            ] = (
                "現在の会社を保存しました。"
                f"続けて「{next_career.company_name}」"
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

        st.session_state[
            CAREER_FORM_RESET_KEY
        ] = True

        st.session_state[
            CAREER_MESSAGE_KEY
        ] = (
            "AIで取り込んだ職務経歴を"
            "すべて保存しました。"
        )

        return

    st.session_state[
        CAREER_FORM_RESET_KEY
    ] = True

    st.session_state[CAREER_MESSAGE_KEY] = (
        "職務経歴を保存しました。"
        "続けて別の会社を登録できます。"
    )


def delete_company(
    target_index: int,
) -> None:
    """指定した会社を一覧とDBから削除する。"""

    career_items = list(
        st.session_state.get(
            CAREER_ITEMS_KEY,
            [],
        )
    )

    if not (
        0 <= target_index < len(career_items)
    ):
        st.session_state[CAREER_ERRORS_KEY] = [
            "削除対象の会社が見つかりませんでした。"
        ]
        return

    deleted_career, _ = career_items.pop(
        target_index
    )

    # 削除後の会社表示順を1から振り直す
    updated_items = [
        (
            replace(
                career,
                display_order=display_order,
            ),
            histories,
        )
        for display_order, (
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
        st.session_state[CAREER_ERRORS_KEY] = (
            save_errors
        )
        return

    st.session_state[CAREER_ITEMS_KEY] = (
        updated_items
    )

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = None

    st.session_state[
        CAREER_FORM_RESET_KEY
    ] = True

    st.session_state[CAREER_MESSAGE_KEY] = (
        f"「{deleted_career.company_name}」"
        "を削除しました。"
    )


def apply_ai_careers_to_form() -> None:
    """AI解析結果を確認用データへ変換してフォームへ反映する。"""

    parsed_careers = st.session_state.get(
        "career_ai_parsed",
        [],
    )

    if not parsed_careers:
        st.session_state[CAREER_ERRORS_KEY] = [
            "AI解析結果が見つかりませんでした。"
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

    load_ai_career_for_review()


def load_ai_career_for_review() -> None:
    """AI解析した1社目を確認用フォームへ反映する。"""

    ai_items = st.session_state.get(
        CAREER_AI_ITEMS_KEY,
        [],
    )

    if not ai_items:
        st.session_state[CAREER_ERRORS_KEY] = [
            "AI解析した職務経歴が見つかりませんでした。"
        ]
        return

    review_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY,
        0,
    )

    if not (
        0 <= review_index < len(ai_items)
    ):
        st.session_state[CAREER_ERRORS_KEY] = [
            "確認対象の会社が見つかりませんでした。"
        ]
        return

    career, histories = ai_items[
        review_index
    ]

    st.session_state[
        CAREER_FORM_RESET_KEY
    ] = False

    clear_ai_history_form_state()

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = None

    print(
        "AI確認中:",
        is_ai_career_reviewing(),
    )

    print(
        "AI確認index:",
        st.session_state.get(
            CAREER_AI_REVIEW_INDEX_KEY
        ),
    )

    print(
        "AI会社数:",
        len(
            st.session_state.get(
                CAREER_AI_ITEMS_KEY,
                [],
            )
        ),
    )

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = list(histories)

    st.session_state["career_company_name"] = (
        career.company_name
    )
    st.session_state["career_employment_type"] = (
        career.employment_type
    )
    st.session_state["career_industry"] = (
        career.industry
    )
    st.session_state["career_start_year"] = (
        career.start_year
    )
    st.session_state["career_start_month"] = (
        career.start_month
    )
    st.session_state["career_is_current"] = (
        career.is_current
    )

    st.session_state["career_end_year"] = (
        career.end_year
        if career.end_year is not None
        else 2025
    )

    st.session_state["career_end_month"] = (
        career.end_month
        if career.end_month is not None
        else 10
    )

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = None

    reset_current_history_form_state()

    st.session_state[
        CAREER_ENTRY_MODE_KEY
    ] = "manual"


def load_company_for_edit(
    target_index: int,
) -> None:
    """選択した会社の内容を入力フォームへ復元する。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    if not (
        0 <= target_index < len(career_items)
    ):
        st.session_state[CAREER_ERRORS_KEY] = [
            "編集対象の会社が見つかりませんでした。"
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

    st.session_state["career_company_name"] = (
        career.company_name
    )
    st.session_state["career_employment_type"] = (
        career.employment_type
    )
    st.session_state["career_industry"] = (
        career.industry
    )
    st.session_state["career_industry"] = (
        career.industry
    )
    st.session_state["career_start_year"] = (
        career.start_year
    )
    st.session_state["career_start_month"] = (
        career.start_month
    )

    st.session_state["career_is_current"] = (
        career.is_current
    )

    st.session_state["career_end_year"] = (
        career.end_year
        if career.end_year is not None
        else 2025
    )

    st.session_state["career_end_month"] = (
        career.end_month
        if career.end_month is not None
        else 10
    )

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = 0

    if histories:
        history = histories[0]

        st.session_state["career_department"] = (
            history.department
        )
        st.session_state["career_position"] = (
            history.position
        )

        st.session_state["career_occupation"] = (
            history.occupation
        )
        st.session_state[
            "career_job_description"
        ] = history.job_description
        st.session_state["career_achievements"] = (
            history.achievements
        )

    else:
        st.session_state["career_department"] = ""
        st.session_state["career_position"] = ""
        st.session_state["career_occupation"] = ""
        st.session_state[
            "career_job_description"
        ] = ""
        st.session_state["career_achievements"] = ""

    st.session_state[CAREER_MESSAGE_KEY] = (
        f"「{career.company_name}」を編集中です。"
    )


def cancel_company_edit() -> None:
    """会社情報の編集を中止して、新規入力状態へ戻す。"""

    st.session_state[
        CAREER_EDIT_INDEX_KEY
    ] = None

    reset_current_career_form_state()

    st.session_state[CAREER_MESSAGE_KEY] = (
        "編集をキャンセルしました。"
    )


def load_history_for_edit(
    target_index: int,
) -> None:
    """選択した部署・役割を入力フォームへ復元する。"""

    histories = st.session_state.get(
        CAREER_HISTORIES_KEY,
        [],
    )

    if not (
        0 <= target_index < len(histories)
    ):
        st.session_state[CAREER_ERRORS_KEY] = [
            "編集対象の部署・役割が見つかりませんでした。"
        ]
        return

    history = histories[target_index]

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = target_index

    st.session_state["career_department"] = (
        history.department
    )
    st.session_state["career_position"] = (
        history.position
    )
    st.session_state["career_occupation"] = (
        history.occupation
    )
    st.session_state[
        "career_job_description"
    ] = history.job_description
    st.session_state["career_achievements"] = (
        history.achievements
    )

    st.session_state[CAREER_MESSAGE_KEY] = (
        f"部署・役割 {target_index + 1} を編集中です。"
    )


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
        st.session_state[CAREER_ERRORS_KEY] = [
            "削除対象の部署・役割が見つかりませんでした。"
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

    st.session_state[
        CAREER_HISTORY_EDIT_INDEX_KEY
    ] = None

    reset_current_history_form_state()

    st.session_state[CAREER_MESSAGE_KEY] = (
        "部署・役割を削除しました。"
    )


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
            "関係部署との調整、手順書整備など"
        ),
        max_chars=1000,
        height=160,
        key="career_job_description",
    )

    st.text_area(
        "実績・成果",
        placeholder=(
            "例：業務の自動化により、"
            "年間約1,400万円相当の工数を削減"
        ),
        max_chars=1000,
        height=160,
        key="career_achievements",
    )


def render_ai_history_forms() -> None:
    """AI解析した全部署・役割を確認用に表示する。"""

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
            "AIが読み取った部署・役割はありません。"
        )
        return

    st.caption(
        "AIが読み取った内容を確認してください。"
        "必要な箇所は修正できます。"
    )

    for index, history in enumerate(
        histories,
        start=1,
    ):
        with st.container(border=True):
            department_name = (
                history.department
                or "部署名未入力"
            )

            st.markdown(
                f"#### {index}. {department_name}"
            )

            st.text_input(
                "部署名",
                value=history.department,
                key=f"career_ai_department_{review_index}_{index}",
            )

            st.text_input(
                "役職",
                value=history.position,
                key=f"career_ai_position_{review_index}_{index}",
            )

            st.text_input(
                "職種",
                value=history.occupation,
                key=f"career_ai_occupation_{review_index}_{index}",
            )

            st.text_area(
                "業務内容",
                value=history.job_description,
                height=160,
                key=f"career_ai_job_description_{review_index}_{index}",
            )

            st.text_area(
                "実績・成果",
                value=history.achievements,
                height=160,
                key=f"career_ai_achievements_{review_index}_{index}",
            )


def clear_ai_history_form_state() -> None:
    """AI確認フォームに残っている部署・役割の入力状態を削除する。"""

    prefixes = (
        "career_ai_department_",
        "career_ai_position_",
        "career_ai_occupation_",
        "career_ai_job_description_",
        "career_ai_achievements_",
    )

    keys_to_delete = [
        key
        for key in st.session_state.keys()
        if key.startswith(prefixes)
    ]

    for key in keys_to_delete:
        del st.session_state[key]


def apply_ai_history_form_values() -> None:
    """AI確認フォームの修正内容を履歴データへ反映する。"""

    review_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY,
        0,
    )

    histories = st.session_state.get(
        CAREER_HISTORIES_KEY,
        [],
    )

    updated_histories = []

    for index, history in enumerate(
        histories,
        start=1,
    ):
        updated_history = replace(
            history,
            department=st.session_state.get(
                f"career_ai_department_{review_index}_{index}",
                history.department,
            ),
            position=st.session_state.get(
                f"career_ai_position_{review_index}_{index}",
                history.position,
            ),
            occupation=st.session_state.get(
                f"career_ai_occupation_{review_index}_{index}",
                history.occupation,
            ),
            job_description=st.session_state.get(
                f"career_ai_job_description_{review_index}_{index}",
                history.job_description,
            ),
            achievements=st.session_state.get(
                f"career_ai_achievements_{review_index}_{index}",
                history.achievements,
            ),
        )

        updated_histories.append(
            updated_history
        )

    st.session_state[
        CAREER_HISTORIES_KEY
    ] = updated_histories


def render_history_list() -> None:
    """現在の会社に登録した部署・役割一覧を表示する。"""

    histories = st.session_state.get(
        CAREER_HISTORIES_KEY,
        [],
    )

    if not histories:
        return

    st.markdown("#### 登録済みの部署・役割")

    for index, history in enumerate(
        histories,
        start=1,
    ):
        with st.container(border=True):

            department_name = (
                history.department
                or "部署名未入力"
            )

            st.markdown(
                f"**{index}. {department_name}**"
            )

            detail_parts = [
                value
                for value in [
                    history.position,
                    history.occupation,
                ]
                if value
            ]

            if detail_parts:
                st.caption(
                    " / ".join(detail_parts)
                )

            if history.job_description:
                st.write(
                    history.job_description
                )

            button_left, button_right = st.columns(2)

            with button_left:
                st.button(
                    "✏ 編集",
                    key=f"career_history_edit_{index}",
                    use_container_width=True,
                    on_click=load_history_for_edit,
                    args=(index - 1,),
                )

            with button_right:
                st.button(
                    "🗑 削除",
                    key=f"career_history_delete_{index}",
                    use_container_width=True,
                    on_click=delete_history,
                    args=(index - 1,),
                )

            if (
                st.session_state.get(
                    CAREER_HISTORY_EDIT_INDEX_KEY
                )
                == index - 1
            ):
                st.divider()
                st.caption("この部署・役割を編集中です")
                render_history_form()

                st.button(
                    "✓ 変更を反映する",
                    key=f"career_update_history_{index}",
                    use_container_width=True,
                    on_click=add_current_history,
                )

def render_company_list() -> None:
    """登録済み会社一覧を表示する。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    header_left, header_right = st.columns(
        [4, 1]
    )

    with header_left:
        st.subheader("登録済みの会社")

    with header_right:
        if st.button(
            "＋会社を追加",
            key="career_add_company_top",
            use_container_width=True,
        ):
            st.session_state[
                CAREER_EDIT_INDEX_KEY
            ] = None

            reset_current_career_form_state()
            st.rerun()

    if not career_items:
        st.info(
            "まだ会社は登録されていません。"
        )
        return

    for index, (
        career,
        _,
    ) in enumerate(
        career_items,
        start=1,
    ):
        with st.container(
            border=True,
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

            st.caption(period)
            st.write(career.employment_type)

            button_left, button_right = (
                st.columns(2)
            )

            with button_left:
                st.button(
                    "✏ 編集",
                    key=f"career_edit_{index}",
                    use_container_width=True,
                    on_click=load_company_for_edit,
                    args=(index - 1,),
                )

            with button_right:
                st.button(
                    "🗑 削除",
                    key=f"career_delete_{index}",
                    use_container_width=True,
                    on_click=delete_company,
                    args=(index - 1,),
                )


def show_page() -> None:
    """職務経歴入力画面を表示する。"""

    initialize_career_state()

    if st.session_state.pop(
        CAREER_FORM_RESET_KEY,
        False,
    ):
        reset_current_career_form_state()

    st.title("💼 職務経歴")

    st.caption(
        "これまでの職務経歴を会社ごとに登録します。"
    )

    st.divider()

    entry_mode = st.session_state.get(
        "career_entry_mode"
    )

    if entry_mode is None:

        st.subheader("登録方法を選択")

        st.caption(
            "既に職務経歴書をお持ちの方はアップロード、"
            "初めて作成する方は手入力がおすすめです。"
        )

        upload_col, manual_col = st.columns(2)

        with upload_col:
            with st.container(border=True):
                st.markdown("## 📄")

                st.markdown(
                    "### 職務経歴書から取り込む"
                )

                st.write(
                    "PDF・Wordの職務経歴書を読み込み、"
                    "AIが内容を整理します。"
                )

                st.caption(
                    "対応形式：PDF / Word（.docx）"
                )

                uploaded_career_file = st.file_uploader(
                    "PDFまたはWordファイルを選択してください",
                    type=["pdf", "docx"],
                    key="career_upload",
                )

                if uploaded_career_file is not None:

                    if uploaded_career_file.name.lower().endswith(
                        ".docx"
                    ):
                        extracted_text = (
                            extract_text_from_docx(
                                uploaded_career_file
                            )
                        )

                        st.success(
                            "Wordファイルを読み取りました。"
                        )

                        if st.button(
                            "AIで職務経歴を整理する",
                            key="career_ai_parse",
                            use_container_width=True,
                        ):
                            with st.spinner(
                                "AIが職務経歴を整理しています..."
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
                            st.success(
                                "AIによる整理が完了しました。"
                            )

                            for career in parsed_careers:
                                with st.container(
                                    border=True
                                ):
                                    st.markdown(
                                        f"**{career.company_name}**"
                                    )

                                    st.write(
                                        f"業種：{career.industry}"
                                    )

                                    st.write(
                                        "部署・役割："
                                        f"{len(career.histories)}件"
                                    )

                            st.button(
                                "この内容を入力フォームに反映する",
                                key="career_ai_apply",
                                use_container_width=True,
                                on_click=apply_ai_careers_to_form,
                            )
                    else:
                        st.info(
                            "PDFの読み取りは次のステップで対応します。"
                        )

        with manual_col:
            with st.container(border=True):
                st.markdown("## ✍")

                st.markdown(
                    "### 手入力する"
                )

                st.write(
                    "会社・部署・役割ごとに"
                    "職務経歴を入力します。"
                )

                st.caption(
                    "初めて職務経歴書を作る方向け"
                )

                if st.button(
                    "入力を始める",
                    key="career_manual",
                    use_container_width=True,
                ):
                    st.session_state[
                        CAREER_ENTRY_MODE_KEY
                    ] = "manual"

                    st.rerun()

        st.stop()

    render_company_list()

    if st.session_state.pop(
        CAREER_SCROLL_TO_FORM_KEY,
        False,
    ):
        st.components.v1.html(
            """
            <script>
                window.parent.document
                    .querySelector(
                        '[data-testid="stMain"]'
                    )
                    .scrollTo({
                        top: 0,
                        behavior: "smooth"
                    });
            </script>
            """,
            height=0,
        )

    edit_index = st.session_state.get(
        CAREER_EDIT_INDEX_KEY
    )

    existing_ai_company_index = None

    if is_ai_career_reviewing():
        current_company_name = st.session_state.get(
            "career_company_name",
            "",
        )

        existing_ai_company_index = (
            find_existing_company_index(
                current_company_name
            )
        )

    if existing_ai_company_index is not None:
        st.warning(
            "⚠️ この会社はすでに登録されています。"
            "重複して新規登録せず、"
            "既存情報を更新するか、"
            "今回の取込をスキップしてください。"
        )

    if edit_index is None:
        st.subheader("会社情報を追加")

    else:
        career_items = st.session_state.get(
            CAREER_ITEMS_KEY,
            [],
        )

        editing_company_name = (
            career_items[edit_index][0].company_name
            if 0 <= edit_index < len(career_items)
            else "選択した会社"
        )

        st.warning(
            f"✏️ 「{editing_company_name}」を編集中です。"
            "内容を修正した後、"
            "「変更を保存する」を押してください。"
        )

        st.subheader(
            f"会社情報を編集：{editing_company_name}"
        )

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
        placeholder="例：金融・クレジットカード",
         key="career_industry",
    )

    year_columns = st.columns(2)

    with year_columns[0]:
        st.number_input(
            "入社年",
            min_value=1950,
            max_value=2100,
            value=2020,
            key="career_start_year",
        )

    with year_columns[1]:
        st.number_input(
            "入社月",
            min_value=1,
            max_value=12,
            value=4,
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
                value=2025,
                key="career_end_year",
            )

        with end_columns[1]:
            st.number_input(
                "退社月",
                min_value=1,
                max_value=12,
                value=10,
                key="career_end_month",
            )


    st.divider()

    st.subheader("部署・役割")


def find_existing_company_index(
    company_name: str,
) -> int | None:
    """同名の登録済み会社があれば、その位置を返す。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    target_name = company_name.strip()

    for index, (
        career,
        _,
    ) in enumerate(career_items):
        if career.company_name.strip() == target_name:
            return index

    return None


def skip_ai_career() -> None:
    """現在確認中のAI取込会社を保存せず、次の会社へ進む。"""

    ai_items = st.session_state.get(
        CAREER_AI_ITEMS_KEY,
        [],
    )

    current_review_index = st.session_state.get(
        CAREER_AI_REVIEW_INDEX_KEY,
        0,
    )

    next_review_index = (
        current_review_index + 1
    )

    if next_review_index < len(ai_items):
        st.session_state[
            CAREER_AI_REVIEW_INDEX_KEY
        ] = next_review_index

        st.session_state[
            CAREER_SCROLL_TO_FORM_KEY
        ] = True

        load_ai_career_for_review()

        next_career, _ = ai_items[
            next_review_index
        ]

        st.session_state[
            CAREER_MESSAGE_KEY
        ] = (
            "現在の会社は保存せずスキップしました。"
            f"続けて「{next_career.company_name}」"
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

    st.session_state[
        CAREER_FORM_RESET_KEY
    ] = True

    st.session_state[
        CAREER_MESSAGE_KEY
    ] = (
        "現在の会社は保存せずスキップしました。"
        "AI取込の確認が完了しました。"
    )


    if is_ai_career_reviewing():
        render_ai_history_forms()
    else:
        render_history_list()

    if st.session_state.get(
        CAREER_HISTORY_EDIT_INDEX_KEY
    ) is None:
        if st.button(
            "＋ 新しい部署・役割を追加",
            key="career_history_new",
            use_container_width=True,
        ):
            st.session_state[
                CAREER_HISTORY_EDIT_INDEX_KEY
            ] = -1
            st.rerun()

    if st.session_state.get(
        CAREER_HISTORY_EDIT_INDEX_KEY
    ) == -1:
        with st.container(border=True):
            st.caption(
                "新しい部署・役割を入力してください"
            )
            render_history_form()

            st.button(
                "＋ 部署・役割を追加する",
                key="career_add_history_new",
                use_container_width=True,
                on_click=add_current_history,
            )

    career_errors = st.session_state.pop(
        CAREER_ERRORS_KEY,
        [],
    )

    for error in career_errors:
        st.error(error)

    history_edit_index = st.session_state.get(
        CAREER_HISTORY_EDIT_INDEX_KEY
    )

    st.divider()

    career_message = st.session_state.pop(
        CAREER_MESSAGE_KEY,
        None,
    )

    if career_message:
        st.success(career_message)

    if edit_index is None:
        if is_ai_career_reviewing():
            save_button_label = (
                "この会社を保存して次へ"
            )
        else:
            save_button_label = "保存する"

        action_columns = st.columns(
            [1, 1, 1]
        )

        with action_columns[1]:
            st.button(
                save_button_label,
                key="career_save",
                type="primary",
                use_container_width=True,
                on_click=save_current_company,
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
                on_click=cancel_company_edit,
            )

        with save_column:
            st.button(
                "変更を保存する",
                key="career_update",
                type="primary",
                use_container_width=True,
                on_click=save_current_company,
            )