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

PAGE_TITLE = "職務経歴"

CAREER_LOADED_KEY = "career_loaded"
CAREER_ITEMS_KEY = "career_items"
CAREER_FORM_RESET_KEY = "career_form_reset"
CAREER_MESSAGE_KEY = "career_message"
CAREER_ERRORS_KEY = "career_errors"
CAREER_ENTRY_MODE_KEY = "career_entry_mode"
CAREER_EDIT_INDEX_KEY = "career_edit_index"


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


def save_current_company() -> None:
    """現在の入力内容を一覧とDBへ保存する。"""

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
        st.session_state[
            "career_job_description"
        ] = history.job_description
        st.session_state["career_achievements"] = (
            history.achievements
        )

    else:
        st.session_state["career_department"] = ""
        st.session_state["career_position"] = ""
        st.session_state["career_industry"] = ""
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
                    "対応予定：PDF / Word"
                )

                st.button(
                    "ファイルを選択する",
                    key="career_upload",
                    use_container_width=True,
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

    career_errors = st.session_state.pop(
        CAREER_ERRORS_KEY,
        [],
    )

    for error in career_errors:
        st.error(error)

    render_company_list()

    edit_index = st.session_state.get(
        CAREER_EDIT_INDEX_KEY
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

    career_message = st.session_state.pop(
        CAREER_MESSAGE_KEY,
        None,
    )

    if career_message:
        st.success(career_message)

    if edit_index is None:
        action_columns = st.columns(
            [1, 1, 1]
        )

        with action_columns[1]:
            st.button(
                "保存する",
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