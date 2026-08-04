"""希望条件画面の表示を担当するモジュール。"""

from datetime import date

import streamlit as st

from data.master_data import (
    AGE_GROUP_OPTIONS,
    CAREER_CONDITIONS,
    EMPLOYMENT_TYPE_OPTIONS,
    HOLIDAY_OPTIONS,
    INDUSTRY_OPTIONS,
    OCCUPATION_OPTIONS,
    PREFECTURES,
    PRIORITY_LABELS,
    WORKSTYLE_CONDITIONS,
)


DRAFT_MESSAGE_KEY = "hope_conditions_draft_message"

# --------------------------------------------------
# 優先度の表示
# --------------------------------------------------

def format_priority(value: str) -> str:
    """優先度の内部値を日本語表示へ変換する。"""

    return PRIORITY_LABELS[value]


def render_priority_select(
    label: str,
    key: str,
    default: str = "no_preference",
    label_visibility: str = "visible",
) -> str:
    """優先度の選択欄を表示する。"""

    options = list(PRIORITY_LABELS)

    return st.selectbox(
        label,
        options=options,
        index=options.index(default),
        format_func=format_priority,
        key=key,
        label_visibility=label_visibility,
    )

# --------------------------------------------------
# 複数選択した項目ごとの優先度
# --------------------------------------------------

def render_selected_item_priorities(
    selected_values: list[str],
    key_prefix: str,
) -> None:
    """選択された項目ごとに優先度を表示する。"""

    if not selected_values:
        st.caption("項目を選択すると、優先度を設定できます。")
        return

    for rank, value in enumerate(selected_values, start=1):
        columns = st.columns([3, 2])

        with columns[0]:
            st.write(f"{rank}. {value}")

        with columns[1]:
            render_priority_select(
                "優先度",
                key=f"{key_prefix}_{rank}_{value}",
                default="want",
                label_visibility="collapsed",
            )


# --------------------------------------------------
# 固定条件ごとの優先度
# --------------------------------------------------

def render_condition_priorities(
    conditions: tuple[tuple[str, str], ...],
    key_prefix: str,
) -> None:
    """働き方などの条件ごとに優先度を表示する。"""

    for condition_code, condition_label in conditions:
        columns = st.columns([3, 2])

        with columns[0]:
            st.write(condition_label)

        with columns[1]:
            render_priority_select(
                "優先度",
                key=f"{key_prefix}_{condition_code}",
                label_visibility="collapsed",
            )


def render_hope_conditions_page() -> None:
    """希望条件の入力画面を表示する。"""

    if st.button(
        "← トップ画面へ戻る",
        key="hope_conditions_back_top",
    ):
        st.query_params.clear()
        st.rerun()

    st.title("希望条件")
    st.write("これからの働き方について教えてください")

    st.progress(
        4 / 6,
        text="入力のステップ 4 / 6",
    )

    st.info(
        "優先度を設定してください。\n\n"
        "必須：絶対に譲れない条件\n\n"
        "希望：できれば満たしたい条件\n\n"
        "許容：妥協できる条件\n\n"
        "こだわらない：求人比較の条件にしない"
    )

    # --------------------------------------------------
    # 1. 希望する仕事
    # --------------------------------------------------

    with st.expander(
        "1　希望する仕事 ★",
        expanded=True,
    ):
        st.write("希望業種と希望職種を選択してください。")

        job_columns = st.columns(2)

        with job_columns[0]:
            selected_industries = st.multiselect(
                "希望業種（最大3件）",
                options=INDUSTRY_OPTIONS,
                max_selections=3,
                key="hope_industries",
            )

            render_selected_item_priorities(
                selected_industries,
                "hope_industry_priority",
            )

        with job_columns[1]:
            selected_occupations = st.multiselect(
                "希望職種（最大3件）",
                options=OCCUPATION_OPTIONS,
                max_selections=3,
                key="hope_occupations",
            )

            render_selected_item_priorities(
                selected_occupations,
                "hope_occupation_priority",
            )

        st.text_area(
            "その他の希望業種・希望職種（任意）",
            max_chars=100,
            placeholder=(
                "選択肢にない業種や職種があれば"
                "入力してください"
            ),
            key="hope_other_jobs",
        )


    # --------------------------------------------------
    # 2. 勤務地・通勤
    # --------------------------------------------------

    with st.expander("2　勤務地・通勤 ★"):
        st.write(
            "希望勤務地や通勤時間、"
            "転勤の可否を入力してください。"
        )

        selected_prefectures = st.multiselect(
            "希望都道府県（最大2件）",
            options=PREFECTURES,
            max_selections=2,
            key="hope_prefectures",
        )

        for rank, prefecture in enumerate(
            selected_prefectures,
            start=1,
        ):
            location_columns = st.columns([3, 2])

            with location_columns[0]:
                st.text_input(
                    f"{prefecture}の希望市区町村",
                    placeholder="例）福岡市中央区",
                    key=f"hope_city_{rank}_{prefecture}",
                )

            with location_columns[1]:
                render_priority_select(
                    "勤務地の優先度",
                    key=(
                        f"hope_location_priority_"
                        f"{rank}_{prefecture}"
                    ),
                    default="want",
                )

        commute_columns = st.columns(2)

        with commute_columns[0]:
            st.number_input(
                "片道通勤時間の上限（分）",
                min_value=0,
                max_value=240,
                value=0,
                step=10,
                key="hope_commute_minutes",
                help="0分の場合は未設定として扱います。",
            )

        with commute_columns[1]:
            render_priority_select(
                "通勤時間の優先度",
                key="hope_commute_priority",
            )

        transfer_columns = st.columns(2)

        with transfer_columns[0]:
            st.selectbox(
                "転勤の可否",
                options=(
                    "こだわらない",
                    "転勤不可",
                    "条件次第で可",
                    "転勤可",
                ),
                key="hope_transfer",
            )

        with transfer_columns[1]:
            render_priority_select(
                "転勤条件の優先度",
                key="hope_transfer_priority",
            )


    # --------------------------------------------------
    # 3. 年収・雇用条件
    # --------------------------------------------------

    with st.expander("3　年収・雇用条件 ★"):
        st.write(
            "希望する年収と雇用形態を"
            "入力してください。"
        )

        salary_columns = st.columns(3)

        with salary_columns[0]:
            st.number_input(
                "最低許容年収（万円）",
                min_value=0,
                max_value=5000,
                value=0,
                step=10,
                key="hope_minimum_salary",
                help=(
                    "この金額を下回ると難しい"
                    "最低ラインです。"
                ),
            )

        with salary_columns[1]:
            st.number_input(
                "希望年収（万円）",
                min_value=0,
                max_value=5000,
                value=0,
                step=10,
                key="hope_desired_salary",
            )

        with salary_columns[2]:
            st.number_input(
                "理想年収（万円・任意）",
                min_value=0,
                max_value=5000,
                value=0,
                step=10,
                key="hope_ideal_salary",
            )

        st.caption(
            "最低許容年収は必須条件、"
            "希望年収は希望条件、"
            "理想年収は上振れ評価として扱います。"
        )

        selected_employment_types = st.multiselect(
            "希望する雇用形態",
            options=EMPLOYMENT_TYPE_OPTIONS,
            key="hope_employment_types",
        )

        render_selected_item_priorities(
            selected_employment_types,
            "hope_employment_priority",
        )


    # --------------------------------------------------
    # 4. 勤務時間・休日
    # --------------------------------------------------

    with st.expander("4　勤務時間・休日 ★"):
        st.write(
            "勤務時間や休日に関する希望を"
            "入力してください。"
        )

        overtime_columns = st.columns(2)

        with overtime_columns[0]:
            st.number_input(
                "月間残業時間の上限",
                min_value=0,
                max_value=200,
                value=0,
                step=5,
                key="hope_overtime_limit",
                help="0時間の場合は未設定として扱います。",
            )

        with overtime_columns[1]:
            render_priority_select(
                "残業時間の優先度",
                key="hope_overtime_priority",
            )

        work_time_columns = st.columns(2)

        with work_time_columns[0]:
            st.selectbox(
                "希望始業時刻",
                options=(
                    "こだわらない",
                    "8:00以降",
                    "9:00以降",
                    "10:00以降",
                    "11:00以降",
                ),
                key="hope_start_time",
            )

            render_priority_select(
                "始業時刻の優先度",
                key="hope_start_time_priority",
            )

        with work_time_columns[1]:
            st.selectbox(
                "希望終業時刻",
                options=(
                    "こだわらない",
                    "17:00まで",
                    "18:00まで",
                    "19:00まで",
                    "20:00まで",
                ),
                key="hope_end_time",
            )

            render_priority_select(
                "終業時刻の優先度",
                key="hope_end_time_priority",
            )

        st.write("勤務制度")

        time_system_conditions = (
            ("flex_time", "フレックスタイム制"),
            ("short_time", "時短勤務制度"),
        )

        render_condition_priorities(
            time_system_conditions,
            "hope_time_system",
        )

        shift_columns = st.columns(2)

        with shift_columns[0]:
            st.selectbox(
                "シフト勤務",
                options=(
                    "こだわらない",
                    "不可",
                    "条件次第で可",
                    "可",
                ),
                key="hope_shift_work",
            )

            render_priority_select(
                "シフト勤務の優先度",
                key="hope_shift_work_priority",
            )

        with shift_columns[1]:
            st.selectbox(
                "夜勤",
                options=(
                    "こだわらない",
                    "不可",
                    "条件次第で可",
                    "可",
                ),
                key="hope_night_work",
            )

            render_priority_select(
                "夜勤の優先度",
                key="hope_night_work_priority",
            )

        st.multiselect(
            "希望する休日",
            options=HOLIDAY_OPTIONS,
            key="hope_holidays",
        )

        render_priority_select(
            "休日条件の優先度",
            key="hope_holiday_priority",
        )

        annual_holiday_columns = st.columns(2)

        with annual_holiday_columns[0]:
            st.number_input(
                "希望する年間休日数",
                min_value=0,
                max_value=365,
                value=0,
                step=1,
                key="hope_annual_holidays",
                help="0日の場合は未設定として扱います。",
            )

        with annual_holiday_columns[1]:
            render_priority_select(
                "年間休日数の優先度",
                key="hope_annual_holiday_priority",
            )


    # --------------------------------------------------
    # 5. 働き方・職場環境
    # --------------------------------------------------

    with st.expander("5　働き方・職場環境 ☆"):
        st.write(
            "働き方や職場環境に関する希望を"
            "入力してください。"
        )

        st.subheader("働き方")

        render_condition_priorities(
            WORKSTYLE_CONDITIONS,
            "hope_workstyle",
        )

        st.subheader("キャリア・組織風土")

        render_condition_priorities(
            CAREER_CONDITIONS,
            "hope_career",
        )

        st.multiselect(
            "希望する職場の年齢層",
            options=AGE_GROUP_OPTIONS,
            key="hope_age_groups",
        )

        render_priority_select(
            "年齢層の優先度",
            key="hope_age_group_priority",
        )


    # --------------------------------------------------
    # 6. 入社条件
    # --------------------------------------------------

    with st.expander("6　入社条件 ☆"):
        st.write(
            "入社可能日と、その他の希望・"
            "NG条件を入力してください。"
        )

        st.date_input(
            "入社可能日",
            value=None,
            min_value=date.today(),
            key="hope_available_date",
        )

        st.text_area(
            "その他の希望・NG条件（任意）",
            max_chars=500,
            placeholder=(
                "求人を比較するときに確認したいことや、"
                "受け入れられない条件を入力してください"
            ),
            key="hope_other_conditions",
        )



    # --------------------------------------------------
    # 画面下部の操作
    # --------------------------------------------------

    st.divider()

    action_columns = st.columns(3)

    with action_columns[0]:
        if st.button(
            "← トップ画面へ戻る",
            key="hope_conditions_back_bottom",
            use_container_width=True,
        ):
            st.query_params.clear()
            st.rerun()

    with action_columns[1]:
        if st.button(
            "一時保存",
            key="hope_conditions_temporary_save",
            use_container_width=True,
        ):
            st.session_state[DRAFT_MESSAGE_KEY] = (
                "入力内容を現在のセッション内に"
                "保持しました。"
            )

    with action_columns[2]:
        st.button(
            "確認画面へ進む →",
            key="hope_conditions_confirm",
            use_container_width=True,
            disabled=True,
            help="確認画面は別の実装タスクで作成します。",
        )

    saved_message = st.session_state.get(
        DRAFT_MESSAGE_KEY
    )

    if saved_message:
        st.success(saved_message)

    st.caption(
        "今回の一時保存はst.session_stateへの保持です。"
        "アプリを停止した後も残るSQLite保存は、"
        "データ構造確定後の別タスクで実装します。"
    )