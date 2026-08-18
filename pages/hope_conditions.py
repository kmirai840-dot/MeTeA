"""希望条件画面の表示を担当するモジュール。"""

from datetime import date
from html import escape

import streamlit as st

from data.master_data import (
    AGE_GROUP_OPTIONS,
    CAREER_CONDITIONS,
    CAREER_PRIORITY_LABELS,
    EMPLOYMENT_TYPE_OPTIONS,
    HOLIDAY_OPTIONS,
    INDUSTRY_OPTIONS,
    OCCUPATION_OPTIONS,
    PREFECTURES,
    PRIORITY_LABELS,
    WORKSTYLE_CONDITIONS,
)

from pages.self_discovery_theme import apply_self_discovery_theme

from models import HopeCondition, HopeConditionItem
from services.hope_condition_service import (
    load_hope_conditions_data,
    load_hope_conditions_draft,
    save_hope_conditions_data,
    save_hope_conditions_draft,
)


DRAFT_MESSAGE_KEY = "hope_conditions_draft_message"
DRAFT_LOADED_KEY = "hope_conditions_draft_loaded"
ERRORS_KEY = "hope_conditions_validation_errors"
PRIORITY_LABELS_WITHOUT_NO_PREFERENCE = {
    key: label
    for key, label in PRIORITY_LABELS.items()
    if key != "no_preference"
}


def initialize_hope_conditions_state() -> None:
    """下書きまたは正式保存データを画面へ復元する。"""

    # 別画面へ移動するとWidgetの状態だけが破棄されることがある。
    # 復元済みフラグに加えて代表的な入力値が残っている場合のみ省略する。
    if ERRORS_KEY not in st.session_state:
        st.session_state[ERRORS_KEY] = {}

    if (
        st.session_state.get(DRAFT_LOADED_KEY)
        and "hope_minimum_salary" in st.session_state
    ):
        return

    draft_data = load_hope_conditions_draft()

    if draft_data:
        for key, value in draft_data.items():
            # ボタンの一時的な状態は復元対象にしない。
            if key in {
                "hope_conditions_back_top",
                "hope_conditions_back_bottom",
                "hope_conditions_temporary_save",
                "hope_conditions_save",
            }:
                continue

            if (
                key == "hope_available_date"
                and isinstance(value, str)
                and value
            ):
                value = date.fromisoformat(value)

            st.session_state[key] = value

    else:
        hope_condition, items = load_hope_conditions_data()

        if hope_condition is not None:
            st.session_state["hope_minimum_salary"] = (
                hope_condition.minimum_salary
            )
            st.session_state["hope_desired_salary"] = (
                hope_condition.desired_salary
            )
            st.session_state["hope_ideal_salary"] = (
                hope_condition.ideal_salary
            )
            st.session_state["hope_commute_minutes"] = (
                hope_condition.commute_minutes
            )
            st.session_state["hope_transfer"] = (
                hope_condition.transfer_condition
            )
            st.session_state["hope_commute_priority"] = (
                hope_condition.commute_priority
            )
            st.session_state["hope_transfer_priority"] = (
                hope_condition.transfer_priority
            )
            st.session_state["hope_overtime_limit"] = (
                hope_condition.overtime_limit
            )
            st.session_state["hope_overtime_priority"] = (
                hope_condition.overtime_priority
            )
            st.session_state["hope_start_time"] = (
                hope_condition.start_time
            )
            st.session_state["hope_start_time_priority"] = (
                hope_condition.start_time_priority
            )
            st.session_state["hope_end_time"] = (
                hope_condition.end_time
            )
            st.session_state["hope_end_time_priority"] = (
                hope_condition.end_time_priority
            )
            st.session_state["hope_shift_work"] = (
                hope_condition.shift_work
            )
            st.session_state["hope_shift_work_priority"] = (
                hope_condition.shift_work_priority
            )
            st.session_state["hope_night_work"] = (
                hope_condition.night_work
            )
            st.session_state["hope_night_work_priority"] = (
                hope_condition.night_work_priority
            )
            st.session_state["hope_holiday_priority"] = (
                hope_condition.holiday_priority
            )
            st.session_state["hope_annual_holidays"] = (
                hope_condition.annual_holidays
            )
            st.session_state["hope_annual_holiday_priority"] = (
                hope_condition.annual_holiday_priority
            )
            st.session_state["hope_available_date"] = (
                hope_condition.available_date
            )
            st.session_state["hope_other_jobs"] = (
                hope_condition.other_jobs
            )
            st.session_state["hope_other_conditions"] = (
                hope_condition.other_conditions
            )

        st.session_state["hope_industry_no_preference"] = any(
            item.condition_type == "industry"
            and item.condition_value == "こだわらない"
            for item in items
        )

        st.session_state["hope_industries"] = [
            item.condition_value
            for item in items
            if item.condition_type == "industry"
            and item.condition_value != "こだわらない"
        ]

        st.session_state["hope_occupations"] = [
            item.condition_value
            for item in items
            if item.condition_type == "occupation"
        ]

        st.session_state["hope_prefectures"] = [
            item.condition_value
            for item in items
            if item.condition_type == "location"
        ]

        st.session_state["hope_employment_types"] = [
            item.condition_value
            for item in items
            if item.condition_type == "employment_type"
        ]

        st.session_state["hope_holidays"] = [
            item.condition_value
            for item in items
            if item.condition_type == "holiday"
        ]

        st.session_state["hope_age_groups"] = [
            item.condition_value
            for item in items
            if item.condition_type == "age_group"
        ]

        # 複数選択項目ごとの優先度・補足値を復元する。
        ranked_item_settings = {
            "industry": "hope_industry_priority",
            "occupation": "hope_occupation_priority",
            "location": "hope_location_priority",
            "employment_type": "hope_employment_priority",
        }

        for condition_type, key_prefix in ranked_item_settings.items():
            ranked_items = sorted(
                (
                    item
                    for item in items
                    if item.condition_type == condition_type
                    and item.condition_value != "こだわらない"
                ),
                key=lambda item: item.rank or 0,
            )

            for fallback_rank, item in enumerate(
                ranked_items,
                start=1,
            ):
                rank = item.rank or fallback_rank
                st.session_state[
                    f"{key_prefix}_{rank}_{item.condition_value}"
                ] = item.priority

                if condition_type == "location":
                    st.session_state[
                        f"hope_city_{rank}_{item.condition_value}"
                    ] = item.detail_value or ""

        age_group_item = next(
            (
                item
                for item in items
                if item.condition_type == "age_group"
            ),
            None,
        )
        if age_group_item is not None:
            st.session_state["hope_age_group_priority"] = (
                age_group_item.priority
            )

        # 固定条件型の優先度を、表示時に使用するWidgetキーへ戻す。
        fixed_condition_groups = (
            (
                "time_system",
                (
                    ("flex_time", "フレックスタイム制"),
                    ("short_time", "時短勤務制度"),
                ),
                "hope_time_system",
            ),
            ("workstyle", WORKSTYLE_CONDITIONS, "hope_workstyle"),
            (
                "career_condition",
                CAREER_CONDITIONS,
                "hope_career",
            ),
        )

        for condition_type, conditions, key_prefix in fixed_condition_groups:
            saved_priorities = {
                item.condition_value: item.priority
                for item in items
                if item.condition_type == condition_type
            }
            for code, label in conditions:
                st.session_state[f"{key_prefix}_{code}"] = (
                    saved_priorities.get(label, "no_preference")
                )

    st.session_state[DRAFT_LOADED_KEY] = True


def validate_hope_conditions() -> dict[str, str]:
    """希望条件の必須・条件付き必須項目を検証する。"""

    errors: dict[str, str] = {}

    if not st.session_state.get("hope_occupations"):
        errors["hope_occupations"] = "希望職種を1件以上選択してください"

    prefectures = st.session_state.get("hope_prefectures", [])
    if not prefectures:
        errors["hope_prefectures"] = "希望都道府県を1件以上選択してください"

    for rank, prefecture in enumerate(prefectures, start=1):
        priority_key = f"hope_location_priority_{rank}_{prefecture}"
        if st.session_state.get(priority_key) not in {
            "must",
            "want",
            "acceptable",
        }:
            errors[priority_key] = (
                f"{prefecture}の勤務地優先度を選択してください"
            )

    minimum_salary = st.session_state.get("hope_minimum_salary", 0) or 0
    desired_salary = st.session_state.get("hope_desired_salary", 0) or 0
    ideal_salary = st.session_state.get("hope_ideal_salary", 0) or 0

    if minimum_salary <= 0:
        errors["hope_minimum_salary"] = "最低許容年収を入力してください"
    if desired_salary <= 0:
        errors["hope_desired_salary"] = "希望年収を入力してください"
    if minimum_salary > 0 and desired_salary > 0 and minimum_salary > desired_salary:
        errors["hope_desired_salary"] = (
            "希望年収は最低許容年収以上で入力してください"
        )
    if ideal_salary > 0 and desired_salary > 0 and ideal_salary < desired_salary:
        errors["hope_ideal_salary"] = (
            "理想年収は希望年収以上で入力してください"
        )

    if not st.session_state.get("hope_employment_types"):
        errors["hope_employment_types"] = "希望する雇用形態を1件以上選択してください"

    conditional_numbers = (
        (
            "hope_commute_priority",
            "hope_commute_minutes",
            "片道通勤時間の上限を入力してください",
        ),
        (
            "hope_overtime_priority",
            "hope_overtime_limit",
            "月間残業時間の上限を入力してください",
        ),
        (
            "hope_annual_holiday_priority",
            "hope_annual_holidays",
            "希望する年間休日数を入力してください",
        ),
    )
    for priority_key, value_key, message in conditional_numbers:
        if (
            st.session_state.get(priority_key, "no_preference")
            != "no_preference"
            and (st.session_state.get(value_key, 0) or 0) <= 0
        ):
            errors[value_key] = message

    if (
        st.session_state.get("hope_holiday_priority", "no_preference")
        != "no_preference"
        and not st.session_state.get("hope_holidays")
    ):
        errors["hope_holidays"] = "希望する休日を1件以上選択してください"

    return errors


def render_hope_error_summary(errors: dict[str, str]) -> None:
    """ページ上部に希望条件のエラーをまとめて表示する。"""

    if not errors:
        return

    error_items = "".join(
        f"<li>{escape(message)}</li>"
        for message in dict.fromkeys(errors.values())
    )
    st.markdown(
        '<div class="metea-hope-error-summary" role="alert">'
        '<span class="metea-hope-error-icon">!</span>'
        '<div><strong>入力内容を確認してください</strong>'
        f'<ul>{error_items}</ul></div></div>',
        unsafe_allow_html=True,
    )


def render_hope_error_field_styles(errors: dict[str, str]) -> None:
    """エラー対象の希望条件入力欄を赤枠で強調する。"""

    selectors: list[str] = []
    for widget_key in sorted(errors):
        selectors.extend((
            # 複数選択は検索用inputではなく、外側の選択枠を強調する。
            f'.st-key-{widget_key} [data-baseweb="select"] > div',
            # Streamlit 1.60系の単一選択欄。
            f'.st-key-{widget_key} [data-testid="stSelectbox"] [role="group"]',
            # 数値入力は増減ボタンを含む枠全体を強調する。
            f'.st-key-{widget_key} [data-testid="stNumberInputContainer"]',
            # 通常の文字入力・テキストエリア。
            f'.st-key-{widget_key} [data-testid="stTextInput"] input',
            f'.st-key-{widget_key} [data-testid="stTextArea"] textarea',
        ))

    if not selectors:
        return

    st.markdown(
        "<style>"
        + ",".join(selectors)
        + "{border:1.5px solid #ef4b55 !important;"
          "background:#fffafa !important;"
          "box-sizing:border-box !important;"
          "box-shadow:0 0 0 2px rgba(239,75,85,.08) !important;}"
          "</style>",
        unsafe_allow_html=True,
    )


def render_hope_field_error(errors: dict[str, str], field_key: str) -> None:
    """希望条件の入力欄直下にエラーメッセージを表示する。"""

    message = errors.get(field_key)
    if message:
        st.markdown(
            f'<p class="metea-hope-field-error">{escape(message)}</p>',
            unsafe_allow_html=True,
        )


def collect_hope_conditions_draft() -> dict[str, object]:
    """希望条件画面の入力値を下書き保存用に集める。"""

    excluded_keys = {
        "hope_conditions_back_top",
        "hope_conditions_back_bottom",
        "hope_conditions_temporary_save",
        "hope_conditions_save",
        DRAFT_MESSAGE_KEY,
        DRAFT_LOADED_KEY,
        ERRORS_KEY,
    }

    draft_data: dict[str, object] = {}

    for key, value in st.session_state.items():
        if not key.startswith("hope_"):
            continue

        if key in excluded_keys:
            continue

        if isinstance(value, date):
            draft_data[key] = value.isoformat()
        else:
            draft_data[key] = value

    return draft_data

def build_hope_condition() -> HopeCondition:
    """画面の単一値を正式保存用データへ変換する。"""

    return HopeCondition(
        minimum_salary=st.session_state.get(
            "hope_minimum_salary",
            0,
        ),
        desired_salary=st.session_state.get(
            "hope_desired_salary",
            0,
        ),
        ideal_salary=st.session_state.get(
            "hope_ideal_salary",
            0,
        ),
        commute_minutes=st.session_state.get(
            "hope_commute_minutes",
            0,
        ),
        transfer_condition=st.session_state.get(
            "hope_transfer",
            "こだわらない",
        ),
        commute_priority=st.session_state.get(
            "hope_commute_priority",
            "no_preference",
        ),
        transfer_priority=st.session_state.get(
            "hope_transfer_priority",
            "no_preference",
        ) if st.session_state.get(
            "hope_transfer", "こだわらない"
        ) != "こだわらない" else "no_preference",
        overtime_limit=st.session_state.get(
            "hope_overtime_limit",
            0,
        ),
        overtime_priority=st.session_state.get(
            "hope_overtime_priority",
            "no_preference",
        ),
        start_time=st.session_state.get(
            "hope_start_time",
            "こだわらない",
        ),
        start_time_priority=st.session_state.get(
            "hope_start_time_priority",
            "no_preference",
        ) if st.session_state.get(
            "hope_start_time", "こだわらない"
        ) != "こだわらない" else "no_preference",
        end_time=st.session_state.get(
            "hope_end_time",
            "こだわらない",
        ),
        end_time_priority=st.session_state.get(
            "hope_end_time_priority",
            "no_preference",
        ) if st.session_state.get(
            "hope_end_time", "こだわらない"
        ) != "こだわらない" else "no_preference",
        shift_work=st.session_state.get(
            "hope_shift_work",
            "こだわらない",
        ),
        shift_work_priority=st.session_state.get(
            "hope_shift_work_priority",
            "no_preference",
        ) if st.session_state.get(
            "hope_shift_work", "こだわらない"
        ) != "こだわらない" else "no_preference",
        night_work=st.session_state.get(
            "hope_night_work",
            "こだわらない",
        ),
        night_work_priority=st.session_state.get(
            "hope_night_work_priority",
            "no_preference",
        ) if st.session_state.get(
            "hope_night_work", "こだわらない"
        ) != "こだわらない" else "no_preference",
        holiday_priority=st.session_state.get(
            "hope_holiday_priority",
            "no_preference",
        ),
        annual_holidays=st.session_state.get(
            "hope_annual_holidays",
            0,
        ),
        annual_holiday_priority=st.session_state.get(
            "hope_annual_holiday_priority",
            "no_preference",
        ),
        available_date=st.session_state.get(
            "hope_available_date"
        ),
        other_jobs=st.session_state.get(
            "hope_other_jobs",
            "",
        ),
        other_conditions=st.session_state.get(
            "hope_other_conditions",
            "",
        ),
    )


def build_hope_condition_items() -> list[HopeConditionItem]:
    """画面の複数選択値を正式保存用データへ変換する。"""

    items: list[HopeConditionItem] = []

    # 希望業種
    if st.session_state.get(
        "hope_industry_no_preference",
        False,
    ):
        items.append(
            HopeConditionItem(
                condition_type="industry",
                condition_value="こだわらない",
                priority="no_preference",
                rank=1,
            )
        )
    else:
        for rank, value in enumerate(
            st.session_state.get("hope_industries", []),
            start=1,
        ):
            items.append(
                HopeConditionItem(
                    condition_type="industry",
                    condition_value=value,
                    priority=st.session_state.get(
                        f"hope_industry_priority_{rank}_{value}",
                        "want",
                    ),
                    rank=rank,
                )
            )

    # 希望職種
    for rank, value in enumerate(
        st.session_state.get("hope_occupations", []),
        start=1,
    ):
        items.append(
            HopeConditionItem(
                condition_type="occupation",
                condition_value=value,
                priority=st.session_state.get(
                    f"hope_occupation_priority_{rank}_{value}",
                    "want",
                ),
                rank=rank,
            )
        )

    # 希望勤務地
    for rank, value in enumerate(
        st.session_state.get("hope_prefectures", []),
        start=1,
    ):
        items.append(
            HopeConditionItem(
                condition_type="location",
                condition_value=value,
                priority=st.session_state.get(
                    f"hope_location_priority_{rank}_{value}",
                    "want",
                ),
                rank=rank,
                detail_value=st.session_state.get(
                    f"hope_city_{rank}_{value}",
                    "",
                ),
            )
        )

    # 雇用形態
    for rank, value in enumerate(
        st.session_state.get(
            "hope_employment_types",
            [],
        ),
        start=1,
    ):
        items.append(
            HopeConditionItem(
                condition_type="employment_type",
                condition_value=value,
                priority=st.session_state.get(
                    f"hope_employment_priority_{rank}_{value}",
                    "want",
                ),
                rank=rank,
            )
        )

    # 希望休日
    for rank, value in enumerate(
        st.session_state.get("hope_holidays", []),
        start=1,
    ):
        items.append(
            HopeConditionItem(
                condition_type="holiday",
                condition_value=value,
                priority=st.session_state.get(
                    "hope_holiday_priority",
                    "no_preference",
                ),
                rank=rank,
            )
        )

    # 希望する職場の年齢層
    for rank, value in enumerate(
        st.session_state.get("hope_age_groups", []),
        start=1,
    ):
        items.append(
            HopeConditionItem(
                condition_type="age_group",
                condition_value=value,
                priority=st.session_state.get(
                    "hope_age_group_priority",
                    "no_preference",
                ),
                rank=rank,
            )
        )

    # 勤務制度
    time_system_conditions = (
        ("flex_time", "フレックスタイム制"),
        ("short_time", "時短勤務制度"),
    )

    for code, label in time_system_conditions:
        priority = st.session_state.get(
            f"hope_time_system_{code}",
            "no_preference",
        )

        if priority != "no_preference":
            items.append(
                HopeConditionItem(
                    condition_type="time_system",
                    condition_value=label,
                    priority=priority,
                )
            )

    # 働き方
    for code, label in WORKSTYLE_CONDITIONS:
        priority = st.session_state.get(
            f"hope_workstyle_{code}",
            "no_preference",
        )

        if priority != "no_preference":
            items.append(
                HopeConditionItem(
                    condition_type="workstyle",
                    condition_value=label,
                    priority=priority,
                )
            )

    # キャリア・組織風土
    for code, label in CAREER_CONDITIONS:
        priority = st.session_state.get(
            f"hope_career_{code}",
            "no_preference",
        )

        if priority != "no_preference":
            items.append(
                HopeConditionItem(
                    condition_type="career_condition",
                    condition_value=label,
                    priority=priority,
                )
            )

    return items

# --------------------------------------------------
# 優先度の表示
# --------------------------------------------------

def render_priority_select(
    label: str,
    key: str,
    default: str = "no_preference",
    label_visibility: str = "visible",
    priority_labels: dict[str, str] = PRIORITY_LABELS,
) -> str:
    """優先度の選択欄を表示する。"""

    options = list(priority_labels)

    # 選択肢構成を変更した場合、保存済みの対象外値を有効な初期値へ移す。
    if st.session_state.get(key) not in (None, *options):
        st.session_state[key] = (
            default if default in options else options[0]
        )

    if default not in options:
        default = options[0]

    return st.selectbox(
        label,
        options=options,
        index=options.index(default),
        format_func=lambda value: priority_labels[value],
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
    priority_labels: dict[str, str] = PRIORITY_LABELS,
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
                priority_labels=priority_labels,
            )


def required_input_label(label: str, required: bool = True) -> str:
    """必須となる入力欄へ共通の赤いアスタリスクを付ける。"""

    return f"{label} :red[*]" if required else label


def priority_requires_value(priority_key: str) -> bool:
    """「こだわらない」以外の優先度なら対応値を必須とする。"""

    return st.session_state.get(priority_key, "no_preference") != "no_preference"


def render_hope_conditions_page() -> None:
    """希望条件の入力画面を表示する。"""

    apply_self_discovery_theme(current_step=2)

    st.markdown(
        """
        <span class="metea-hope-page-marker" aria-hidden="true"></span>
        <style>
        /* 基本情報画面と同じPCカード位置・サイズ・文字密度へ揃える。 */
        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker),
        section.main > div.block-container:has(.metea-hope-page-marker) {
            box-sizing: border-box;
            width: calc(100vw - 272px);
            max-width: none;
            height: calc(100dvh - 84px);
            min-height: 620px;
            margin: 66px 28px 18px 244px;
            padding: 12px 34px 18px;
            overflow-x: hidden;
            overflow-y: auto;
            scrollbar-gutter: stable;
            overscroll-behavior: contain;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker) h1 {
            margin-top: 0;
            margin-bottom: 0;
            font-size: clamp(1.9rem, 2.3vw, 2.35rem);
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        > [data-testid="stVerticalBlock"],
        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        > div > [data-testid="stVerticalBlock"] {
            gap: 0.45rem;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stProgress"] {
            margin: 2px 0 7px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        .metea-priority-guide {
            margin: 5px 0 0;
            padding: 9px 13px;
        }

        .metea-hope-expander-boundary {
            display: block;
            width: 100%;
            height: 12px;
        }

        [data-testid="stElementContainer"]:has(.metea-hope-expander-boundary) {
            min-height: 12px;
            height: 12px;
            overflow: hidden;
        }

        .metea-hope-error-summary {
            display: flex;
            gap: 14px;
            align-items: flex-start;
            margin: 4px 0 10px;
            padding: 13px 16px;
            border: 1.5px solid #ffb8bd;
            border-radius: 11px;
            background: #fff7f7;
            color: #d92d3a;
        }

        .metea-hope-error-icon {
            display: grid;
            place-items: center;
            flex: 0 0 25px;
            width: 25px;
            height: 25px;
            border: 2px solid #ef3f4c;
            border-radius: 7px 7px 9px 9px;
            font-weight: 900;
            line-height: 1;
        }

        .metea-hope-error-summary strong { font-size: 0.95rem; }
        .metea-hope-error-summary ul { margin: 5px 0 0; padding-left: 1.15rem; }
        .metea-hope-error-summary li { margin: 2px 0; font-size: 0.88rem; }

        .metea-hope-field-error {
            display: block;
            min-height: 18px;
            margin: 1px 0 4px !important;
            color: #dc3545 !important;
            font-size: 0.84rem !important;
            font-weight: 650;
            line-height: 1.35 !important;
        }

        [data-testid="stElementContainer"]:has(.metea-hope-field-error) {
            min-height: 23px;
            margin-bottom: 2px;
            overflow: visible;
        }

        /* 複数選択の候補は、右端のチェック状態で選択可否を明示する。 */
        /*
         * Streamlit/BaseWeb は候補リストをポータル内の仮想リストとして
         * 描画するため、実際に付与される testid を基準にする。
         */
        [data-testid="stSelectboxVirtualDropdown"]:has([role="option"]:nth-child(5))
        [role="option"] {
            position: relative;
            min-height: 40px;
            padding-right: 48px !important;
        }

        [data-testid="stSelectboxVirtualDropdown"]:has([role="option"]:nth-child(5))
        [role="option"]::after {
            content: "";
            position: absolute;
            top: 50%;
            right: 15px;
            box-sizing: border-box;
            width: 18px;
            height: 18px;
            border: 1.5px solid #aebacc;
            border-radius: 4px;
            background: #ffffff;
            transform: translateY(-50%);
        }

        [data-testid="stSelectboxVirtualDropdown"]:has([role="option"]:nth-child(5))
        [role="option"][aria-selected="true"]::after {
            content: "✓";
            display: grid;
            place-items: center;
            border-color: var(--metea-blue);
            background: var(--metea-blue);
            color: #ffffff;
            font-size: 12px;
            font-weight: 900;
            line-height: 1;
        }

        [data-testid="stSelectboxVirtualDropdown"]:has([role="option"]:nth-child(5))
        [role="option"][aria-disabled="true"]::after {
            border-color: #d7dee8;
            background: #eef2f6;
        }

        /* 一括選択は使用しないため、Select all 行だけチェックを表示しない。 */
        [data-testid="stSelectboxVirtualDropdown"]:has([role="option"]:nth-child(5))
        [role="option"]:first-child::after {
            content: none !important;
            display: none !important;
        }

        /* カード内の優先度も、画面上部と同じ色付きタグとして見せる。 */
        [data-testid="stSelectbox"]:has(input[aria-label*="優先度"][value="必須"])
        [role="group"] {
            border-color: #f3b9b4 !important;
            background: #fff0ef !important;
            color: #b42318 !important;
            font-weight: 700;
        }

        input[aria-label*="優先度"][value="必須"] {
            background: #fff0ef !important;
            color: #b42318 !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label*="優先度"][value="希望"])
        [role="group"] {
            border-color: #b9d6ff !important;
            background: #eaf3ff !important;
            color: #075fdc !important;
            font-weight: 700;
        }

        input[aria-label*="優先度"][value="希望"] {
            background: #eaf3ff !important;
            color: #075fdc !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label*="優先度"][value="許容"])
        [role="group"] {
            border-color: #b7e8da !important;
            background: #eaf9f4 !important;
            color: #08745d !important;
            font-weight: 700;
        }

        input[aria-label*="優先度"][value="許容"] {
            background: #eaf9f4 !important;
            color: #08745d !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label*="優先度"][value="こだわらない"])
        [role="group"] {
            border-color: #b8c3d1 !important;
            background: #e8edf3 !important;
            color: #405168 !important;
            font-weight: 700;
        }

        input[aria-label*="優先度"][value="こだわらない"] {
            background: #e8edf3 !important;
            color: #405168 !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label*="優先度"][value="希望しない"])
        [role="group"] {
            border-color: #f0c778 !important;
            background: #fff4df !important;
            color: #945700 !important;
            font-weight: 700;
        }

        input[aria-label*="優先度"][value="希望しない"] {
            background: #fff4df !important;
            color: #945700 !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label*="優先度"][value="不可"])
        [role="group"] {
            border-color: #e6a2aa !important;
            background: #fdebed !important;
            color: #9f2431 !important;
            font-weight: 700;
        }

        input[aria-label*="優先度"][value="不可"] {
            background: #fdebed !important;
            color: #9f2431 !important;
            font-weight: 700 !important;
        }

        /* 転勤可否も、意味が近い優先度タグの配色へ統一する。 */
        [data-testid="stSelectbox"]:has(input[aria-label="転勤の可否"][value="転勤不可"])
        [role="group"],
        input[aria-label="転勤の可否"][value="転勤不可"] {
            border-color: #f3b9b4 !important;
            background: #fff0ef !important;
            color: #b42318 !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label="転勤の可否"][value="転勤可"])
        [role="group"],
        input[aria-label="転勤の可否"][value="転勤可"] {
            border-color: #b9d6ff !important;
            background: #eaf3ff !important;
            color: #075fdc !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label="転勤の可否"][value="条件次第で可"])
        [role="group"],
        input[aria-label="転勤の可否"][value="条件次第で可"] {
            border-color: #b7e8da !important;
            background: #eaf9f4 !important;
            color: #08745d !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label="転勤の可否"][value="こだわらない"])
        [role="group"],
        input[aria-label="転勤の可否"][value="こだわらない"] {
            border-color: #b8c3d1 !important;
            background: #e8edf3 !important;
            color: #405168 !important;
            font-weight: 700 !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label="転勤の可否"])
        [role="group"] {
            min-height: 38px;
            border-radius: 10px !important;
            box-shadow: none !important;
        }

        [data-testid="stSelectbox"]:has(input[aria-label*="優先度"])
        [role="group"] {
            min-height: 38px;
            border-radius: 10px !important;
            box-shadow: none !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-location-card-marker) {
            margin: 8px 0 10px;
            border: 1px solid #d7e2f0 !important;
            border-radius: 12px !important;
            background: #fbfdff;
            box-shadow: 0 3px 10px rgba(31, 65, 114, 0.045);
        }

        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-location-card-marker)
        [data-testid="stVerticalBlock"] {
            gap: 0.45rem;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        .metea-priority-guide__intro {
            gap: 9px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        .metea-priority-guide__intro p {
            margin-top: 1px;
            line-height: 1.35;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        .metea-priority-guide__items {
            gap: 8px;
            margin-top: 6px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        .metea-priority-guide__items > div {
            padding: 7px 10px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        .metea-priority-guide__items p {
            margin-top: 4px;
            line-height: 1.3;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stExpander"] {
            margin-bottom: 4px;
            overflow: hidden;
            border: 1px solid var(--metea-line) !important;
            border-radius: 12px !important;
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(31, 65, 114, 0.055);
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stExpander"] details,
        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stExpander"] summary {
            border-radius: 11px !important;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stExpander"] details[open] summary {
            border-radius: 11px 11px 0 0 !important;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stExpander"] summary {
            min-height: 39px;
            padding: 0 10px;
            font-size: 0.91rem;
            line-height: 1.25;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stExpander"] summary p {
            font-size: 0.91rem;
            line-height: 1.25;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stDivider"] {
            margin: 0.55rem 0;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
        [data-testid="stCaptionContainer"] {
            font-size: 0.8rem !important;
            line-height: 1.35;
        }

        @media (max-height: 820px) and (min-width: 1101px) {
            [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker),
            section.main > div.block-container:has(.metea-hope-page-marker) {
                width: calc(100vw - 264px);
                height: calc(100dvh - 58px);
                min-height: 0;
                margin: 48px 20px 10px 244px;
                padding: 10px 30px 12px;
            }
        }

        @media (max-width: 1100px) {
            [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker),
            section.main > div.block-container:has(.metea-hope-page-marker) {
                width: calc(100vw - 36px);
                max-width: none;
                height: calc(100dvh - 36px);
                min-height: 0;
                margin: 18px;
                padding: 22px 28px 28px;
            }
        }

        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker),
            section.main > div.block-container:has(.metea-hope-page-marker) {
                width: 100%;
                height: auto;
                min-height: 100dvh;
                margin: 0;
                padding: 20px 16px 32px;
                overflow: visible;
                border-left: 0;
                border-right: 0;
                border-radius: 0;
            }

            [data-testid="stMainBlockContainer"]:has(.metea-hope-page-marker)
            .metea-priority-guide__items {
                grid-template-columns: 1fr 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    initialize_hope_conditions_state()

    basic_info_message = st.session_state.pop(
        "basic_info_save_message",
        None,
    )
    if basic_info_message:
        st.toast(basic_info_message)

    if st.button(
        "← 基本情報へ戻る",
        key="hope_conditions_back_top",
    ):
        st.query_params["page"] = "basic_info"
        st.rerun()

    st.title("希望条件")
    st.write("これからの働き方について教えてください")

    st.progress(
        2 / 5,
        text="自分を知る 2 / 5　希望条件",
    )

    errors = st.session_state.get(ERRORS_KEY, {})
    render_hope_error_summary(errors)
    render_hope_error_field_styles(errors)

    st.markdown(
        """
        <section class="metea-priority-guide">
          <div class="metea-priority-guide__intro">
            <span class="metea-priority-guide__icon">i</span>
            <div><strong>優先度を設定してください</strong>
            <p>求人を比較するときに、どの程度重視するかを選びます。</p></div>
          </div>
          <div class="metea-priority-guide__items">
            <div><span class="is-required">必須</span><p>絶対に譲れない条件</p></div>
            <div><span class="is-desired">希望</span><p>できれば満たしたい条件</p></div>
            <div><span class="is-acceptable">許容</span><p>状況により妥協できる条件</p></div>
            <div><span class="is-neutral">こだわらない</span><p>求人比較の条件にしない</p></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------
    # 1. 希望する仕事
    # --------------------------------------------------

    st.markdown(
        '<span class="metea-hope-expander-boundary" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    with st.expander(
        "1　希望する仕事",
        expanded=any(
            key in errors
            for key in (
                "hope_occupations",
                "hope_industries",
            )
        ),
    ):
        st.write("希望業種と希望職種を選択してください。")

        job_columns = st.columns(2)

        with job_columns[0]:
            industry_no_preference = st.checkbox(
                "企業の業種にはこだわらない",
                key="hope_industry_no_preference",
            )

            selected_industries = st.multiselect(
                "企業業種（最大3件）",
                options=INDUSTRY_OPTIONS,
                max_selections=3,
                key="hope_industries",
                disabled=industry_no_preference,
                placeholder="項目を選択（複数選択可）",
            )

            if industry_no_preference:
                st.caption(
                    "企業業種はAIマッチングの評価対象にしません。"
                )
            else:
                render_selected_item_priorities(
                    selected_industries,
                    "hope_industry_priority",
                )

        with job_columns[1]:
            selected_occupations = st.multiselect(
                required_input_label("希望職種（最大3件）"),
                options=OCCUPATION_OPTIONS,
                max_selections=3,
                key="hope_occupations",
                placeholder="項目を選択（複数選択可）",
            )
            render_hope_field_error(errors, "hope_occupations")

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

    with st.expander(
        "2　勤務地・通勤",
        expanded=any(
            key == "hope_prefectures"
            or key == "hope_commute_minutes"
            or key.startswith("hope_location_priority_")
            for key in errors
        ),
    ):
        st.write(
            "希望勤務地や通勤時間、"
            "転勤の可否を入力してください。"
        )

        selected_prefectures = st.multiselect(
            required_input_label("希望都道府県（最大2件）"),
            options=PREFECTURES,
            max_selections=2,
            key="hope_prefectures",
        )
        render_hope_field_error(errors, "hope_prefectures")

        for rank, prefecture in enumerate(
            selected_prefectures,
            start=1,
        ):
            with st.container(border=True):
                st.markdown(
                    '<span class="metea-location-card-marker" '
                    'aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{rank}. {prefecture}**")

                location_columns = st.columns([3, 2])

                with location_columns[0]:
                    st.text_input(
                        "希望市区町村（任意・複数入力可）",
                        placeholder=(
                            "例）福岡市中央区、福岡市博多区"
                        ),
                        key=f"hope_city_{rank}_{prefecture}",
                    )
                    st.caption(
                        "複数入力する場合は「、」で区切ってください。"
                        "未入力の場合は県内全域を希望として扱います。"
                    )

                with location_columns[1]:
                    render_priority_select(
                        required_input_label("勤務地の優先度"),
                        key=(
                            f"hope_location_priority_"
                            f"{rank}_{prefecture}"
                        ),
                        default="want",
                        priority_labels=(
                            PRIORITY_LABELS_WITHOUT_NO_PREFERENCE
                        ),
                    )
                    render_hope_field_error(
                        errors,
                        f"hope_location_priority_{rank}_{prefecture}",
                    )

        commute_columns = st.columns(2)

        with commute_columns[0]:
            st.number_input(
                required_input_label(
                    "片道通勤時間の上限（分）",
                    priority_requires_value("hope_commute_priority"),
                ),
                min_value=0,
                max_value=240,
                value=0,
                step=10,
                key="hope_commute_minutes",
                help="0分の場合は未設定として扱います。",
            )
            render_hope_field_error(errors, "hope_commute_minutes")

        with commute_columns[1]:
            render_priority_select(
                "通勤時間の優先度",
                key="hope_commute_priority",
            )

        transfer_columns = st.columns(2)

        with transfer_columns[0]:
            transfer_condition = st.selectbox(
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
            if transfer_condition == "こだわらない":
                st.caption(
                    "転勤条件を選択すると優先度を設定できます。"
                )
            else:
                render_priority_select(
                    "転勤条件の優先度",
                    key="hope_transfer_priority",
                    default="want",
                    priority_labels=(
                        PRIORITY_LABELS_WITHOUT_NO_PREFERENCE
                    ),
                )


    # --------------------------------------------------
    # 3. 年収・雇用条件
    # --------------------------------------------------

    with st.expander(
        "3　年収・雇用条件",
        expanded=any(
            key in errors
            for key in (
                "hope_minimum_salary",
                "hope_desired_salary",
                "hope_ideal_salary",
                "hope_employment_types",
            )
        ),
    ):
        st.write(
            "希望する年収と雇用形態を"
            "入力してください。"
        )

        salary_columns = st.columns(3)

        with salary_columns[0]:
            st.number_input(
                required_input_label("最低許容年収（万円）"),
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
            render_hope_field_error(errors, "hope_minimum_salary")

        with salary_columns[1]:
            st.number_input(
                required_input_label("希望年収（万円）"),
                min_value=0,
                max_value=5000,
                value=0,
                step=10,
                key="hope_desired_salary",
            )
            render_hope_field_error(errors, "hope_desired_salary")

        with salary_columns[2]:
            st.number_input(
                "理想年収（万円・任意）",
                min_value=0,
                max_value=5000,
                value=0,
                step=10,
                key="hope_ideal_salary",
            )
            render_hope_field_error(errors, "hope_ideal_salary")

        st.caption(
            "最低許容年収は必須条件、"
            "希望年収は希望条件、"
            "理想年収は上振れ評価として扱います。"
        )

        selected_employment_types = st.multiselect(
            required_input_label("希望する雇用形態"),
            options=EMPLOYMENT_TYPE_OPTIONS,
            key="hope_employment_types",
        )
        render_hope_field_error(errors, "hope_employment_types")

        render_selected_item_priorities(
            selected_employment_types,
            "hope_employment_priority",
        )


    # --------------------------------------------------
    # 4. 勤務時間・休日
    # --------------------------------------------------

    with st.expander(
        "4　勤務時間・休日",
        expanded=any(
            key in errors
            for key in (
                "hope_overtime_limit",
                "hope_holidays",
                "hope_annual_holidays",
            )
        ),
    ):
        st.write(
            "勤務時間や休日に関する希望を"
            "入力してください。"
        )

        overtime_columns = st.columns(2)

        with overtime_columns[0]:
            st.number_input(
                required_input_label(
                    "月間残業時間の上限",
                    priority_requires_value("hope_overtime_priority"),
                ),
                min_value=0,
                max_value=200,
                value=0,
                step=5,
                key="hope_overtime_limit",
                help="0時間の場合は未設定として扱います。",
            )
            render_hope_field_error(errors, "hope_overtime_limit")

        with overtime_columns[1]:
            render_priority_select(
                "残業時間の優先度",
                key="hope_overtime_priority",
            )

        start_time_columns = st.columns(2)

        with start_time_columns[0]:
            start_time = st.selectbox(
                required_input_label(
                    "希望始業時刻",
                    priority_requires_value("hope_start_time_priority"),
                ),
                options=(
                    "こだわらない",
                    "8:00以降",
                    "9:00以降",
                    "10:00以降",
                    "11:00以降",
                ),
                key="hope_start_time",
            )

        with start_time_columns[1]:
            if start_time == "こだわらない":
                st.caption(
                    "希望始業時刻を選択すると"
                    "優先度を設定できます。"
                )
            else:
                render_priority_select(
                    "始業時刻の優先度",
                    key="hope_start_time_priority",
                    default="want",
                    priority_labels=(
                        PRIORITY_LABELS_WITHOUT_NO_PREFERENCE
                    ),
                )

        end_time_columns = st.columns(2)

        with end_time_columns[0]:
            end_time = st.selectbox(
                required_input_label(
                    "希望終業時刻",
                    priority_requires_value("hope_end_time_priority"),
                ),
                options=(
                    "こだわらない",
                    "17:00まで",
                    "18:00まで",
                    "19:00まで",
                    "20:00まで",
                ),
                key="hope_end_time",
            )

        with end_time_columns[1]:
            if end_time == "こだわらない":
                st.caption(
                    "希望終業時刻を選択すると"
                    "優先度を設定できます。"
                )
            else:
                render_priority_select(
                    "終業時刻の優先度",
                    key="hope_end_time_priority",
                    default="want",
                    priority_labels=(
                        PRIORITY_LABELS_WITHOUT_NO_PREFERENCE
                    ),
                )

        st.markdown("**勤務制度**")

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
            shift_work = st.selectbox(
                "シフト勤務",
                options=(
                    "こだわらない",
                    "不可",
                    "条件次第で可",
                    "可",
                ),
                key="hope_shift_work",
            )

            if shift_work == "こだわらない":
                st.caption(
                    "シフト勤務の条件を選択すると"
                    "優先度を設定できます。"
                )
            else:
                render_priority_select(
                    "シフト勤務の優先度",
                    key="hope_shift_work_priority",
                    default="want",
                    priority_labels=(
                        PRIORITY_LABELS_WITHOUT_NO_PREFERENCE
                    ),
                )

        with shift_columns[1]:
            night_work = st.selectbox(
                "夜勤",
                options=(
                    "こだわらない",
                    "不可",
                    "条件次第で可",
                    "可",
                ),
                key="hope_night_work",
            )

            if night_work == "こだわらない":
                st.caption(
                    "夜勤の条件を選択すると"
                    "優先度を設定できます。"
                )
            else:
                render_priority_select(
                    "夜勤の優先度",
                    key="hope_night_work_priority",
                    default="want",
                    priority_labels=(
                        PRIORITY_LABELS_WITHOUT_NO_PREFERENCE
                    ),
                )

        st.multiselect(
            required_input_label(
                "希望する休日",
                priority_requires_value("hope_holiday_priority"),
            ),
            options=HOLIDAY_OPTIONS,
            key="hope_holidays",
        )
        render_hope_field_error(errors, "hope_holidays")

        render_priority_select(
            "休日条件の優先度",
            key="hope_holiday_priority",
        )

        annual_holiday_columns = st.columns(2)

        with annual_holiday_columns[0]:
            st.number_input(
                required_input_label(
                    "希望する年間休日数",
                    priority_requires_value("hope_annual_holiday_priority"),
                ),
                min_value=0,
                max_value=365,
                value=0,
                step=1,
                key="hope_annual_holidays",
                help="0日の場合は未設定として扱います。",
            )
            render_hope_field_error(errors, "hope_annual_holidays")

        with annual_holiday_columns[1]:
            render_priority_select(
                "年間休日数の優先度",
                key="hope_annual_holiday_priority",
            )


    # --------------------------------------------------
    # 5. 働き方・職場環境
    # --------------------------------------------------

    with st.expander("5　働き方・職場環境"):
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

        st.caption(
            "避けたい条件は「希望しない」、"
            "受け入れられない条件は「不可」を選択してください。"
        )

        render_condition_priorities(
            CAREER_CONDITIONS,
            "hope_career",
            priority_labels=CAREER_PRIORITY_LABELS,
        )

        selected_age_groups = st.multiselect(
            "希望する職場の年齢層",
            options=AGE_GROUP_OPTIONS,
            key="hope_age_groups",
        )

        if selected_age_groups:
            render_priority_select(
                "年齢層の優先度",
                key="hope_age_group_priority",
                default="want",
                priority_labels=(
                    PRIORITY_LABELS_WITHOUT_NO_PREFERENCE
                ),
            )
        else:
            st.caption(
                "希望する年齢層を選択すると"
                "優先度を設定できます。"
            )


    # --------------------------------------------------
    # 6. 入社条件
    # --------------------------------------------------

    with st.expander("6　入社条件"):
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

    st.markdown(
        '<span class="metea-hope-expander-boundary" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )



       # --------------------------------------------------
    # 画面下部の操作
    # --------------------------------------------------

    st.divider()

    action_columns = st.columns(3)

    with action_columns[0]:
        if st.button(
            "← 基本情報へ戻る",
            key="hope_conditions_back_bottom",
            use_container_width=True,
        ):
            st.query_params["page"] = "basic_info"
            st.rerun()

    with action_columns[1]:
        if st.button(
            "一時保存",
            key="hope_conditions_temporary_save",
            use_container_width=True,
        ):
            try:
                draft_data = collect_hope_conditions_draft()
                save_hope_conditions_draft(draft_data)

                st.toast("入力内容を一時保存しました。")

            except Exception as error:
                st.error(
                    "一時保存に失敗しました。"
                    f"\n\n{error}"
                )

    with action_columns[2]:
        if st.button(
            "保存して次へ →",
            key="hope_conditions_save",
            use_container_width=True,
            type="primary",
        ):
            try:
                # 基本情報と同様、入力値を下書きへ退避してから検証する。
                draft_data = collect_hope_conditions_draft()
                save_hope_conditions_draft(draft_data)

                validation_errors = validate_hope_conditions()
                st.session_state[ERRORS_KEY] = validation_errors

                if validation_errors:
                    st.rerun()

                hope_condition = build_hope_condition()
                hope_condition_items = (
                    build_hope_condition_items()
                )

                save_hope_conditions_data(
                    hope_condition,
                    hope_condition_items,
                )

                st.session_state[DRAFT_MESSAGE_KEY] = (
                    "希望条件を保存しました。"
                )
                st.session_state[ERRORS_KEY] = {}
                st.query_params["page"] = "work_values"
                st.rerun()

            except Exception as error:
                st.error(
                    "保存に失敗しました。"
                    f"\n\n{error}"
                )

    st.caption(
        "一時保存した内容はSQLiteへ保存されます。"
        "正式保存が完了すると、下書きデータは削除されます。"
    )
