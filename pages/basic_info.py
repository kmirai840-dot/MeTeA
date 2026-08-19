"""基本情報画面の表示と入力チェックを担当するモジュール。"""

from datetime import date
import streamlit as st

from data.master_data import GENDER_LABELS, PREFECTURES
from pages.self_discovery_theme import apply_self_discovery_theme

from models import BasicInfo
from services.basic_info_service import (
    load_basic_info,
    load_basic_info_draft,
    save_basic_info,
    save_basic_info_draft,
    validate_basic_info,
)

from services.station_search_service import (
    StationSearchError,
    search_station_candidates,
)
from ui.design_system import render_field_error as render_common_field_error
from ui.design_system import render_save_failure, render_validation_summary

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
NEAREST_STATION_KEY = "basic_nearest_station"
NEAREST_STATION_PLACE_ID_KEY = (
    "basic_nearest_station_place_id"
)
STATION_SEARCH_QUERY_KEY = "basic_station_search_query"
STATION_CANDIDATES_KEY = "basic_station_candidates"

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
NEAREST_STATION_ERROR_KEY = "nearest_station"

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
    NEAREST_STATION_KEY: NEAREST_STATION_ERROR_KEY,
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
        NEAREST_STATION_KEY: "",
        NEAREST_STATION_PLACE_ID_KEY: "",
        STATION_SEARCH_QUERY_KEY: "",
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
        NEAREST_STATION_KEY: st.session_state.get(
            NEAREST_STATION_KEY,
            "",
        ),
        NEAREST_STATION_PLACE_ID_KEY: st.session_state.get(
            NEAREST_STATION_PLACE_ID_KEY,
            "",
        ),
        STATION_SEARCH_QUERY_KEY: st.session_state.get(
            STATION_SEARCH_QUERY_KEY,
            "",
        ),
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
        NEAREST_STATION_KEY: saved_data.nearest_station,
        NEAREST_STATION_PLACE_ID_KEY: (
            saved_data.nearest_station_place_id
        ),
        STATION_SEARCH_QUERY_KEY: saved_data.nearest_station,
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

    if STATION_CANDIDATES_KEY not in st.session_state:
        saved_station_name = st.session_state.get(
            NEAREST_STATION_KEY,
            "",
        )
        saved_place_id = st.session_state.get(
            NEAREST_STATION_PLACE_ID_KEY,
            "",
        )

        if saved_station_name and saved_place_id:
            st.session_state[STATION_CANDIDATES_KEY] = [
                {
                    "place_id": saved_place_id,
                    "station_name": saved_station_name,
                    "address_text": "",
                    "display_name": saved_station_name,
                },
            ]
        else:
            st.session_state[STATION_CANDIDATES_KEY] = []


def render_error_summary(
    errors: dict[str, str],
) -> None:
    """ページ上部にエラーをまとめて表示する。"""

    render_validation_summary(errors)


def render_error_field_styles(errors: dict[str, str]) -> None:
    """エラーがある入力欄だけを赤枠で強調する。"""

    error_to_widget_keys = {
        FAMILY_NAME_ERROR_KEY: (FAMILY_NAME_KEY,),
        GIVEN_NAME_ERROR_KEY: (GIVEN_NAME_KEY,),
        GENDER_ERROR_KEY: (GENDER_KEY,),
        BIRTH_YEAR_ERROR_KEY: (BIRTH_YEAR_KEY,),
        BIRTH_MONTH_ERROR_KEY: (BIRTH_MONTH_KEY,),
        BIRTH_DAY_ERROR_KEY: (BIRTH_DAY_KEY,),
        BIRTH_DATE_ERROR_KEY: (BIRTH_YEAR_KEY, BIRTH_MONTH_KEY, BIRTH_DAY_KEY),
        PREFECTURE_ERROR_KEY: (PREFECTURE_KEY,),
        MUNICIPALITY_ERROR_KEY: (MUNICIPALITY_KEY,),
        NEAREST_STATION_ERROR_KEY: (STATION_SEARCH_QUERY_KEY,),
    }
    widget_keys = {
        widget_key
        for error_key, mapped_widget_keys in error_to_widget_keys.items()
        if error_key in errors
        for widget_key in mapped_widget_keys
    }
    if not widget_keys:
        return

    selectors = []
    for widget_key in sorted(widget_keys):
        selectors.extend((
            f'.st-key-{widget_key} input',
            f'.st-key-{widget_key} [data-baseweb="select"] > div',
        ))
    st.markdown(
        "<style>"
        + ",".join(selectors)
        + "{border:1.5px solid #ef4b55 !important;"
          "background:#fffafa !important;"
          "box-shadow:0 0 0 2px rgba(239,75,85,.08) !important;}"
          "</style>",
        unsafe_allow_html=True,
    )


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
        render_common_field_error(message)


def format_station_candidate(
    place_id: str,
) -> str:
    """place_idを駅候補の表示名へ変換する。"""

    candidates = st.session_state.get(
        STATION_CANDIDATES_KEY,
        [],
    )

    for candidate in candidates:
        if candidate["place_id"] == place_id:
            return candidate["display_name"]

    return place_id


def get_selected_station_values() -> tuple[str, str]:
    """選択された駅名とplace_idを取得する。"""

    selected_place_id = st.session_state.get(
        NEAREST_STATION_PLACE_ID_KEY,
        "",
    )
    candidates = st.session_state.get(
        STATION_CANDIDATES_KEY,
        [],
    )

    for candidate in candidates:
        if candidate["place_id"] == selected_place_id:
            return (
                candidate["station_name"],
                candidate["place_id"],
            )

    return "", ""


def render_basic_info_page() -> None:
    """基本情報の入力画面を表示する。"""

    apply_self_discovery_theme(current_step=1)

    st.markdown(
        """
        <span class="metea-basic-page-marker" aria-hidden="true"></span>
        <style>
        /* 基本情報は1画面で主要入力と「次へ」を見渡せる密度に整える。 */
        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker),
        section.main > div.block-container:has(.metea-basic-page-marker) {
            box-sizing: border-box;
            width: calc(100vw - 272px);
            max-width: none;
            height: calc(100dvh - 84px);
            min-height: 620px;
            margin: 66px 28px 18px 244px;
            padding: 12px 34px 14px;
            overflow-x: hidden;
            overflow-y: auto;
            scrollbar-gutter: stable;
            overscroll-behavior: contain;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker) h1 {
            margin-top: 0;
            margin-bottom: 0;
            font-size: clamp(1.9rem, 2.3vw, 2.35rem);
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        > [data-testid="stVerticalBlock"],
        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        > div > [data-testid="stVerticalBlock"] {
            gap: 0.45rem;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker) [data-testid="stProgress"] {
            margin: 2px 0 7px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker) [data-testid="stForm"] {
            padding: 8px 14px 10px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-testid="stForm"] [data-testid="stVerticalBlock"] {
            gap: 0.26rem;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-testid="stTextInput"] input,
        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-baseweb="select"] > div {
            min-height: 36px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-testid="stFormSubmitButton"] > button {
            min-height: 36px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-testid="stWidgetLabel"] p,
        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-testid="stForm"] > div p {
            line-height: 1.25;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-testid="stCaptionContainer"] {
            font-size: 0.8rem !important;
            line-height: 1.35;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
        [data-testid="stButton"] > button {
            min-height: 36px;
        }

        .metea-basic-error-summary {
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

        .metea-basic-error-icon {
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

        .metea-basic-error-summary strong { font-size: 0.95rem; }
        .metea-basic-error-summary ul { margin: 5px 0 0; padding-left: 1.15rem; }
        .metea-basic-error-summary li { margin: 2px 0; font-size: 0.88rem; }
        .metea-basic-field-error {
            display: block;
            min-height: 18px;
            margin: 1px 0 4px !important;
            color: #dc3545 !important;
            font-size: 0.84rem !important;
            font-weight: 650;
            line-height: 1.35 !important;
        }

        [data-testid="stElementContainer"]:has(.metea-basic-field-error) {
            min-height: 23px;
            margin-bottom: 2px;
            overflow: visible;
        }

        /* Streamlitのバージョン差に依存せず「次へ」だけを主要ボタンにする。 */
        [data-testid="stElementContainer"]:has(.metea-basic-next-marker)
        + [data-testid="stElementContainer"] button,
        div:has(> [data-testid="stMarkdownContainer"] .metea-basic-next-marker)
        + div button,
        [class*="st-key-basic_next"] button {
            border-color: var(--metea-blue) !important;
            background: linear-gradient(180deg, #2878ff, #0862f1) !important;
            color: #ffffff !important;
            box-shadow: 0 7px 16px rgba(20, 108, 255, 0.22) !important;
        }

        [data-testid="stElementContainer"]:has(.metea-basic-next-marker)
        + [data-testid="stElementContainer"] button p,
        div:has(> [data-testid="stMarkdownContainer"] .metea-basic-next-marker)
        + div button p,
        [class*="st-key-basic_next"] button p {
            color: #ffffff !important;
        }

        [data-testid="stElementContainer"]:has(.metea-basic-next-marker)
        + [data-testid="stElementContainer"] button:hover,
        div:has(> [data-testid="stMarkdownContainer"] .metea-basic-next-marker)
        + div button:hover,
        [class*="st-key-basic_next"] button:hover {
            border-color: var(--metea-blue-dark) !important;
            background: linear-gradient(180deg, #1e70f5, #0759df) !important;
        }

        @media (max-height: 820px) and (min-width: 1101px) {
            [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker),
            section.main > div.block-container:has(.metea-basic-page-marker) {
                width: calc(100vw - 264px);
                height: calc(100dvh - 58px);
                min-height: 0;
                margin: 48px 20px 10px 244px;
                padding-top: 10px;
                padding-bottom: 10px;
            }
            [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
            [data-testid="stForm"] [data-testid="stVerticalBlock"] {
                gap: 0.2rem;
            }
        }

        /* ステッパーを畳む幅では、利用可能な横幅いっぱいにカードを広げる。 */
        @media (max-width: 1100px) {
            [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker),
            section.main > div.block-container:has(.metea-basic-page-marker) {
                width: calc(100vw - 36px);
                max-width: none;
                height: calc(100dvh - 36px);
                min-height: 0;
                margin: 18px;
                padding: 22px 28px 28px;
            }
        }

        /* スマホはカード内スクロールを使わず、画面全体を自然に縦スクロールする。 */
        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker),
            section.main > div.block-container:has(.metea-basic-page-marker) {
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

            [data-testid="stMainBlockContainer"]:has(.metea-basic-page-marker)
            [data-testid="stForm"] {
                padding: 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    initialize_basic_info_state()

    errors=st.session_state[ERRORS_KEY]

    if st.button("← 戻る",key="basic_back"):
        st.session_state[ERRORS_KEY] = {}
        st.query_params.clear()
        st.rerun()

    st.title("基本情報")
    st.write("あなたについて教えてください")

    st.progress(
        1 / 5,
        text="自分を知る 1 / 5　基本情報",
    )

    render_error_summary(errors)
    render_error_field_styles(errors)

    selected_station_place_id_in_form = (
        st.session_state.get(
            NEAREST_STATION_PLACE_ID_KEY,
            "",
        )
    )

    with st.form("basic_info_form"):
        name_columns = st.columns(2)

        with name_columns[0]:
            st.text_input(
                "姓 :red[*]",
                key=FAMILY_NAME_KEY,
                placeholder="例）山田",
            )
            render_field_error(
                errors,
                FAMILY_NAME_KEY,
            )

        with name_columns[1]:
            st.text_input(
                "名 :red[*]",
                key=GIVEN_NAME_KEY,
                placeholder="例）太郎",
            )
            render_field_error(
                errors,
                GIVEN_NAME_KEY,
            )

        st.selectbox(
            "性別 :red[*]",
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
                "都道府県 :red[*]",
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
                "市区町村 :red[*]",
                key=MUNICIPALITY_KEY,
                placeholder="例）福岡市中央区",
            )
            render_field_error(
                errors,
                MUNICIPALITY_KEY,
            )

        st.markdown("**現在の最寄駅 :red[*]**")

        station_search_columns = st.columns(
            [4, 1],
            vertical_alignment="bottom",
        )

        with station_search_columns[0]:
            st.text_input(
                "駅名",
                key=STATION_SEARCH_QUERY_KEY,
                placeholder="例）博多駅",
                label_visibility="collapsed",
                help=(
                    "駅名を入力して「駅を検索」を押し、"
                    "表示された候補から現在の最寄駅を選択してください。"
                ),
            )

        with station_search_columns[1]:
            station_search_submitted = (
                st.form_submit_button(
                    "駅を検索",
                    use_container_width=True,
                )
            )

        station_candidates = st.session_state.get(
            STATION_CANDIDATES_KEY,
            [],
        )

        if station_candidates:
            station_place_id_options = [
                candidate["place_id"]
                for candidate in station_candidates
            ]

            current_place_id = st.session_state.get(
                NEAREST_STATION_PLACE_ID_KEY,
                "",
            )

            if current_place_id in station_place_id_options:
                station_select_index = (
                    station_place_id_options.index(
                        current_place_id,
                    )
                )
            else:
                station_select_index = 0

            selected_station_place_id_in_form = (
                st.selectbox(
                    "検索結果から最寄駅を選択してください :red[*]",
                    options=station_place_id_options,
                    index=station_select_index,
                    format_func=format_station_candidate,
                )
            )

            st.caption(
                "選択した駅から勤務地の最寄駅までの"
                "電車所要時間をAIマッチングに使用します。"
                "徒歩時間は含みません。"
            )
            st.caption("Powered by Google")
        else:
            st.caption(
                "駅名を入力して「駅を検索」を押してください。"
                "候補が表示されたら、現在の最寄駅を選択します。"
            )

        render_field_error(
            errors,
            NEAREST_STATION_KEY,
        )

        st.markdown(
            '<span class="metea-basic-next-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        submitted = st.form_submit_button(
            "次へ →",
            type="primary",
            use_container_width=True,
            key="basic_next",
        )



    if station_search_submitted:
        search_query = st.session_state.get(
            STATION_SEARCH_QUERY_KEY,
            "",
        ).strip()

        if not search_query:
            st.session_state[STATION_CANDIDATES_KEY] = []
            st.session_state[NEAREST_STATION_KEY] = ""
            st.session_state[
                NEAREST_STATION_PLACE_ID_KEY
            ] = ""
            st.session_state[ERRORS_KEY][
                NEAREST_STATION_ERROR_KEY
            ] = "検索する駅名を入力してください"
            st.rerun()

        try:
            station_candidates = search_station_candidates(
                search_query,
            )
        except StationSearchError as error:
            st.session_state[STATION_CANDIDATES_KEY] = []
            st.session_state[NEAREST_STATION_KEY] = ""
            st.session_state[
                NEAREST_STATION_PLACE_ID_KEY
            ] = ""
            st.session_state[ERRORS_KEY][
                NEAREST_STATION_ERROR_KEY
            ] = str(error)
            st.rerun()

        if not station_candidates:
            st.session_state[STATION_CANDIDATES_KEY] = []
            st.session_state[NEAREST_STATION_KEY] = ""
            st.session_state[
                NEAREST_STATION_PLACE_ID_KEY
            ] = ""
            st.session_state[ERRORS_KEY][
                NEAREST_STATION_ERROR_KEY
            ] = (
                "該当する駅が見つかりませんでした。"
                "駅名を確認して、もう一度検索してください"
            )
            st.rerun()

        st.session_state[STATION_CANDIDATES_KEY] = [
            {
                "place_id": candidate.place_id,
                "station_name": candidate.station_name,
                "address_text": candidate.address_text,
                "display_name": candidate.display_name,
            }
            for candidate in station_candidates
        ]

        first_candidate = station_candidates[0]

        st.session_state[NEAREST_STATION_KEY] = (
            first_candidate.station_name
        )
        st.session_state[
            NEAREST_STATION_PLACE_ID_KEY
        ] = first_candidate.place_id

        st.session_state[ERRORS_KEY].pop(
            NEAREST_STATION_ERROR_KEY,
            None,
        )

        st.rerun()

    if not submitted:
        return

    st.session_state[
        NEAREST_STATION_PLACE_ID_KEY
    ] = selected_station_place_id_in_form

    (
        selected_station_name,
        selected_station_place_id,
    ) = get_selected_station_values()

    st.session_state[NEAREST_STATION_KEY] = (
        selected_station_name
    )

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
        st.session_state[NEAREST_STATION_KEY],
        st.session_state[
            NEAREST_STATION_PLACE_ID_KEY
        ],
    )

    st.session_state[ERRORS_KEY] = validation_errors

    if validation_errors:
        st.rerun()

    assert basic_info is not None

    try:
        save_basic_info(basic_info)
    except Exception:
        render_save_failure(
            "基本情報",
            recovery="入力内容は下書きとして保持されています。時間をおいて、もう一度「次へ」を押してください。",
        )
        return

    st.session_state[SAVED_DATA_KEY] = basic_info
    st.session_state[ERRORS_KEY] = {}
    st.session_state[SAVE_MESSAGE_KEY] = (
        "基本情報を保存しました。"
        "続けて希望条件を入力してください。"
    )

    st.query_params["page"] = "hope_conditions"
    st.rerun()
