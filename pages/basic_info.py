"""基本情報画面の表示と入力チェックを担当するモジュール。"""

from datetime import date
import streamlit as st

from data.master_data import GENDER_LABELS, PREFECTURES
from models import BasicInfo
from services.basic_info_service import (
    load_basic_info,
    load_basic_info_draft,
    save_basic_info,
    save_basic_info_draft,
    validate_basic_info,
)

SAVED_DATA_KEY = "basic_info"
ERRORS_KEY = "basic_info_errors"
SAVE_MESSAGE_KEY = "basic_info_save_message"

# 入力内容を一時的に保持するための識別名
FAMILY_NAME_KEY = "basic_family_name"
GIVEN_NAME_KEY = "basic_given_name"
GENDER_KEY = "basic_gender"
BIRTH_YEAR_KEY = "basic_birth_year"
BIRTH_MONTH_KEY = "basic_birth_month"
BIRTH_DAY_KEY = "basic_birth_day"
PREFECTURE_KEY = "basic_prefecture"
MUNICIPALITY_KEY = "basic_municipality"

# 入力チェックで作成されたエラーを取得するための識別名
FAMILY_NAME_ERROR_KEY = "family_name"
GIVEN_NAME_ERROR_KEY = "given_name"
GENDER_ERROR_KEY = "gender"
BIRTH_YEAR_ERROR_KEY = "birth_year"
BIRTH_MONTH_ERROR_KEY = "birth_month"
BIRTH_DAY_ERROR_KEY = "birth_day"
BIRTH_DATE_ERROR_KEY = "birth_date"
PREFECTURE_ERROR_KEY = "prefecture"
MUNICIPALITY_ERROR_KEY = "municipality"

# 入力欄の識別名とエラーの識別名を対応付ける
ERROR_KEY_BY_FIELD_KEY = {
    FAMILY_NAME_KEY: FAMILY_NAME_ERROR_KEY,
    GIVEN_NAME_KEY: GIVEN_NAME_ERROR_KEY,
    GENDER_KEY: GENDER_ERROR_KEY,
    BIRTH_YEAR_KEY: BIRTH_YEAR_ERROR_KEY,
    BIRTH_MONTH_KEY: BIRTH_MONTH_ERROR_KEY,
    BIRTH_DAY_KEY: BIRTH_DAY_ERROR_KEY,
    PREFECTURE_KEY: PREFECTURE_ERROR_KEY,
    MUNICIPALITY_KEY: MUNICIPALITY_ERROR_KEY,
}



def build_birth_year_options() -> list[int]:
    """現在年から100年前までの選択肢を作る。"""


    current_year = date.today().year

    return [
        *range(
            current_year,
            current_year - 101,
            -1,
        ),
    ]


def format_gender(value: str | None) -> str:
    """性別の内部値を画面表示へ変換する。"""

    return GENDER_LABELS[value]


def format_year(value: int | None) -> str:
    """年の選択肢を画面表示へ変換する。"""

    if value is None:
        return "選択してください（年）"

    return f"{value}年"


def format_month(value : int | None) -> str:
    """月の選択肢を画面表示へ変換する。"""

    if value is None:
        return "選択してください（月）"

    return f"{value}月"


def format_day(value: int | None) -> str:
    """日の選択肢を画面表示へ変換する。"""

    if value is None:
        return "選択してください（日）"

    return f"{value}日"


def format_prefecture(value: str | None) -> str:
    """都道府県の未選択状態を画面表示へ変換する。"""

    if value is None:
        return "選択してください"

    return value


def build_empty_form_values() -> dict[str, str | int | None]:
    """基本情報画面の初期値を作る。"""

    return {
        FAMILY_NAME_KEY: "",
        GIVEN_NAME_KEY: "",
        GENDER_KEY: None,
        BIRTH_YEAR_KEY: None,
        BIRTH_MONTH_KEY: None,
        BIRTH_DAY_KEY: None,
        PREFECTURE_KEY: None,
        MUNICIPALITY_KEY: "",
    }


def build_current_form_values() -> dict[str, object]:
    """現在の入力欄の値を下書き保存用の辞書へまとめる。"""

    return {
        FAMILY_NAME_KEY: st.session_state.get(FAMILY_NAME_KEY, ""),
        GIVEN_NAME_KEY: st.session_state.get(GIVEN_NAME_KEY, ""),
        GENDER_KEY: st.session_state.get(GENDER_KEY),
        BIRTH_YEAR_KEY: st.session_state.get(BIRTH_YEAR_KEY),
        BIRTH_MONTH_KEY: st.session_state.get(BIRTH_MONTH_KEY),
        BIRTH_DAY_KEY: st.session_state.get(BIRTH_DAY_KEY),
        PREFECTURE_KEY: st.session_state.get(PREFECTURE_KEY),
        MUNICIPALITY_KEY: st.session_state.get(MUNICIPALITY_KEY, ""),
    }


def build_draft_form_values(
    draft_data: dict[str, object],
) -> dict[str, object]:
    """SQLiteの下書きを入力欄の初期値へ変換する。"""

    values: dict[str, object] = build_empty_form_values()

    for key in values:
        if key in draft_data:
            values[key] = draft_data[key]

    return values


def build_saved_form_values(
        saved_data: BasicInfo,
) -> dict[str, str | int | None]:
    """保存済みの基本情報から入力欄の値を作る。"""

    return{
        FAMILY_NAME_KEY: saved_data.family_name,
        GIVEN_NAME_KEY: saved_data.given_name,
        GENDER_KEY: saved_data.gender,
        BIRTH_YEAR_KEY: saved_data.birth_date.year,
        BIRTH_MONTH_KEY: saved_data.birth_date.month,
        BIRTH_DAY_KEY: saved_data.birth_date.day,
        PREFECTURE_KEY: saved_data.prefecture,
        MUNICIPALITY_KEY: saved_data.municipality,
    }


def initialize_basic_info_state() -> None:
    """基本情報画面で使う入力値を初期化する。"""

    saved_data = st.session_state.get(SAVED_DATA_KEY)

    if isinstance(saved_data, BasicInfo):
        defaults = build_saved_form_values(saved_data)
    else:
        draft_data = load_basic_info_draft()

        if draft_data is not None:
            defaults = build_draft_form_values(draft_data)
        else:
            saved_profile = load_basic_info()

            if saved_profile is not None:
                st.session_state[SAVED_DATA_KEY] = saved_profile
                defaults = build_saved_form_values(saved_profile)
            else:
                defaults = build_empty_form_values()

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if ERRORS_KEY not in st.session_state:
        st.session_state[ERRORS_KEY] = {}


def render_error_summary(
    errors: dict[str, str],
) -> None:
    """ページ上部にエラーをまとめて表示する。"""

    if not errors:
        return

    error_lines = [
        "入力内容を確認してください",
        "",
        *[
            f"- {message}"
            for message in errors.values()
        ],
    ]

    st.error("\n".join(error_lines))


def render_field_error(
        errors: dict[str, str],
        field_key: str,
) -> None:
    """指定した入力欄のエラーを表示する。"""

    error_key = ERROR_KEY_BY_FIELD_KEY.get(
        field_key,
        field_key,
    )
    message = errors.get(error_key)

    if message:
        st.markdown(f":red[{message}]")

def render_basic_info_page() -> None:
    """基本情報の入力画面を表示する。"""

    initialize_basic_info_state()

    errors=st.session_state[ERRORS_KEY]

    if st.button("← 戻る",key="basic_back"):
        st.session_state[ERRORS_KEY] = {}
        st.query_params.clear()
        st.rerun()

    st.title("基本情報")
    st.write("あなたについて教えてください")

    st.progress(
        12,
        text="入力の進捗 12%",
    )

    render_error_summary(errors)

    with st.form("basic_info_form"):
        name_columns = st.columns(2)

        with name_columns[0]:
            st.text_input(
                "姓 *",
                key=FAMILY_NAME_KEY,
                placeholder="例）山田",
            )
            render_field_error(
                errors,
                FAMILY_NAME_KEY,
            )

        with name_columns[1]:
            st.text_input(
                "名 *",
                key=GIVEN_NAME_KEY,
                placeholder="例）太郎",
            )
            render_field_error(
                errors,
                GIVEN_NAME_KEY,
            )

        st.selectbox(
            "性別 *",
            options=[
                value
                for value in GENDER_LABELS
                if value is not None
            ],
            index=None,
            format_func=format_gender,
            key=GENDER_KEY,
            placeholder="選択してください",
        )

        render_field_error(
            errors,
            GENDER_KEY,
        )

        st.markdown("**生年月日 :red[*]**")

        birth_columns=st.columns(3)

        with birth_columns[0]:
            st.selectbox(
                "生年月日の年",
                options=build_birth_year_options(),
                index=None,
                placeholder="選択してください（年）",
                format_func=format_year,
                key=BIRTH_YEAR_KEY,
                label_visibility="collapsed",
            )
            render_field_error(
                errors,
                BIRTH_YEAR_KEY,
            )

        with birth_columns[1]:
            st.selectbox(
                "生年月日の月",
                options=[
                    *range(1, 13),
                ],
                index=None,
                placeholder="選択してください（月）",
                format_func=format_month,
                key=BIRTH_MONTH_KEY,
                label_visibility="collapsed",
            )
            render_field_error(
                errors,
                BIRTH_MONTH_KEY,
            )

        with birth_columns[2]:
            st.selectbox(
                "生年月日の日",
                options=[
                    *range(1, 32),
                ],
                index=None,
                placeholder="選択してください（日）",
                format_func=format_day,
                key=BIRTH_DAY_KEY,
                label_visibility="collapsed",
            )
            render_field_error(
                errors,
                BIRTH_DAY_KEY,
            )

        render_field_error(
            errors,
            BIRTH_DATE_ERROR_KEY,
        )

        location_columns = st.columns(2)

        with location_columns[0]:
            st.selectbox(
                "都道府県 *",
                options=[
                    *PREFECTURES,
                ],
                index=None,
                placeholder="選択してください",
                format_func=format_prefecture,
                key=PREFECTURE_KEY,
            )
            render_field_error(
                errors,
                PREFECTURE_KEY,
            )

        with location_columns[1]:
            st.text_input(
                "市区町村 *",
                key=MUNICIPALITY_KEY,
                placeholder="例）福岡市中央区",
            )
            render_field_error(
                errors,
                MUNICIPALITY_KEY,
            )
        submitted = st.form_submit_button(
            "次へ →",
            use_container_width=True,
        )


    if not submitted:
        return

    save_basic_info_draft(
        build_current_form_values(),
    )


    basic_info, validation_errors = validate_basic_info(
        st.session_state[FAMILY_NAME_KEY],
        st.session_state[GIVEN_NAME_KEY],
        st.session_state[GENDER_KEY],
        st.session_state[BIRTH_YEAR_KEY],
        st.session_state[BIRTH_MONTH_KEY],
        st.session_state[BIRTH_DAY_KEY],
        st.session_state[PREFECTURE_KEY],
        st.session_state[MUNICIPALITY_KEY],
    )

    st.session_state[ERRORS_KEY] = validation_errors

    if validation_errors:
        st.rerun()

    assert basic_info is not None

    try:
        save_basic_info(basic_info)
    except Exception:
        st.error(
            "基本情報を保存できませんでした。"
            "入力内容は下書きとして保存されています。"
            "時間をおいて、もう一度「次へ」を押してください。"
        )
        return

    st.session_state[SAVED_DATA_KEY] = basic_info
    st.session_state[ERRORS_KEY] = {}
    st.session_state[SAVE_MESSAGE_KEY] = (
        "基本情報を保存しました。"
        "次の「転職理由」を入力してください。"
    )

    st.query_params["page"] = "job_change_reason"