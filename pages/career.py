"""職務経歴入力画面。"""

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

PAGE_TITLE = "職務経歴"

CAREER_LOADED_KEY = "career_loaded"
CAREER_ITEMS_KEY = "career_items"
CAREER_FORM_RESET_KEY = "career_form_reset"
CAREER_MESSAGE_KEY = "career_message"
CAREER_ERRORS_KEY = "career_errors"


def initialize_career_state() -> None:
    """保存済みの職務経歴を画面と一覧へ復元する。"""

    if st.session_state.get(CAREER_LOADED_KEY):
        return

    career_items = load_career_data()

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
            history = histories[0]

            st.session_state["career_department"] = (
                history.department
            )
            st.session_state["career_position"] = (
                history.position
            )
            st.session_state["career_industry"] = (
                history.industry
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

    form_keys = [
        "career_company_name",
        "career_employment_type",
        "career_start_year",
        "career_start_month",
        "career_is_current",
        "career_end_year",
        "career_end_month",
        "career_department",
        "career_position",
        "career_industry",
        "career_occupation",
        "career_job_description",
        "career_achievements",
    ]

    for key in form_keys:
        st.session_state.pop(
            key,
            None,
        )

    st.session_state["career_start_year"] = 2020
    st.session_state["career_start_month"] = 4
    st.session_state["career_is_current"] = False
    st.session_state["career_end_year"] = 2025
    st.session_state["career_end_month"] = 10


def build_current_career_item(
    display_order: int,
) -> tuple[
    Career,
    list[CareerHistory],
]:
    """現在の入力フォームを1社分の職務経歴へ変換する。"""

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

    history = CareerHistory(
        department=st.session_state.get(
            "career_department",
            "",
        ),
        position=st.session_state.get(
            "career_position",
            "",
        ),
        industry=st.session_state.get(
            "career_industry",
            "",
        ),
        occupation=st.session_state.get(
            "career_occupation",
            "",
        ),
        start_year=career.start_year,
        start_month=career.start_month,
        end_year=career.end_year,
        end_month=career.end_month,
        job_description=st.session_state.get(
            "career_job_description",
            "",
        ),
        achievements=st.session_state.get(
            "career_achievements",
            "",
        ),
        display_order=1,
    )

    return (
        career,
        [history],
    )


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

    st.info(
        "まずは1社目を入力できるようにします。"
    )

    career_errors = st.session_state.pop(
        CAREER_ERRORS_KEY,
        [],
    )

    for error in career_errors:
        st.error(error)

    career_message = st.session_state.pop(
        CAREER_MESSAGE_KEY,
        None,
    )

    if career_message:
        st.success(career_message)

    st.subheader("会社情報")

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

    job_columns = st.columns(2)

    with job_columns[0]:
        st.text_input(
            "業種",
            placeholder="例：金融・クレジットカード",
            key="career_industry",
        )

    with job_columns[1]:
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


    st.divider()


    st.button(
        "＋会社を追加",
        key="career_add_company",
        use_container_width=True,
        on_click=add_current_company,
    )

    action_columns = st.columns([1, 1, 1])

    with action_columns[1]:
        if st.button(
            "保存する",
            key="career_save",
            type="primary",
            use_container_width=True,
        ):
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
                display_order=1,
            )

            history = CareerHistory(
                department=st.session_state.get(
                    "career_department",
                    "",
                ),
                position=st.session_state.get(
                    "career_position",
                    "",
                ),
                industry=st.session_state.get(
                    "career_industry",
                    "",
                ),
                occupation=st.session_state.get(
                    "career_occupation",
                    "",
                ),
                start_year=career.start_year,
                start_month=career.start_month,
                end_year=career.end_year,
                end_month=career.end_month,
                job_description=st.session_state.get(
                    "career_job_description",
                    "",
                ),
                achievements=st.session_state.get(
                    "career_achievements",
                    "",
                ),
                display_order=1,
            )

            career_items = [
                (
                    career,
                    [history],
                )
            ]

            try:
                save_errors = save_career_data(
                    career_items
                )

                if save_errors:
                    for error in save_errors:
                        st.error(error)

                else:
                    st.success(
                        "職務経歴を保存しました。"
                    )

            except Exception as error:
                st.error(
                    "職務経歴の保存に失敗しました。"
                    f"\n\n{error}"
                )