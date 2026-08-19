"""求人登録画面。"""

import base64
from dataclasses import asdict
from datetime import (
    date,
    datetime,
    time,
)
from html import escape
from pathlib import Path

import streamlit as st

from pages.job_layout import render_job_navigation
from ui.design_system import render_field_error as render_common_field_error
from ui.design_system import render_validation_summary

from models import Job

from services.job_extraction_service import (
    extract_job_data,
    normalize_job_document_text,
)
from services.career_document_service import (
    extract_text_from_pdf,
)
from services.job_matching_auto_evaluation_service import (
    enqueue_job_evaluation,
)

from services.job_service import (
    DUPLICATE_DIFFERENT_SOURCE,
    DUPLICATE_EXACT,
    DUPLICATE_NONE,
    DUPLICATE_POSSIBLE,
    add_job_source_data,
    compare_jobs,
    create_job_data,
    delete_job_data,
    load_job,
    load_jobs,
    save_job_data,
    update_job_data,
)
from services.current_user_service import get_current_user_id
from services.job_evaluation_service import load_job_application_decisions
from database.repositories.application_repository import get_applications
from database.repositories.draft_repository import (
    delete_draft,
    get_draft,
    save_draft,
)


# ========================================
# セッションキー
# ========================================

JOB_REGISTRATION_MODE_KEY = "job_registration_mode"
JOB_FORM_STEP_KEY = "job_form_step"
JOB_EDIT_ID_KEY = "job_edit_id"
JOB_PENDING_DATA_KEY = "job_pending_data"
JOB_CONFIRM_DATA_KEY = "job_confirm_data"
JOB_COMPLETE_MESSAGE_KEY = "job_complete_message"
JOB_COMPLETE_NOTE_KEY = "job_complete_note"
JOB_COMPLETE_JOB_ID_KEY = "job_complete_job_id"
JOB_DUPLICATE_ID_KEY = "job_duplicate_id"
JOB_DUPLICATE_TYPE_KEY = "job_duplicate_type"
SAME_COMPANY_OTHER_JOB = "same_company_other_job"
JOB_FORM_ERRORS_KEY = "job_form_validation_errors"
JOB_FORM_GENERAL_ERRORS_KEY = "job_form_general_validation_errors"
JOB_SCROLL_TO_ERRORS_KEY = "job_form_scroll_to_errors"
JOB_REGISTRATION_DRAFT_FORM_NAME = "job_registration"
JOB_REGISTRATION_DRAFT_LOADED_KEY = (
    "job_registration_draft_loaded"
)
JOB_REGISTRATION_DRAFT_NOTICE_KEY = (
    "job_registration_draft_notice"
)
JOB_FORM_RETURN_PAGE_KEY = (
    "job_form_return_page"
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def svg_data_uri(filename: str) -> str:
    """ローカルSVGをHTML表示用のdata URIへ変換する。"""

    svg_bytes = (ASSETS_DIR / filename).read_bytes()
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def start_new_job_registration() -> None:
    """新規求人登録を初期状態から開始する。"""

    st.session_state[
        JOB_REGISTRATION_MODE_KEY
    ] = ""

    st.session_state[
        JOB_FORM_STEP_KEY
    ] = "select"

    st.session_state[
        JOB_EDIT_ID_KEY
    ] = None

    st.session_state[
        JOB_PENDING_DATA_KEY
    ] = None

    st.session_state[
        JOB_CONFIRM_DATA_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_MESSAGE_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_NOTE_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_JOB_ID_KEY
    ] = None

    st.session_state[
        JOB_DUPLICATE_ID_KEY
    ] = None

    st.session_state[
        JOB_DUPLICATE_TYPE_KEY
    ] = None

    st.session_state[JOB_FORM_ERRORS_KEY] = {}
    st.session_state[JOB_FORM_GENERAL_ERRORS_KEY] = []
    st.session_state[JOB_SCROLL_TO_ERRORS_KEY] = False


def save_extracted_job_draft(
    extracted_data: dict,
    *,
    show_notice: bool = True,
) -> None:
    """AI抽出結果を正式登録前の求人下書きとして保存する。"""

    save_draft(
        user_id=get_current_user_id(),
        form_name=JOB_REGISTRATION_DRAFT_FORM_NAME,
        draft_data={
            "registration_mode": st.session_state.get(
                JOB_REGISTRATION_MODE_KEY,
                "",
            ),
            "extracted_data": extracted_data,
            "source_text": st.session_state.get(
                "job_registration_text",
                "",
            ),
        },
    )
    st.session_state[JOB_REGISTRATION_DRAFT_LOADED_KEY] = True
    if show_notice:
        st.session_state[JOB_REGISTRATION_DRAFT_NOTICE_KEY] = (
            "AIの読み取り結果を下書き保存しました。"
        )


def restore_extracted_job_draft() -> None:
    """新しいセッションで求人登録のAI抽出下書きを復元する。"""

    if JOB_REGISTRATION_DRAFT_LOADED_KEY in st.session_state:
        return

    st.session_state[JOB_REGISTRATION_DRAFT_LOADED_KEY] = True

    # すでに画面上の求人データがある場合は上書きしない。
    if st.session_state.get(JOB_EDIT_ID_KEY) is not None:
        return

    if any(
        key.startswith("job_form_")
        for key in st.session_state
    ):
        return

    draft_data = get_draft(
        user_id=get_current_user_id(),
        form_name=JOB_REGISTRATION_DRAFT_FORM_NAME,
    )
    if not draft_data:
        return

    extracted_data = draft_data.get("extracted_data")
    if not isinstance(extracted_data, dict):
        return

    apply_new_extracted_job_data(extracted_data)
    st.session_state["job_extracted_data"] = extracted_data
    st.session_state["job_registration_text"] = str(
        draft_data.get("source_text") or ""
    )
    st.session_state[JOB_REGISTRATION_MODE_KEY] = str(
        draft_data.get("registration_mode") or ""
    )
    st.session_state[JOB_FORM_STEP_KEY] = "form"
    st.session_state["job_extraction_completed"] = True
    st.session_state[JOB_REGISTRATION_DRAFT_NOTICE_KEY] = (
        "前回AIで読み取った求人情報の下書きを復元しました。"
    )


SOURCE_TYPES = (
    "選択してください",
    "転職エージェント",
    "求人サイト",
    "企業採用ページ",
    "ハローワーク",
    "スカウト",
    "知人・社員紹介",
    "その他",
)

REQUIRED_JOB_FIELDS = {
    "company_name": "会社名を入力してください",
    "source_type": "紹介経路の種別を選択してください",
    "source_name": "紹介経路の具体名を入力してください",
    "occupation": "募集ポジション（職種）を入力してください",
    "job_summary": "仕事内容・業務概要を入力してください",
}


def clear_job_form_error(field_name: str) -> None:
    """入力を修正した必須項目のエラー表示を解除する。"""

    errors = dict(st.session_state.get(JOB_FORM_ERRORS_KEY, {}))
    errors.pop(field_name, None)
    st.session_state[JOB_FORM_ERRORS_KEY] = errors


def validate_required_job_fields(
    *,
    company_name: str,
    source_type: str,
    source_name: str,
    occupation: str,
    job_summary: str,
) -> dict[str, str]:
    """保存前確認へ進むための必須項目を検証する。"""

    values = {
        "company_name": company_name,
        "source_type": source_type,
        "source_name": source_name,
        "occupation": occupation,
        "job_summary": job_summary,
    }
    errors: dict[str, str] = {}
    for field_name, message in REQUIRED_JOB_FIELDS.items():
        value = str(values.get(field_name) or "").strip()
        if not value or (field_name == "source_type" and value == "選択してください"):
            errors[field_name] = message
    return errors


def render_required_field_error(field_name: str) -> None:
    """必須入力欄の赤枠用マーカーと項目別メッセージを表示する。"""

    message = st.session_state.get(JOB_FORM_ERRORS_KEY, {}).get(field_name)
    if not message:
        return
    st.markdown(
        '<span class="job-field-error-marker"></span>',
        unsafe_allow_html=True,
    )
    render_common_field_error(message)


def render_job_field_error_styles(errors: dict[str, str]) -> None:
    """赤枠を、検証エラーがある必須入力欄だけに適用する。"""

    widget_selectors = {
        "company_name": (
            '.st-key-job_form_company_name '
            '[data-testid="stTextInputRootElement"]'
        ),
        "source_type": (
            '.st-key-job_form_source_type '
            '[data-testid="stSelectbox"] '
            '.react-aria-ComboBox > div'
        ),
        "source_name": (
            '.st-key-job_form_source_name '
            '[data-testid="stTextInputRootElement"]'
        ),
        "occupation": (
            '.st-key-job_form_occupation '
            '[data-testid="stTextInputRootElement"]'
        ),
        "job_summary": (
            '.st-key-job_form_job_summary '
            '[data-testid="stTextAreaRootElement"]'
        ),
    }
    selectors = [
        widget_selectors[field_name]
        for field_name in errors
        if field_name in widget_selectors
    ]

    if not selectors:
        return

    st.markdown(
        "<style>"
        + ",\n".join(selectors)
        + """ {
            border-color: #ef4050 !important;
            box-shadow: 0 0 0 1px #ef4050 !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )


def _format_comma_input(key: str) -> None:
    """金額入力を3桁カンマ表記へ整形する。"""

    raw_value = str(st.session_state.get(key, "") or "")
    digits = raw_value.replace(",", "").strip()
    if not digits:
        st.session_state[key] = ""
        return
    if digits.isdigit():
        st.session_state[key] = f"{int(digits):,}"


def comma_number_input(label: str, key: str, placeholder: str = "") -> int | None:
    """カンマ付きで表示し、数値として返す金額入力欄。"""

    current = st.session_state.get(key)
    if current not in (None, ""):
        digits = str(current).replace(",", "").strip()
        if digits.isdigit():
            st.session_state[key] = f"{int(digits):,}"
    value = st.text_input(
        label,
        key=key,
        placeholder=placeholder,
        on_change=_format_comma_input,
        args=(key,),
    )
    digits = str(value or "").replace(",", "").strip()
    return int(digits) if digits.isdigit() else None

LISTING_STATUSES = (
    "",
    "上場",
    "非上場",
    "不明",
)

EMPLOYMENT_TYPES = (
    "",
    "正社員",
    "契約社員",
    "派遣社員",
    "パート・アルバイト",
    "業務委託",
    "その他",
)

WAGE_TYPES = (
    "",
    "月給制",
    "年俸制",
    "時給制",
    "日給制",
    "その他",
)

SELECTION_STEP_OPTIONS = (
    "",
    "あり",
    "なし",
    "不明",
)

PROBATION_PERIOD_OPTIONS = (
    "",
    "あり",
    "なし",
    "不明",
)

FIXED_OVERTIME_OPTIONS = (
    "",
    "あり",
    "なし",
    "不明",
)

FLEXTIME_OPTIONS = (
    "",
    "あり",
    "なし",
    "条件付き",
    "不明",
)

TRANSFER_OPTIONS = (
    "",
    "あり",
    "なし",
    "条件付き",
    "不明",
)

WORK_STYLE_OPTIONS = (
    "",
    "出社のみ",
    "一部在宅",
    "完全在宅",
    "相談可",
    "不明",
)

PREFECTURES = (
    "",
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
    "海外",
    "勤務地不明",
)


def options_with_current(
    options: tuple[str, ...],
    current_value: str,
) -> tuple[str, ...]:
    """既存の自由記述値を失わず選択肢へ含める。"""

    if (
        current_value
        and current_value not in options
    ):
        return (
            *options,
            current_value,
        )

    return options


def infer_source_type(
    source_name: str,
) -> str:
    """既存の紹介経路名から種別を推定する。"""

    normalized = source_name.strip().casefold()

    if not normalized:
        return "選択してください"

    if "エージェント" in source_name:
        return "転職エージェント"

    if normalized in {
        "indeed",
        "求人ボックス",
        "スタンバイ",
    }:
        return "求人サイト"

    if (
        "採用" in source_name
        or "企業" in source_name
    ):
        return "企業採用ページ"

    if "ハローワーク" in source_name:
        return "ハローワーク"

    if "スカウト" in source_name:
        return "スカウト"

    return "その他"

# ========================================
# CSS
# ========================================

def render_styles() -> None:
    """求人登録画面用のスタイルを表示する。"""

    st.markdown(
        """
        <style>
        .stApp, .stApp button, .stApp input, .stApp textarea,
        .stApp [data-baseweb="select"] {
            font-family: "Noto Sans JP", "Yu Gothic UI", "Yu Gothic",
                "Hiragino Kaku Gothic ProN", sans-serif;
        }

        [data-testid="stAppViewContainer"] {
            background: #f4f7fb;
        }

        .block-container {
            padding-top: 2.1rem;
            width: calc(100% - 32px);
            max-width: 1680px;
        }

        div[data-testid="stVerticalBlock"]:has(
            > [data-testid="stElementContainer"] .job-registration-shell-marker
        ) {
            padding: 28px 30px 30px;
            border: 1px solid #d8e2f0;
            border-radius: 16px;
            background: #ffffff !important;
            box-shadow: 0 10px 28px rgba(30, 67, 116, 0.07);
        }

        .job-registration-shell-marker {
            display: none;
        }

        .job-page-title {
            color: #061b3a;
            font-size: 34px;
            font-weight: 800;
            line-height: 1.35;
            margin-bottom: 4px;
        }

        .job-page-description {
            color: #667085;
            font-size: 15px;
            margin-bottom: 28px;
        }

        .job-section-title {
            color: #061b3a;
            font-size: 20px;
            font-weight: 800;
            margin-top: 12px;
            margin-bottom: 4px;
        }

        .job-section-description {
            color: #667085;
            font-size: 14px;
            margin-bottom: 18px;
        }

        .job-input-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .job-input-description {
            color: #667085;
            font-size: 14px;
            margin-bottom: 14px;
        }

        .job-list-back-link {
            display: inline-flex;
            align-items: center;
            min-height: 38px;
            margin-bottom: 26px;
            padding: 8px 14px;
            border: 1px solid #a9c9ff;
            border-radius: 9px;
            background: #ffffff;
            color: #146cff !important;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.4;
            text-decoration: none !important;
            box-shadow: 0 2px 7px rgba(20, 108, 255, 0.04);
            transition: background .16s ease, border-color .16s ease,
                transform .16s ease;
        }

        .job-list-back-link:hover {
            border-color: #72a6ff;
            background: #eef5ff;
            color: #0759df !important;
            text-decoration: none !important;
            transform: translateY(-1px);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px;
            background-color: #ffffff !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]
        > div,
        div[data-testid="stVerticalBlockBorderWrapper"]
        div[data-testid="stVerticalBlock"] {
            background-color: #ffffff !important;
        }

        div[data-testid="stVerticalBlock"]:has(
            > [data-testid="stElementContainer"] h3
        ) {
            background-color: #ffffff !important;
        }

        .job-source-required-note {
            margin: 6px 0 14px;
            padding: 14px 16px;
            border: 1px solid #b8d2ff;
            border-radius: 11px;
            background: #f3f7ff;
            color: #24466f;
            font-size: 13px;
            line-height: 1.7;
        }

        .job-source-required-note strong {
            display: block;
            margin-bottom: 2px;
            color: #075ee8;
            font-size: 14px;
        }

        .job-validation-summary {
            display: flex;
            gap: 12px;
            margin: 6px 0 18px;
            padding: 15px 17px;
            border: 1px solid #ff9aa5;
            border-radius: 11px;
            background: #fff5f6;
            color: #d92d3a;
        }

        .job-validation-summary > span {
            display: grid;
            place-items: center;
            flex: 0 0 23px;
            width: 23px;
            height: 23px;
            border: 2px solid #ef4050;
            border-radius: 50%;
            font-weight: 800;
        }

        .job-validation-summary strong {
            display: block;
            margin-bottom: 5px;
        }

        .job-validation-summary ul {
            margin: 0;
            padding-left: 20px;
        }

        .job-field-error-marker { display: none; }

        .job-field-error-message {
            margin-top: -9px;
            margin-bottom: 8px;
            color: #e02f3f;
            font-size: 12px;
            font-weight: 700;
        }

        .job-progress {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 8px;
            margin: 18px 0 28px;
        }

        .job-progress-item {
            position: relative;
            display: flex;
            align-items: center;
            gap: 8px;
            min-height: 42px;
            padding: 8px 10px;
            border-radius: 10px;
            background: #f4f7fb;
            color: #7b879b;
            font-size: 12px;
            font-weight: 700;
        }

        .job-progress-item.is-active {
            background: #eaf2ff;
            color: #075ee8;
        }

        .job-progress-item.is-complete {
            background: #f0f6ff;
            color: #3974cc;
        }

        .job-progress-number {
            display: grid;
            place-items: center;
            flex: 0 0 24px;
            width: 24px;
            height: 24px;
            border: 1px solid #cbd7e8;
            border-radius: 50%;
            background: #fff;
        }

        .job-progress-item.is-active .job-progress-number {
            border-color: #1f6fff;
            background: #1f6fff;
            color: #fff;
        }

        .job-complete-content {
            max-width: 780px;
            margin: 18px auto 4px;
            text-align: center;
        }

        .job-complete-icon {
            display: grid;
            place-items: center;
            width: 72px;
            height: 72px;
            margin: 0 auto 18px;
            border-radius: 22px;
            background: #eaf2ff;
            box-shadow: inset 0 0 0 1px #d6e5ff;
        }

        .job-complete-icon img {
            width: 38px;
            height: 38px;
        }

        .job-complete-title {
            margin: 0;
            color: #061b3a;
            font-size: 30px;
            font-weight: 800;
            line-height: 1.4;
        }

        .job-complete-description {
            margin: 10px 0 0;
            color: #667085;
            font-size: 15px;
            line-height: 1.8;
        }

        .job-complete-status {
            display: flex;
            align-items: flex-start;
            gap: 14px;
            max-width: 700px;
            margin: 26px auto 22px;
            padding: 18px 20px;
            border: 1px solid #bdd5ff;
            border-radius: 12px;
            background: #f1f6ff;
            text-align: left;
        }

        .job-complete-status-mark {
            position: relative;
            flex: 0 0 18px;
            width: 18px;
            height: 18px;
            margin-top: 2px;
            border: 2px solid #1f6fff;
            border-radius: 50%;
        }

        .job-complete-status-mark::after {
            position: absolute;
            top: 3px;
            left: 3px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #1f6fff;
            content: "";
        }

        .job-complete-status strong {
            display: block;
            margin-bottom: 4px;
            color: #075ee8;
            font-size: 14px;
        }

        .job-complete-status span {
            color: #475467;
            font-size: 13px;
            line-height: 1.7;
        }

        .job-complete-id {
            display: inline-flex;
            align-items: center;
            min-height: 28px;
            margin-bottom: 20px;
            padding: 4px 11px;
            border-radius: 999px;
            background: #f4f7fb;
            color: #7b879b;
            font-size: 12px;
            font-weight: 700;
        }

        div[data-testid="stVerticalBlock"]:has(
            > [data-testid="stElementContainer"] .job-complete-actions-marker
        ) {
            max-width: 700px;
            margin: 0 auto;
        }

        .job-complete-actions-marker {
            display: none;
        }

        .job-method-heading {
            margin-bottom: 18px;
            padding-left: 14px;
            border-left: 4px solid #1f6fff;
        }

        .job-method-heading strong {
            display: block;
            color: #061b3a;
            font-size: 19px;
            margin-bottom: 3px;
        }

        .job-method-heading span {
            color: #667085;
            font-size: 13px;
        }

        .job-method-icon {
            width: 48px;
            height: 48px;
            display: grid;
            place-items: center;
            margin-bottom: 12px;
            border-radius: 14px;
            background: #eaf2ff;
        }

        .job-method-icon.manual { background: #fff3e8; }
        .job-method-icon img { width: 34px; height: 34px; }

        .job-method-label {
            min-height: 108px;
        }

        div[data-testid="stVerticalBlock"]:has(
            > [data-testid="stElementContainer"] .job-method-selected
        ) {
            position: relative;
            border-color: #1f6fff;
            background: #f5f9ff;
            box-shadow: 0 8px 22px rgba(31, 111, 255, 0.10);
        }

        .job-method-selected {
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 2;
            display: flex;
            align-items: center;
            gap: 6px;
            width: fit-content;
            margin: 0;
            padding: 4px 9px;
            border-radius: 999px;
            background: #e6f0ff;
            color: #075ee8;
            font-size: 11px;
            font-weight: 800;
        }

        .job-method-selected::before {
            content: "";
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #1f6fff;
        }

        .job-selected-source-heading {
            margin-top: 22px;
            padding: 14px 16px;
            border: 1px solid #a9c9ff;
            border-radius: 11px;
            background: #edf5ff;
            color: #12345f;
        }

        .job-selected-source-heading strong {
            display: block;
            margin-bottom: 3px;
            color: #075ee8;
            font-size: 15px;
        }

        .job-selected-source-heading span {
            font-size: 13px;
        }

        .job-method-title {
            color: #061b3a;
            font-size: 18px;
            font-weight: 800;
            margin: 0 0 8px;
        }

        .job-method-label p {
            color: #667085;
            font-size: 13px;
            line-height: 1.7;
            margin: 0;
        }

        .job-method-label--compact {
            min-height: 118px;
        }

        .job-method-label--compact .job-method-title {
            min-height: 44px;
            font-size: 15px;
            line-height: 1.45;
        }

        .job-method-label--compact p {
            min-height: 58px;
            font-size: 12px;
            line-height: 1.6;
        }

        .job-recommended {
            display: inline-flex;
            margin-left: 7px;
            padding: 3px 8px;
            border: 1px solid #8bb6ff;
            border-radius: 999px;
            background: #fff;
            color: #075ee8;
            font-size: 11px;
            vertical-align: 2px;
        }

        .job-secondary-methods-title {
            margin: 18px 0 10px;
            color: #42526a;
            font-size: 13px;
            font-weight: 800;
        }

        .job-secondary-methods-note {
            margin-left: 6px;
            color: #8a96a8;
            font-weight: 500;
        }

        .job-flow-panel {
            margin-top: 18px;
            padding: 16px 18px;
            border: 1px solid #cfe0fb;
            border-radius: 12px;
            background: #f7faff;
            color: #42526a;
            font-size: 13px;
            line-height: 1.75;
        }

        .job-method-guide {
            transform: translateX(-10mm);
            padding: 20px 18px;
            border: 1px dashed #9fc2f7;
            border-radius: 14px;
            background: #ffffff;
            box-shadow: 0 8px 22px rgba(30, 67, 116, 0.06);
        }

        .job-method-guide-title {
            display: flex;
            align-items: center;
            gap: 9px;
            margin-bottom: 12px;
            color: #075ee8;
            font-size: 16px;
            font-weight: 800;
        }

        .job-method-guide-title::before {
            content: "";
            width: 10px;
            height: 10px;
            border-radius: 2px;
            background: #1f6fff;
        }

        .job-method-guide-list {
            margin-bottom: 16px;
            color: #42526a;
            font-size: 11.5px;
            line-height: 1.8;
            white-space: nowrap;
        }

        .job-method-guide-step {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 11px;
            border: 1px solid #d9e3f1;
            border-radius: 10px;
            background: #ffffff;
            color: #274365;
            font-size: 12px;
            font-weight: 700;
            box-shadow: 0 2px 6px rgba(31, 78, 140, 0.04);
        }

        .job-method-guide-step img {
            flex: 0 0 23px;
            width: 23px;
            height: 23px;
            object-fit: contain;
        }

        .job-method-guide-arrow {
            position: relative;
            width: 2px;
            height: 18px;
            margin: 2px auto;
            background: #9ebce8;
        }

        .job-method-guide-arrow::after {
            content: "";
            position: absolute;
            left: 50%;
            bottom: -1px;
            width: 6px;
            height: 6px;
            border-right: 2px solid #7aa7ea;
            border-bottom: 2px solid #7aa7ea;
            transform: translateX(-50%) rotate(45deg);
        }

        .job-flow-panel strong {
            color: #12345f;
        }

        .job-url-note {
            position: relative;
            margin: 0 0 18px;
            padding: 15px 18px 15px 48px;
            border: 1px solid #f3bd78;
            border-radius: 12px;
            background: #fff8ed;
            color: #71491c;
            font-size: 13px;
            line-height: 1.75;
            box-shadow: 0 4px 12px rgba(202, 123, 31, 0.06);
        }

        .job-url-note::before {
            content: "!";
            position: absolute;
            top: 16px;
            left: 17px;
            display: grid;
            place-items: center;
            width: 20px;
            height: 20px;
            border: 2px solid #e98a22;
            border-radius: 50%;
            color: #d97400;
            font-size: 13px;
            font-weight: 900;
            line-height: 1;
        }

        .job-url-note strong {
            color: #a85400;
            font-size: 14px;
        }

        .job-source-layout {
            margin-top: 22px;
        }

        .job-flow-step {
            margin: 8px 0;
            padding: 9px 12px;
            border: 1px solid #d9e5f7;
            border-radius: 9px;
            background: #fff;
            color: #274365;
            font-weight: 700;
            text-align: center;
        }

        .job-flow-arrow {
            position: relative;
            width: 2px;
            height: 14px;
            margin: 3px auto;
            background: #9ebce8;
        }

        .job-flow-arrow::after {
            content: "";
            position: absolute;
            left: 50%;
            bottom: -1px;
            width: 6px;
            height: 6px;
            border-right: 2px solid #7aa7ea;
            border-bottom: 2px solid #7aa7ea;
            transform: translateX(-50%) rotate(45deg);
        }

        @media (max-width: 900px) {
            .job-progress { grid-template-columns: 1fr; }
            .job-method-label { min-height: auto; }
            div[data-testid="stVerticalBlock"]:has(
                > [data-testid="stElementContainer"] .job-registration-shell-marker
            ) {
                padding: 20px 16px;
            }
            .job-method-guide-list { white-space: normal; }
            .job-method-guide { transform: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ========================================
# 登録方法選択
# ========================================

def render_registration_progress(
    active_step: int,
) -> None:
    """求人登録の5段階を共通表示する。"""

    labels = (
        "登録方法の選択",
        "求人情報の準備",
        "求人情報の入力",
        "登録内容の確認",
        "登録完了",
    )
    items = []

    for index, label in enumerate(labels, start=1):
        state_class = (
            "is-active"
            if index == active_step
            else "is-complete"
            if index < active_step
            else ""
        )
        items.append(
            f'<div class="job-progress-item {state_class}">'
            f'<span class="job-progress-number">{index}</span>'
            f'<span>{label}</span></div>'
        )

    st.markdown(
        f'<div class="job-progress">{"".join(items)}</div>',
        unsafe_allow_html=True,
    )


def select_registration_mode(mode: str) -> None:
    """登録方式を選択し、入力欄を同一画面に展開する。"""

    st.session_state[JOB_REGISTRATION_MODE_KEY] = mode
    st.session_state[JOB_FORM_STEP_KEY] = "select"
    st.rerun()


def render_method_selection() -> None:
    """利用頻度で整理した4種類の登録方法を表示する。"""

    st.markdown(
        """
        <div class="job-method-heading">
            <strong>求人情報をどの方法で登録しますか？</strong>
            <span>選んだ方法の入力欄が、この画面の下に表示されます。AIが整理した内容は、保存前に確認・修正できます。</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_mode = st.session_state.get(
        JOB_REGISTRATION_MODE_KEY,
        "",
    )

    pdf_col, text_col, url_col, manual_col = st.columns(
        [1.25, 1.25, 0.85, 0.85],
        gap="small",
    )

    # ------------------------
    # PDFアップロード（推奨）
    # ------------------------

    with pdf_col:
        with st.container(border=True):
            if selected_mode == "pdf":
                st.markdown(
                    '<div class="job-method-selected">選択中</div>',
                    unsafe_allow_html=True,
                )
            st.image("assets/job-pdf.svg", width=48)
            st.markdown(
                """
                <div class="job-method-label">
                    <div class="job-method-title">求人票をアップロード<span class="job-recommended">おすすめ</span></div>
                    <p>PDFの求人票を読み込み、AIが必要な情報を整理します。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "この方法を選ぶ",
                key="select_job_pdf",
                type="primary",
                use_container_width=True,
            ):
                select_registration_mode("pdf")

    # ------------------------
    # 貼り付け（推奨）
    # ------------------------

    with text_col:
        with st.container(border=True):
            if selected_mode == "text":
                st.markdown(
                    '<div class="job-method-selected">選択中</div>',
                    unsafe_allow_html=True,
                )
            st.image("assets/job-paste.svg", width=48)
            st.markdown(
                """
                <div class="job-method-label">
                    <div class="job-method-title">求人票を貼り付け</div>
                    <p>求人票の本文を貼り付けると、AIが必要な情報を整理します。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "この方法を選ぶ",
                key="select_job_text",
                type="primary",
                use_container_width=True,
            ):
                select_registration_mode("text")

    # ------------------------
    # URL（補助方法）
    # ------------------------

    with url_col:
        with st.container(border=True):
            if selected_mode == "url":
                st.markdown(
                    '<div class="job-method-selected">選択中</div>',
                    unsafe_allow_html=True,
                )
            st.image("assets/job-url.svg", width=40)
            st.markdown(
                """
                <div class="job-method-label job-method-label--compact">
                    <div class="job-method-title">求人URLから登録</div>
                    <p>公開求人ページからAIが情報を取得します。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "この方法を選ぶ",
                key="select_job_url",
                type="primary",
                use_container_width=True,
            ):
                select_registration_mode("url")

    # ------------------------
    # 手動（補助方法）
    # ------------------------

    with manual_col:
        with st.container(border=True):
            if selected_mode == "manual":
                st.markdown(
                    '<div class="job-method-selected">選択中</div>',
                    unsafe_allow_html=True,
                )
            st.image("assets/job-manual.svg", width=40)
            st.markdown(
                """
                <div class="job-method-label job-method-label--compact">
                    <div class="job-method-title">手動で入力</div>
                    <p>確認しながら必要な情報を入力します。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "入力を始める",
                key="select_job_manual",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[JOB_REGISTRATION_MODE_KEY] = "manual"
                st.session_state[JOB_FORM_STEP_KEY] = "form"
                st.session_state["job_extraction_completed"] = False
                st.rerun()

    if selected_mode in {"pdf", "text", "url"}:
        selected_label = (
            "求人票をアップロード"
            if selected_mode == "pdf"
            else "求人票を貼り付け"
            if selected_mode == "text"
            else "求人URLから登録"
        )
        st.markdown(
            f"""
            <div class="job-selected-source-heading">
                <strong>{selected_label}を選択しました</strong>
                <span>続けて、下の入力欄から求人情報を登録してください。</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="job-source-layout"></div>',
            unsafe_allow_html=True,
        )
        if selected_mode == "pdf":
            render_pdf_registration()
        elif selected_mode == "text":
            render_text_registration()
        else:
            render_url_registration()


def render_registration_method_guide() -> None:
    """登録方法の違いと、AI処理後の流れを表示する。"""

    input_icon = svg_data_uri("job-paste.svg")
    ai_icon = svg_data_uri("sparkle.svg")
    review_icon = svg_data_uri("review-basic.svg")
    save_icon = svg_data_uri("value-check.svg")

    st.markdown(
        f"""
        <div class="job-method-guide">
            <div class="job-method-guide-title">登録方法の違い</div>
            <div class="job-method-guide-list">
                ・PDFをアップロード：求人票ファイルから抽出<br>
                ・URLから登録：公開Webページから自動取得<br>
                ・求人票を貼り付け：求人票の文章から抽出<br>
                ・手動入力：AIで取得できない情報を手入力
            </div>
            <div class="job-method-guide-step">
                <img src="{input_icon}" alt="">
                <span>アップロード・貼り付け・入力</span>
            </div>
            <div class="job-method-guide-arrow"></div>
            <div class="job-method-guide-step">
                <img src="{ai_icon}" alt="">
                <span>AIで情報を取得・抽出</span>
            </div>
            <div class="job-method-guide-arrow"></div>
            <div class="job-method-guide-step">
                <img src="{review_icon}" alt="">
                <span>AI抽出結果の確認・修正</span>
            </div>
            <div class="job-method-guide-arrow"></div>
            <div class="job-method-guide-step">
                <img src="{save_icon}" alt="">
                <span>登録内容の確認・保存</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ========================================
# PDF入力
# ========================================

def render_pdf_registration() -> None:
    """テキストを取得できるPDF求人票の入力欄を表示する。"""

    with st.container(border=True):
        st.markdown(
            """
            <div class="job-input-title">求人票をアップロード</div>
            <div class="job-input-description">
                1求人分のPDFを選択してください。読み取り後に内容を確認・修正できます。
            </div>
            <div class="job-url-note">
                <strong>PDFの文字情報について</strong><br>
                <span>
                    画像として保存・スキャンされたPDFは読み取れません。
                    文字を選択・コピーできる状態のPDFをご利用ください。
                    文字を選択できない場合は、求人票の本文をコピーして「求人票を貼り付け」をご利用ください。
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "PDF求人票",
            type=["pdf"],
            key="job_registration_pdf",
            help="テキストを選択できるPDFに対応しています。上限は10MBです。",
        )
        st.caption(
            "対応形式：PDF（1ファイル1求人・10MBまで）"
        )

        if st.button(
            "PDFから求人情報を抽出する",
            key="job_registration_pdf_button",
            type="primary",
            use_container_width=True,
        ):
            if uploaded_file is None:
                st.warning("PDF求人票を選択してください。")
                return

            if uploaded_file.size > 10 * 1024 * 1024:
                st.error("ファイルサイズは10MB以下にしてください。")
                return

            try:
                with st.spinner("PDFから求人情報を読み取っています..."):
                    extracted_text = extract_text_from_pdf(uploaded_file)
            except Exception as error:
                st.error(
                    "PDFを読み取れませんでした。破損していないファイルか確認し、もう一度お試しください。"
                )
                st.caption(f"エラー内容：{error}")
                return

            if not extracted_text.strip():
                st.error(
                    "PDFから文字情報を読み取れませんでした。文字を選択・コピーできるPDFへ変換するか、求人票の本文を貼り付けてください。"
                )
                return

            try:
                with st.spinner("AIが求人票の情報を整理しています..."):
                    extracted_text = normalize_job_document_text(extracted_text)
                    extracted_data = extract_job_data(extracted_text)
            except Exception as error:
                st.error(
                    "求人票のAI抽出に失敗しました。API設定を確認して、もう一度お試しください。"
                )
                st.caption(f"エラー内容：{error}")
                return

            apply_new_extracted_job_data(extracted_data)
            st.session_state["job_extracted_data"] = extracted_data
            st.session_state["job_registration_text"] = extracted_text
            save_extracted_job_draft(extracted_data)
            st.session_state[JOB_FORM_STEP_KEY] = "form"
            st.session_state["job_extraction_completed"] = True
            st.rerun()


# ========================================
# URL入力
# ========================================

def render_url_registration() -> None:
    """URL入力欄を表示する。"""

    with st.container(border=True):

        st.markdown(
            """
            <div class="job-input-title">
                求人URLから登録
            </div>
            <div class="job-input-description">
                求人ページのURLを入力してください。
            </div>
            <div class="job-url-note">
                <strong>URLから登録できる求人について</strong><br>
                URLから読み込めるのは、企業の採用ページなど、ログインせずに閲覧できる公開求人ページです。<br>
                会員登録・ログインが必要な求人サイトや、アクセスが制限されているページは読み込めない場合があります。<br>
                その場合は、求人票の本文をコピーして「求人票を貼り付け」をご利用ください。
            </div>
            """,
            unsafe_allow_html=True,
        )

        job_url = st.text_input(
            "求人URL",
            placeholder="https://example.com/jobs/...",
            key="job_registration_url",
        )

        if st.button(
            "求人URLから情報を取得する",
            key="job_registration_url_button",
            type="primary",
            use_container_width=True,
        ):
            if not job_url.strip():
                st.warning(
                    "求人URLを入力してください。"
                )
            else:
                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "form"

                st.rerun()



def apply_extracted_job_data(
    extracted_data: dict,
) -> None:
    """AI抽出結果を共通フォームへ反映する。"""

    text_field_map = {
        "company_name": "job_form_company_name",
        "job_title": "job_form_job_title",
        "job_number": "job_form_job_number",
        "industry": "job_form_industry",
        "business_description": (
            "job_form_business_description"
        ),
        "established_date": (
            "job_form_established_date"
        ),
        "capital": "job_form_capital",
        "listing_status": (
            "job_form_listing_status"
        ),
        "occupation": "job_form_occupation",
        "department": "job_form_department",
        "recruitment_reason": (
            "job_form_recruitment_reason"
        ),
        "job_summary": "job_form_job_summary",
        "responsibility_scope": (
            "job_form_responsibility_scope"
        ),
        "customers": "job_form_customers",
        "internal_stakeholders": (
            "job_form_internal_stakeholders"
        ),
        "external_partners": (
            "job_form_external_partners"
        ),
        "goals_kpi": "job_form_goals_kpi",
        "expected_results": (
            "job_form_expected_results"
        ),
        "organizational_culture": (
            "job_form_organizational_culture"
        ),
        "employment_type": (
            "job_form_employment_type"
        ),
        "probation_period_status": (
            "job_form_probation_period_status"
        ),
        "probation_period": (
            "job_form_probation_period"
        ),
        "prefecture": "job_form_prefecture",
        "municipality": "job_form_municipality",
        "nearest_station": (
            "job_form_nearest_station"
        ),
        "transfer_required": (
            "job_form_transfer_required"
        ),
        "work_style": "job_form_work_style",
        "flextime": "job_form_flextime",
        "holidays": "job_form_holidays",
        "wage_type": "job_form_wage_type",
        "fixed_overtime_system": (
            "job_form_fixed_overtime_system"
        ),
        "overtime_extra_pay": (
            "job_form_overtime_extra_pay"
        ),
        "bonus": "job_form_bonus",
        "salary_increase": (
            "job_form_salary_increase"
        ),
        "incentive": "job_form_incentive",
        "social_insurance": (
            "job_form_social_insurance"
        ),
        "commuting_allowance": (
            "job_form_commuting_allowance"
        ),
        "housing_allowance": (
            "job_form_housing_allowance"
        ),
        "retirement_plan": (
            "job_form_retirement_plan"
        ),
        "qualification_support": (
            "job_form_qualification_support"
        ),
        "training_program": (
            "job_form_training_program"
        ),
        "document_screening_status": (
            "job_form_document_screening_status"
        ),
        "document_screening": (
            "job_form_document_screening"
        ),
        "interview": "job_form_interview",
        "aptitude_test_status": (
            "job_form_aptitude_test_status"
        ),
        "aptitude_test": (
            "job_form_aptitude_test"
        ),
        "expected_join_date": (
            "job_form_expected_join_date"
        ),
    }

    for (
        field_name,
        form_key,
    ) in text_field_map.items():
        extracted_value = extracted_data.get(
            field_name,
            "",
        )

        st.session_state[form_key] = str(
            extracted_value or ""
        ).strip()

    list_field_map = {
        "job_details": "job_form_job_details",
        "required_experience": (
            "job_form_required_experience"
        ),
        "required_skills": (
            "job_form_required_skills"
        ),
        "required_qualifications": (
            "job_form_required_qualifications"
        ),
        "preferred_experience": (
            "job_form_preferred_experience"
        ),
        "preferred_skills": (
            "job_form_preferred_skills"
        ),
        "desired_personality": (
            "job_form_desired_personality"
        ),
        "not_listed_fields": (
            "job_form_not_listed_fields"
        ),
    }

    for (
        field_name,
        form_key,
    ) in list_field_map.items():
        extracted_values = extracted_data.get(
            field_name,
            [],
        )

        if not isinstance(
            extracted_values,
            list,
        ):
            extracted_values = []

        st.session_state[form_key] = "\n".join(
            str(value).strip()
            for value in extracted_values
            if str(value).strip()
        )

    def extracted_integer(
        field_name: str,
    ) -> int | None:
        return parse_integer_value(
            str(
                extracted_data.get(
                    field_name,
                    "",
                )
                or ""
            )
        )

    def apply_optional_integer(
        field_name: str,
        state_key: str,
        checkbox_key: str,
        value_key: str,
    ) -> None:
        extracted_value = extracted_integer(
            field_name
        )

        st.session_state[state_key] = (
            extracted_value
        )

        st.session_state[checkbox_key] = (
            extracted_value is not None
        )

        if extracted_value is not None:
            st.session_state[value_key] = (
                extracted_value
            )
        else:
            st.session_state.pop(
                value_key,
                None,
            )

    employee_count_min = extracted_integer(
        "employee_count_min"
    )

    employee_count_max = extracted_integer(
        "employee_count_max"
    )

    has_employee_count = (
        employee_count_min is not None
        or employee_count_max is not None
    )

    st.session_state[
        "job_form_has_employee_count"
    ] = has_employee_count

    st.session_state[
        "job_form_employee_count_min"
    ] = employee_count_min

    st.session_state[
        "job_form_employee_count_max"
    ] = employee_count_max

    apply_optional_integer(
        "planned_hires",
        "job_form_planned_hires",
        "job_form_has_planned_hires",
        "job_form_planned_hires_value",
    )

    apply_optional_integer(
        "annual_holidays",
        "job_form_annual_holidays",
        "job_form_has_annual_holidays",
        "job_form_annual_holidays_value",
    )

    interview_count_min = extracted_integer(
        "interview_count_min"
    )

    interview_count_max = extracted_integer(
        "interview_count_max"
    )

    has_interview_count = (
        interview_count_min is not None
        or interview_count_max is not None
    )

    st.session_state[
        "job_form_has_interview_count"
    ] = has_interview_count

    st.session_state[
        "job_form_interview_count_min"
    ] = interview_count_min

    st.session_state[
        "job_form_interview_count_max"
    ] = interview_count_max

    st.session_state[
        "job_form_probation_period_months"
    ] = extracted_integer(
        "probation_period_months"
    )

    start_time_value = parse_time_value(
        str(
            extracted_data.get(
                "start_time",
                "",
            )
            or ""
        )
    )

    end_time_value = parse_time_value(
        str(
            extracted_data.get(
                "end_time",
                "",
            )
            or ""
        )
    )

    st.session_state[
        "job_form_start_time"
    ] = start_time_value

    st.session_state[
        "job_form_end_time"
    ] = end_time_value

    break_minutes_value = extracted_integer(
        "break_minutes"
    )

    st.session_state[
        "job_form_has_break_minutes"
    ] = break_minutes_value is not None

    if break_minutes_value is not None:
        st.session_state[
            "job_form_break_minutes_value"
        ] = break_minutes_value
    else:
        st.session_state.pop(
            "job_form_break_minutes_value",
            None,
        )

    scheduled_work_hours_value = parse_hour_value(
        str(
            extracted_data.get(
                "scheduled_work_hours",
                "",
            )
            or ""
        )
    )

    st.session_state[
        "job_form_has_scheduled_work_hours"
    ] = scheduled_work_hours_value is not None

    if scheduled_work_hours_value is not None:
        st.session_state[
            "job_form_scheduled_work_hours_value"
        ] = scheduled_work_hours_value
    else:
        st.session_state.pop(
            "job_form_scheduled_work_hours_value",
            None,
        )

    overtime_value = extracted_integer(
        "overtime"
    )

    st.session_state[
        "job_form_has_overtime"
    ] = overtime_value is not None

    if overtime_value is not None:
        st.session_state[
            "job_form_overtime_value"
        ] = overtime_value
    else:
        st.session_state.pop(
            "job_form_overtime_value",
            None,
        )

    numeric_form_fields = {
        "monthly_salary_min": (
            "job_form_monthly_salary_min"
        ),
        "monthly_salary_max": (
            "job_form_monthly_salary_max"
        ),
        "base_salary_min": (
            "job_form_base_salary_min"
        ),
        "base_salary_max": (
            "job_form_base_salary_max"
        ),
        "expected_salary_min": (
            "job_form_expected_salary_min"
        ),
        "expected_salary_max": (
            "job_form_expected_salary_max"
        ),
        "fixed_overtime_hours": (
            "job_form_fixed_overtime_hours"
        ),
        "fixed_overtime_pay_min": (
            "job_form_fixed_overtime_pay_min"
        ),
        "fixed_overtime_pay_max": (
            "job_form_fixed_overtime_pay_max"
        ),
    }

    for (
        field_name,
        form_key,
    ) in numeric_form_fields.items():
        st.session_state[form_key] = (
            extracted_integer(field_name)
        )


def apply_new_extracted_job_data(
    extracted_data: dict,
) -> None:
    """新しい求人の抽出結果だけでフォームを作り直す。"""

    # 前回確認した求人の値が、今回の未記載項目へ残ることを防ぐ。
    for state_key in tuple(st.session_state.keys()):
        if state_key.startswith("job_form_"):
            st.session_state.pop(state_key, None)

    apply_extracted_job_data(extracted_data)

# ========================================
# 貼り付け入力
# ========================================

def render_text_registration() -> None:
    """求人票本文入力欄を表示する。"""

    with st.container(border=True):

        st.markdown(
            """
            <div class="job-input-title">
                求人票を貼り付け
            </div>
            <div class="job-input-description">
                求人票の文章を貼り付けてください。
            </div>
            """,
            unsafe_allow_html=True,
        )

        job_text = st.text_area(
            "求人票の内容",
            placeholder=(
                "ここに求人票の本文を"
                "貼り付けてください。"
            ),
            height=220,
            key="job_registration_text",
        )

        if st.button(
            "求人票から情報を抽出する",
            key="job_registration_text_button",
            type="primary",
            use_container_width=True,
        ):
            if not job_text.strip():
                st.warning(
                    "求人票の内容を"
                    "貼り付けてください。"
                )
            else:
                try:
                    with st.spinner(
                        "AIが求人票の情報を整理しています..."
                    ):
                        extracted_data = (
                            extract_job_data(
                                normalize_job_document_text(job_text)
                            )
                        )

                except Exception as error:
                    st.error(
                        "求人票のAI抽出に失敗しました。"
                        "入力内容とAPI設定を確認して、"
                        "もう一度お試しください。"
                    )

                    st.caption(
                        f"エラー内容：{error}"
                    )

                    return

                apply_new_extracted_job_data(
                    extracted_data
                )

                st.session_state[
                    "job_extracted_data"
                ] = extracted_data

                save_extracted_job_draft(
                    extracted_data
                )

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "form"

                st.session_state[
                    "job_extraction_completed"
                ] = True

                st.rerun()


# ========================================
# 手動入力
# ========================================


def parse_date_value(
    value: str,
) -> date | None:
    """保存済みの日付文字列を日付へ変換する。"""

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    date_formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
    )

    for date_format in date_formats:
        try:
            return datetime.strptime(
                cleaned_value,
                date_format,
            ).date()

        except ValueError:
            continue

    return None


def date_to_text(
    value: date | None,
) -> str:
    """選択された日付を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return value.isoformat()


def parse_time_value(
    value: str,
) -> time | None:
    """保存済みの時刻文字列を時刻へ変換する。"""

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    time_formats = (
        "%H:%M",
        "%H:%M:%S",
    )

    for time_format in time_formats:
        try:
            return datetime.strptime(
                cleaned_value,
                time_format,
            ).time()

        except ValueError:
            continue

    return None


def time_to_text(
    value: time | None,
) -> str:
    """選択された時刻を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return value.strftime("%H:%M")


def parse_integer_value(
    value: str,
    unit: str = "",
) -> int | None:
    """保存済みの整数文字列を数値へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
    )

    if (
        unit
        and cleaned_value.endswith(unit)
    ):
        cleaned_value = cleaned_value[
            :-len(unit)
        ].strip()

    if not cleaned_value:
        return None

    try:
        return int(cleaned_value)

    except ValueError:
        return None


def integer_to_text(
    value: int | None,
) -> str:
    """入力された整数を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return str(value)


def parse_hour_value(
    value: str,
) -> float | None:
    """保存済みの時間文字列を数値へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
        .replace("　", "")
        .replace(" ", "")
        .replace("時間／日", "")
        .replace("時間/日", "")
        .replace("時間", "")
    )

    if not cleaned_value:
        return None

    try:
        return float(cleaned_value)

    except ValueError:
        return None


def hour_to_text(
    value: float | None,
) -> str:
    """入力された時間を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return f"{value:g}"


def parse_monthly_overtime_hours(
    value: str,
) -> int | None:
    """残業時間の文字列を月平均の整数へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
        .replace("　", "")
        .replace(" ", "")
    )

    removable_texts = (
        "1か月あたり",
        "1ヶ月あたり",
        "月平均",
        "時間程度",
        "時間／月",
        "時間/月",
        "約",
        "平均",
        "月",
        "時間",
    )

    for removable_text in removable_texts:
        cleaned_value = cleaned_value.replace(
            removable_text,
            "",
        )

    if not cleaned_value:
        return None

    try:
        return int(cleaned_value)

    except ValueError:
        return None


def parse_yen_value(
    value: str,
) -> int | None:
    """保存済みの金額を円単位へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
        .replace(" ", "")
    )

    if not cleaned_value:
        return None

    if cleaned_value.endswith("万円"):
        number_text = cleaned_value[:-2]

        try:
            return int(
                float(number_text)
                * 10000
            )

        except ValueError:
            return None

    if cleaned_value.endswith("円"):
        cleaned_value = cleaned_value[:-1]

    try:
        return int(cleaned_value)

    except ValueError:
        return None


def text_to_list(
    value: str,
) -> list[str]:
    """改行区切りの文字列をリストへ変換する。"""

    return [
        line.strip()
        for line in value.splitlines()
        if line.strip()
    ]


def render_registered_jobs() -> None:
    """登録済み求人を表示する。"""

    jobs = load_jobs()

    if not jobs:
        return

    st.markdown(
        """
        <div class="job-section-title">
            登録済み求人
        </div>
        <div class="job-section-description">
            登録済みの求人を選択すると、
            内容を編集できます。
        </div>
        """,
        unsafe_allow_html=True,
    )

    for job_id, job in jobs:
        with st.container(border=True):

            col1, col2, col3 = st.columns(
                [4, 1, 1]
            )

            with col1:
                st.markdown(
                    f"**{job.company_name or '会社名未入力'}**"
                )

                st.caption(
                    job.job_title
                    or "求人名未入力"
                )

            with col2:
                if st.button(
                    "編集",
                    key=f"edit_job_{job_id}",
                    use_container_width=True,
                ):
                    load_job_for_edit(
                        job_id
                    )

                    st.rerun()

            with col3:
                if st.button(
                    "削除",
                    key=f"delete_job_{job_id}",
                    use_container_width=True,
                ):
                    deleted = delete_job_data(
                        job_id
                    )

                    if deleted:
                        st.rerun()
                    else:
                        st.error(
                            "求人を削除できませんでした。"
                        )


def load_job_for_edit(
    job_id: int,
) -> None:
    """登録済み求人を編集フォームへ復元する。"""

    job = load_job(job_id)

    if job is None:
        st.error(
            "編集対象の求人が見つかりませんでした。"
        )
        return

    st.session_state[
        JOB_EDIT_ID_KEY
    ] = job_id

    st.session_state[
        JOB_FORM_STEP_KEY
    ] = "form"

    st.session_state[
        JOB_REGISTRATION_MODE_KEY
    ] = job.registration_method or "manual"

    st.session_state[
        "job_form_company_name"
    ] = job.company_name

    st.session_state[
        "job_form_job_title"
    ] = job.job_title

    st.session_state[
        "job_form_job_number"
    ] = job.job_number

    st.session_state[
        "job_form_publication_start"
    ] = parse_date_value(
        job.publication_start_date
    )

    st.session_state[
        "job_form_publication_end"
    ] = parse_date_value(
        job.publication_end_date
    )

    st.session_state[
        "job_form_industry"
    ] = job.industry

    st.session_state[
        "job_form_business_description"
    ] = job.business_description

    employee_count_min = parse_integer_value(
        job.employee_count_min,
        "名",
    )

    employee_count_max = parse_integer_value(
        job.employee_count_max,
        "名",
    )

    legacy_employee_count = parse_integer_value(
        job.employee_count,
        "名",
    )

    if (
        employee_count_min is None
        and employee_count_max is None
        and legacy_employee_count is not None
    ):
        employee_count_min = legacy_employee_count
        employee_count_max = legacy_employee_count

    st.session_state[
        "job_form_has_employee_count"
    ] = (
        employee_count_min is not None
        or employee_count_max is not None
    )

    st.session_state[
        "job_form_employee_count_min"
    ] = employee_count_min

    st.session_state[
        "job_form_employee_count_max"
    ] = employee_count_max

    st.session_state[
        "job_form_established_date"
    ] = job.established_date

    st.session_state[
        "job_form_capital"
    ] = job.capital

    st.session_state[
        "job_form_listing_status"
    ] = job.listing_status

    st.session_state[
        "job_form_job_summary"
    ] = job.job_summary

    st.session_state[
        "job_form_job_details"
    ] = "\n".join(job.job_details)

    st.session_state[
        "job_form_responsibility_scope"
    ] = job.responsibility_scope

    st.session_state[
        "job_form_customers"
    ] = job.customers

    st.session_state[
        "job_form_internal_stakeholders"
    ] = job.internal_stakeholders

    st.session_state[
        "job_form_external_partners"
    ] = job.external_partners

    st.session_state[
        "job_form_goals_kpi"
    ] = job.goals_kpi

    st.session_state[
        "job_form_expected_results"
    ] = job.expected_results

    st.session_state[
        "job_form_organizational_culture"
    ] = job.organizational_culture

    st.session_state[
        "job_form_occupation"
    ] = job.occupation

    st.session_state[
        "job_form_department"
    ] = job.department

    planned_hires_value = (
        parse_integer_value(
            job.planned_hires,
            "名",
        )
    )

    st.session_state[
        "job_form_planned_hires"
    ] = planned_hires_value

    st.session_state[
        "job_form_has_planned_hires"
    ] = (
        planned_hires_value
        is not None
    )

    if planned_hires_value is not None:
        st.session_state[
            "job_form_planned_hires_value"
        ] = planned_hires_value

    st.session_state[
        "job_form_recruitment_reason"
    ] = job.recruitment_reason

    st.session_state[
        "job_form_source_name"
    ] = job.source_name

    st.session_state[
        "job_form_source_type"
    ] = (
        job.source_type
        or infer_source_type(
            job.source_name
        )
    )

    st.session_state[
        "job_form_employment_type"
    ] = job.employment_type

    probation_period_status = (
        job.probation_period_status
    )

    if (
        not probation_period_status
        and (
            job.probation_period
            or job.probation_period_months
        )
    ):
        probation_period_status = "あり"

    st.session_state[
        "job_form_probation_period_status"
    ] = probation_period_status

    st.session_state[
        "job_form_probation_period_months"
    ] = parse_integer_value(
        job.probation_period_months
    )

    st.session_state[
        "job_form_probation_period"
    ] = job.probation_period

    st.session_state[
        "job_form_prefecture"
    ] = job.prefecture

    st.session_state[
        "job_form_municipality"
    ] = job.municipality

    st.session_state[
        "job_form_nearest_station"
    ] = job.nearest_station

    st.session_state[
        "job_form_transfer_required"
    ] = job.transfer_required

    st.session_state[
        "job_form_work_style"
    ] = job.work_style

    st.session_state[
        "job_form_start_time"
    ] = parse_time_value(
        job.start_time
    )

    st.session_state[
        "job_form_end_time"
    ] = parse_time_value(
        job.end_time
    )

    st.session_state[
        "job_form_break_minutes_legacy"
    ] = job.break_minutes

    break_minutes_value = parse_integer_value(
        job.break_minutes,
        "分",
    )

    st.session_state[
        "job_form_has_break_minutes"
    ] = break_minutes_value is not None

    if break_minutes_value is not None:
        st.session_state[
            "job_form_break_minutes_value"
        ] = break_minutes_value

    st.session_state[
        "job_form_scheduled_work_hours_legacy"
    ] = job.scheduled_work_hours

    scheduled_work_hours_value = parse_hour_value(
        job.scheduled_work_hours
    )

    st.session_state[
        "job_form_has_scheduled_work_hours"
    ] = scheduled_work_hours_value is not None

    if scheduled_work_hours_value is not None:
        st.session_state[
            "job_form_scheduled_work_hours_value"
        ] = scheduled_work_hours_value
    st.session_state[
        "job_form_flextime"
    ] = job.flextime

    st.session_state[
        "job_form_overtime_legacy"
    ] = job.overtime

    overtime_value = parse_monthly_overtime_hours(
        job.overtime
    )

    st.session_state[
        "job_form_has_overtime"
    ] = overtime_value is not None

    if overtime_value is not None:
        st.session_state[
            "job_form_overtime_value"
        ] = overtime_value

    st.session_state[
        "job_form_holidays"
    ] = job.holidays

    annual_holidays_value = (
        parse_integer_value(
            job.annual_holidays,
            "日",
        )
    )

    st.session_state[
        "job_form_annual_holidays"
    ] = annual_holidays_value

    st.session_state[
        "job_form_has_annual_holidays"
    ] = (
        annual_holidays_value
        is not None
    )

    if annual_holidays_value is not None:
        st.session_state[
            "job_form_annual_holidays_value"
        ] = annual_holidays_value

    st.session_state[
        "job_form_wage_type"
    ] = job.wage_type

    monthly_salary_min_value = (
        parse_yen_value(
            job.monthly_salary_min
        )
    )

    if monthly_salary_min_value is None:
        monthly_salary_min_value = (
            parse_yen_value(
                job.monthly_salary
            )
        )

    st.session_state[
        "job_form_monthly_salary_min"
    ] = monthly_salary_min_value

    st.session_state[
        "job_form_monthly_salary_max"
    ] = parse_yen_value(
        job.monthly_salary_max
    )

    st.session_state[
        "job_form_base_salary_min"
    ] = parse_yen_value(
        job.base_salary_min
    )

    st.session_state[
        "job_form_base_salary_max"
    ] = parse_yen_value(
        job.base_salary_max
    )

    st.session_state[
        "job_form_monthly_salary"
    ] = job.monthly_salary

    st.session_state[
        "job_form_annual_salary"
    ] = job.annual_salary

    st.session_state[
        "job_form_expected_salary_min"
    ] = parse_integer_value(
        job.expected_salary_min,
        "万円",
    )

    st.session_state[
        "job_form_expected_salary_max"
    ] = parse_integer_value(
        job.expected_salary_max,
        "万円",
    )

    fixed_overtime_system = (
        job.fixed_overtime_system
    )

    if (
        not fixed_overtime_system
        and (
            job.fixed_overtime_hours
            or job.fixed_overtime_pay
            or job.fixed_overtime_pay_min
            or job.fixed_overtime_pay_max
        )
    ):
        fixed_overtime_system = "あり"

    st.session_state[
        "job_form_fixed_overtime_system"
    ] = fixed_overtime_system

    st.session_state[
        "job_form_fixed_overtime_hours"
    ] = parse_integer_value(
        job.fixed_overtime_hours,
        "時間",
    )

    fixed_overtime_pay_min = (
        job.fixed_overtime_pay_min
        or job.fixed_overtime_pay
    )

    st.session_state[
        "job_form_fixed_overtime_pay_min"
    ] = parse_yen_value(
        fixed_overtime_pay_min
    )

    st.session_state[
        "job_form_fixed_overtime_pay_max"
    ] = parse_yen_value(
        job.fixed_overtime_pay_max
    )

    st.session_state[
        "job_form_overtime_extra_pay"
    ] = job.overtime_extra_pay

    st.session_state[
        "job_form_fixed_overtime_pay"
    ] = job.fixed_overtime_pay

    st.session_state[
        "job_form_bonus"
    ] = job.bonus

    st.session_state[
        "job_form_salary_increase"
    ] = job.salary_increase

    st.session_state[
        "job_form_incentive"
    ] = job.incentive

    st.session_state[
        "job_form_social_insurance"
    ] = job.social_insurance

    st.session_state[
        "job_form_commuting_allowance"
    ] = job.commuting_allowance

    st.session_state[
        "job_form_housing_allowance"
    ] = job.housing_allowance

    st.session_state[
        "job_form_retirement_plan"
    ] = job.retirement_plan

    st.session_state[
        "job_form_qualification_support"
    ] = job.qualification_support

    st.session_state[
        "job_form_training_program"
    ] = job.training_program

    st.session_state[
        "job_form_required_experience"
    ] = "\n".join(
        job.required_experience
    )

    st.session_state[
        "job_form_required_skills"
    ] = "\n".join(
        job.required_skills
    )

    st.session_state[
        "job_form_required_qualifications"
    ] = "\n".join(
        job.required_qualifications
    )

    st.session_state[
        "job_form_preferred_experience"
    ] = "\n".join(
        job.preferred_experience
    )

    st.session_state[
        "job_form_preferred_skills"
    ] = "\n".join(
        job.preferred_skills
    )

    st.session_state[
        "job_form_desired_personality"
    ] = "\n".join(
        job.desired_personality
    )

    st.session_state[
        "job_form_not_listed_fields"
    ] = "\n".join(
        job.not_listed_fields
    )

    document_screening_status = (
        job.document_screening_status
    )

    if (
        not document_screening_status
        and job.document_screening
    ):
        document_screening_status = "あり"

    st.session_state[
        "job_form_document_screening_status"
    ] = document_screening_status

    st.session_state[
        "job_form_document_screening"
    ] = job.document_screening

    st.session_state[
        "job_form_interview"
    ] = job.interview

    aptitude_test_status = (
        job.aptitude_test_status
    )

    if (
        not aptitude_test_status
        and job.aptitude_test
    ):
        aptitude_test_status = "あり"

    st.session_state[
        "job_form_aptitude_test_status"
    ] = aptitude_test_status

    st.session_state[
        "job_form_aptitude_test"
    ] = job.aptitude_test

    interview_count_min = parse_integer_value(
        job.interview_count_min,
        "回",
    )

    interview_count_max = parse_integer_value(
        job.interview_count_max,
        "回",
    )

    legacy_interview_count = parse_integer_value(
        job.interview_count,
        "回",
    )

    if (
        interview_count_min is None
        and interview_count_max is None
        and legacy_interview_count is not None
    ):
        interview_count_min = legacy_interview_count
        interview_count_max = legacy_interview_count

    st.session_state[
        "job_form_has_interview_count"
    ] = (
        interview_count_min is not None
        or interview_count_max is not None
    )

    st.session_state[
        "job_form_interview_count_min"
    ] = interview_count_min

    st.session_state[
        "job_form_interview_count_max"
    ] = interview_count_max

    st.session_state[
        "job_form_expected_join_date"
    ] = job.expected_join_date


def render_job_form() -> None:
    """求人情報の入力フォームを表示する。"""

    # 抽出直後の処理経路だけに依存せず、AI結果フォームを表示した
    # 時点でも必ずSQLiteへ同期する。これによりブラウザー更新後も
    # 登録方法選択へ戻らず、同じ確認フォームを復元できる。
    extracted_data = st.session_state.get("job_extracted_data")
    if (
        st.session_state.get(JOB_EDIT_ID_KEY) is None
        and st.session_state.get("job_extraction_completed")
        and isinstance(extracted_data, dict)
    ):
        save_extracted_job_draft(
            extracted_data,
            show_notice=False,
        )

    draft_notice = st.session_state.pop(
        JOB_REGISTRATION_DRAFT_NOTICE_KEY,
        None,
    )
    if draft_notice:
        st.info(draft_notice)

    edit_job_id = st.session_state.get(
        JOB_EDIT_ID_KEY
    )

    return_page = st.session_state.get(
        JOB_FORM_RETURN_PAGE_KEY
    )

    back_button_label = (
        "← 求人一覧へ戻る"
        if (
            edit_job_id is not None
            and return_page == "job_list"
        )
        else "← 登録方法の選択に戻る"
    )

    if st.button(
        back_button_label,
        key="job_form_back",
    ):
        if (
            edit_job_id is not None
            and return_page == "job_list"
        ):
            st.session_state[
                JOB_EDIT_ID_KEY
            ] = None

            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

            st.session_state[
                JOB_FORM_RETURN_PAGE_KEY
            ] = None

            st.query_params["page"] = (
                "job_list"
            )

        else:
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

        st.rerun()

    if edit_job_id is not None:
        st.info(
            f"求人ID {edit_job_id} を編集中です。"
        )

    render_registration_progress(3)

    form_title = (
        "求人情報を編集してください"
        if edit_job_id is not None
        else "求人情報を入力してください"
    )
    st.markdown(
        f"""
        <div class="job-section-title">
            {form_title}
        </div>
        <div class="job-section-description">
            求人票の内容をもとに、必要な情報を入力してください。
            入力した内容は、保存前に次の画面で確認できます。
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get(
        "job_extraction_completed",
        False,
    ):
        st.info(
            "求人票から取得できた情報を"
            "入力フォームへ反映しました。"
            "内容を確認し、不足項目を入力してください。"
        )

    validation_errors = st.session_state.get(JOB_FORM_ERRORS_KEY, {})
    general_validation_errors = st.session_state.get(
        JOB_FORM_GENERAL_ERRORS_KEY,
        [],
    )
    render_job_field_error_styles(validation_errors)
    all_validation_messages = [
        *validation_errors.values(),
        *general_validation_errors,
    ]
    if all_validation_messages:
        render_validation_summary(all_validation_messages)

        if st.session_state.pop(JOB_SCROLL_TO_ERRORS_KEY, False):
            st.components.v1.html(
                """
                <script>
                    window.setTimeout(() => {
                        const summary = window.parent.document
                            .querySelector('.metea-error-summary');
                        if (summary) {
                            summary.scrollIntoView({
                                behavior: 'smooth',
                                block: 'start'
                            });
                        }
                    }, 80);
                </script>
                """,
                height=0,
            )

    with st.container(border=True):

        st.markdown("### 求人基本情報")

        with st.container():
            company_name = st.text_input(
                "会社名 :red[*]",
                key="job_form_company_name",
                on_change=clear_job_form_error,
                args=("company_name",),
            )
            render_required_field_error("company_name")

        job_title = st.text_input(
            "求人名",
            key="job_form_job_title",
        )

        st.markdown(
            '<div class="job-source-required-note">'
            '<strong>紹介経路を入力してください</strong>'
            '紹介経路は求人票から自動判定できないため、保存前に必ず入力してください。'
            '</div>',
            unsafe_allow_html=True,
        )

        source_col1, source_col2 = st.columns(2)
        with source_col1:
            with st.container():
                source_type = st.selectbox(
                    "紹介経路の種別 :red[*]",
                    SOURCE_TYPES,
                    key="job_form_source_type",
                    on_change=clear_job_form_error,
                    args=("source_type",),
                )
                render_required_field_error("source_type")

        with source_col2:
            with st.container():
                source_name = st.text_input(
                    "紹介経路の具体名 :red[*]",
                    placeholder=(
                        "例：リクルートエージェント、"
                        "Indeed、企業採用ページ"
                    ),
                    key="job_form_source_name",
                    on_change=clear_job_form_error,
                    args=("source_name",),
                )
                render_required_field_error("source_name")

        job_number = st.text_input(
            "求人番号",
            key="job_form_job_number",
        )

        col1, col2 = st.columns(2)

        with col1:
            publication_start_date = st.date_input(
                "掲載開始日",
                value=None,
                format="YYYY/MM/DD",
                key="job_form_publication_start",
            )

        with col2:
            publication_end_date = st.date_input(
                "掲載終了日",
                value=None,
                format="YYYY/MM/DD",
                key="job_form_publication_end",
            )

        industry = st.text_input(
            "業種",
            key="job_form_industry",
        )

        business_description = st.text_area(
            "事業内容",
            key="job_form_business_description",
        )

        col3, col4 = st.columns(2)

        with col3:
            has_employee_count = st.checkbox(
                "従業員数の記載あり",
                key="job_form_has_employee_count",
            )

            if has_employee_count:
                employee_count_col1, employee_count_col2 = (
                    st.columns(2)
                )

                with employee_count_col1:
                    employee_count_min = st.number_input(
                        "従業員数（下限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：51",
                        key="job_form_employee_count_min",
                    )

                with employee_count_col2:
                    employee_count_max = st.number_input(
                        "従業員数（上限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：100",
                        key="job_form_employee_count_max",
                    )

                st.caption(
                    "単位：名。単一の人数が記載されている場合は、"
                    "下限と上限へ同じ人数を入力します。"
                )

            else:
                employee_count_min = None
                employee_count_max = None

            established_date = st.text_input(
                "設立",
                key="job_form_established_date",
            )

        with col4:
            capital = st.text_input(
                "資本金",
                key="job_form_capital",
            )

            listing_status = st.selectbox(
                "上場区分",
                options_with_current(
                    LISTING_STATUSES,
                    st.session_state.get(
                        "job_form_listing_status",
                        "",
                    ),
                ),
                key="job_form_listing_status",
            )

    with st.container(border=True):

        st.markdown("### 募集内容")

        col5, col6 = st.columns(2)

        with col5:
            with st.container():
                occupation = st.text_input(
                    "募集ポジション（職種） :red[*]",
                    key="job_form_occupation",
                    on_change=clear_job_form_error,
                    args=("occupation",),
                )
                render_required_field_error("occupation")

            department = st.text_input(
                "配属部署",
                key="job_form_department",
            )

        with col6:
            has_planned_hires = st.checkbox(
                "採用予定人数の記載あり",
                value=(
                    st.session_state.get(
                        "job_form_planned_hires"
                    )
                    is not None
                ),
                key="job_form_has_planned_hires",
            )

            if has_planned_hires:
                planned_hires = st.number_input(
                    "採用予定人数",
                    min_value=1,
                    step=1,
                    value=(
                        st.session_state.get(
                            "job_form_planned_hires"
                        )
                        or 1
                    ),
                    key="job_form_planned_hires_value",
                )

                st.caption("単位：名")

            else:
                planned_hires = None

        recruitment_reason = st.text_area(
            "募集背景・採用理由",
            key="job_form_recruitment_reason",
        )

    with st.container(border=True):

        st.markdown("### 仕事内容")

        with st.container():
            job_summary = st.text_area(
                "仕事内容・業務概要 :red[*]",
                height=140,
                key="job_form_job_summary",
                on_change=clear_job_form_error,
                args=("job_summary",),
            )
            render_required_field_error("job_summary")

        responsibility_scope = st.text_area(
            "担当範囲・役割",
            height=100,
            key="job_form_responsibility_scope",
        )

        col7, col8 = st.columns(2)

        with col7:
            customers = st.text_area(
                "顧客・対象者",
                key="job_form_customers",
            )

            internal_stakeholders = st.text_area(
                "社内の関係者",
                key="job_form_internal_stakeholders",
            )

        with col8:
            external_partners = st.text_area(
                "社外の関係者",
                key="job_form_external_partners",
            )

            goals_kpi = st.text_area(
                "目標・KPI",
                key="job_form_goals_kpi",
            )

        expected_results = st.text_area(
            "期待される成果",
            key="job_form_expected_results",
        )

        organizational_culture = st.text_area(
            "組織風土・企業文化",
            height=120,
            placeholder=(
                "例：チームで相談しながら進める文化、"
                "週次で相互フィードバックを行う"
            ),
            key="job_form_organizational_culture",
            help=(
                "求人票に明記された相談・協働・評価・"
                "フィードバックなどの特徴を入力します。"
            ),
        )

    with st.container(border=True):

        st.markdown("### 勤務条件")

        col9, col10 = st.columns(2)

        with col9:
            employment_type = st.selectbox(
                "雇用形態",
                options_with_current(
                    EMPLOYMENT_TYPES,
                    st.session_state.get(
                        "job_form_employment_type",
                        "",
                    ),
                ),
                key="job_form_employment_type",
            )

            probation_period_status = st.selectbox(
                "試用期間",
                options_with_current(
                    PROBATION_PERIOD_OPTIONS,
                    st.session_state.get(
                        "job_form_probation_period_status",
                        "",
                    ),
                ),
                key="job_form_probation_period_status",
            )

            if probation_period_status == "あり":
                probation_period_months = st.number_input(
                    "試用期間の月数",
                    min_value=1,
                    max_value=60,
                    step=1,
                    value=None,
                    placeholder="例：3",
                    key="job_form_probation_period_months",
                )

                st.caption(
                    "単位：か月。期間が日数で記載されている場合や、"
                    "条件に補足がある場合は下の補足欄へ入力します。"
                )

            else:
                probation_period_months = None

            probation_period = st.text_input(
                "試用期間の補足",
                placeholder=(
                    "例：試用期間中も待遇変更なし、"
                    "試用期間14日間"
                ),
                key="job_form_probation_period",
            )

            prefecture = st.selectbox(
                "都道府県",
                options_with_current(
                    PREFECTURES,
                    st.session_state.get(
                        "job_form_prefecture",
                        "",
                    ),
                ),
                key="job_form_prefecture",
            )

            municipality = st.text_input(
                "市区町村",
                key="job_form_municipality",
            )

            nearest_station = st.text_input(
                "最寄駅",
                key="job_form_nearest_station",
            )

        with col10:
            transfer_required = st.selectbox(
                "転勤",
                options_with_current(
                    TRANSFER_OPTIONS,
                    st.session_state.get(
                        "job_form_transfer_required",
                        "",
                    ),
                ),
                key="job_form_transfer_required",
            )

            work_style = st.selectbox(
                "勤務形態・働き方",
                options_with_current(
                    WORK_STYLE_OPTIONS,
                    st.session_state.get(
                        "job_form_work_style",
                        "",
                    ),
                ),
                key="job_form_work_style",
            )

            flextime = st.selectbox(
                "フレックスタイム",
                options_with_current(
                    FLEXTIME_OPTIONS,
                    st.session_state.get(
                        "job_form_flextime",
                        "",
                    ),
                ),
                key="job_form_flextime",
            )

            has_overtime = st.checkbox(
                "月平均残業時間の記載あり",
                key="job_form_has_overtime",
            )

            if has_overtime:
                overtime = st.number_input(
                    "月平均残業時間",
                    min_value=0,
                    max_value=744,
                    step=1,
                    value=(
                        st.session_state.get(
                            "job_form_overtime_value"
                        )
                        if st.session_state.get(
                            "job_form_overtime_value"
                        )
                        is not None
                        else 20
                    ),
                    key="job_form_overtime_value",
                )

                st.caption(
                    "単位：時間／月。"
                    "求人票に記載された月平均時間を"
                    "0～744時間で入力してください。"
                )

            else:
                overtime = None

        col11, col12 = st.columns(2)

        with col11:
            start_time = st.time_input(
                "始業時間",
                value=None,
                step=900,
                key="job_form_start_time",
            )

            has_break_minutes = st.checkbox(
                "休憩時間の記載あり",
                key="job_form_has_break_minutes",
            )

            if has_break_minutes:
                break_minutes = st.number_input(
                    "休憩時間",
                    min_value=0,
                    max_value=1440,
                    step=1,
                    value=(
                        st.session_state.get(
                            "job_form_break_minutes_value"
                        )
                        if st.session_state.get(
                            "job_form_break_minutes_value"
                        )
                        is not None
                        else 60
                    ),
                    key="job_form_break_minutes_value",
                )

                st.caption(
                    "単位：分。0～1440分の範囲で"
                    "入力してください。"
                )

            else:
                break_minutes = None

        with col12:
            end_time = st.time_input(
                "終業時間",
                value=None,
                step=900,
                key="job_form_end_time",
            )

            has_scheduled_work_hours = st.checkbox(
                "所定労働時間の記載あり",
                key="job_form_has_scheduled_work_hours",
            )

            if has_scheduled_work_hours:
                scheduled_work_hours = st.number_input(
                    "所定労働時間",
                    min_value=0.0,
                    max_value=24.0,
                    step=0.25,
                    value=(
                        st.session_state.get(
                            "job_form_scheduled_work_hours_value"
                        )
                        if st.session_state.get(
                            "job_form_scheduled_work_hours_value"
                        )
                        is not None
                        else 8.0
                    ),
                    key=(
                        "job_form_"
                        "scheduled_work_hours_value"
                    ),
                )

                st.caption(
                    "単位：時間／日。"
                    "例：7時間30分の場合は7.5と入力します。"
                )

            else:
                scheduled_work_hours = None

        holidays = st.text_input(
            "休日・休暇",
            key="job_form_holidays",
        )

        has_annual_holidays = st.checkbox(
            "年間休日数の記載あり",
            value=(
                st.session_state.get(
                    "job_form_annual_holidays"
                )
                is not None
            ),
            key="job_form_has_annual_holidays",
        )

        if has_annual_holidays:
            annual_holidays = st.number_input(
                "年間休日数",
                min_value=1,
                max_value=366,
                step=1,
                value=(
                    st.session_state.get(
                        "job_form_annual_holidays"
                    )
                    or 120
                ),
                key="job_form_annual_holidays_value",
            )

            st.caption(
                "1年間の休日数を"
                "1～366日の範囲で入力してください。"
            )

        else:
            annual_holidays = None
    with st.container(border=True):

        st.markdown("### 給与・待遇")

        wage_type = st.selectbox(
            "賃金形態",
            options_with_current(
                WAGE_TYPES,
                st.session_state.get(
                    "job_form_wage_type",
                    "",
                ),
            ),
            key="job_form_wage_type",
        )

        st.caption(
            "月給・基本給は円単位、"
            "想定年収は万円単位で入力します。"
        )

        col13, col14 = st.columns(2)

        with col13:
            monthly_salary_min = comma_number_input(
                "月給最低額（円）",
                key="job_form_monthly_salary_min",
                placeholder="例：280,000",
            )

            base_salary_min = comma_number_input(
                "基本給最低額（円）",
                key="job_form_base_salary_min",
                placeholder="例：240,000",
            )

            expected_salary_min = comma_number_input(
                "想定年収最低額（万円）",
                key="job_form_expected_salary_min",
                placeholder="例：400",
            )

            bonus = st.text_input(
                "賞与",
                key="job_form_bonus",
            )

        with col14:
            monthly_salary_max = comma_number_input(
                "月給最高額（円）",
                key="job_form_monthly_salary_max",
                placeholder="例：350,000",
            )

            base_salary_max = comma_number_input(
                "基本給最高額（円）",
                key="job_form_base_salary_max",
                placeholder="例：300,000",
            )

            expected_salary_max = comma_number_input(
                "想定年収最高額（万円）",
                key="job_form_expected_salary_max",
                placeholder="例：550",
            )

            salary_increase = st.text_input(
                "昇給",
                key="job_form_salary_increase",
            )

        st.divider()

        fixed_overtime_system = st.selectbox(
            "固定残業制",
            options_with_current(
                FIXED_OVERTIME_OPTIONS,
                st.session_state.get(
                    "job_form_fixed_overtime_system",
                    "",
                ),
            ),
            key="job_form_fixed_overtime_system",
        )

        if fixed_overtime_system == "あり":
            st.caption(
                "求人票に記載された固定残業時間と"
                "固定残業代を入力してください。"
            )

            fixed_col1, fixed_col2 = st.columns(2)

            with fixed_col1:
                fixed_overtime_hours = st.number_input(
                    "固定残業時間（時間／月）",
                    min_value=0,
                    step=1,
                    value=None,
                    placeholder="例：20",
                    key="job_form_fixed_overtime_hours",
                )

                fixed_overtime_pay_min = comma_number_input(
                    "固定残業代最低額（円）",
                    key="job_form_fixed_overtime_pay_min",
                    placeholder="例：40,000",
                )

            with fixed_col2:
                fixed_overtime_pay_max = comma_number_input(
                    "固定残業代最高額（円）",
                    key="job_form_fixed_overtime_pay_max",
                    placeholder="例：60,000",
                )

                overtime_extra_pay = st.selectbox(
                    "固定残業時間の超過分を追加支給",
                    options_with_current(
                        FIXED_OVERTIME_OPTIONS,
                        st.session_state.get(
                            "job_form_overtime_extra_pay",
                            "",
                        ),
                    ),
                    key="job_form_overtime_extra_pay",
                )

            st.caption(
                "固定残業代について求人票に記載がない項目は、"
                "未入力のままで保存できます。"
            )

        else:
            fixed_overtime_hours = None
            fixed_overtime_pay_min = None
            fixed_overtime_pay_max = None
            overtime_extra_pay = ""

        incentive = st.text_input(
            "インセンティブ",
            key="job_form_incentive",
        )

    with st.container(border=True):

        st.markdown("### 福利厚生")

        col15, col16 = st.columns(2)

        with col15:
            social_insurance = st.text_input(
                "社会保険",
                key="job_form_social_insurance",
            )

            commuting_allowance = st.text_input(
                "通勤手当",
                key="job_form_commuting_allowance",
            )

            housing_allowance = st.text_input(
                "住宅手当",
                key="job_form_housing_allowance",
            )

        with col16:
            retirement_plan = st.text_input(
                "退職金制度",
                key="job_form_retirement_plan",
            )

            qualification_support = st.text_input(
                "資格取得支援",
                key="job_form_qualification_support",
            )

            training_program = st.text_input(
                "研修制度",
                key="job_form_training_program",
            )

    with st.container(border=True):

        st.markdown("### 応募条件・求める人物像")

        st.caption(
            "複数ある場合は、1行に1項目ずつ入力してください。"
        )

        col17, col18 = st.columns(2)

        with col17:
            required_experience_text = st.text_area(
                "必須経験",
                placeholder=(
                    "例：\n"
                    "法人営業経験3年以上\n"
                    "顧客折衝経験"
                ),
                key="job_form_required_experience",
            )

            required_skills_text = st.text_area(
                "必須スキル",
                placeholder=(
                    "例：\n"
                    "Excel\n"
                    "PowerPoint"
                ),
                key="job_form_required_skills",
            )

            required_qualifications_text = st.text_area(
                "必須資格",
                key="job_form_required_qualifications",
            )

        with col18:
            preferred_experience_text = st.text_area(
                "歓迎経験",
                key="job_form_preferred_experience",
            )

            preferred_skills_text = st.text_area(
                "歓迎スキル",
                key="job_form_preferred_skills",
            )

            desired_personality_text = st.text_area(
                "求める人物像",
                key="job_form_desired_personality",
            )

        job_details_text = st.text_area(
            "具体的な業務内容",
            placeholder=(
                "複数ある場合は1行ずつ入力してください。"
            ),
            key="job_form_job_details",
        )

        not_listed_fields_text = st.text_area(
            "求人票に記載がない項目・確認したいこと",
            placeholder=(
                "例：\n"
                "平均残業時間の記載なし\n"
                "在宅勤務頻度の記載なし"
            ),
            key="job_form_not_listed_fields",
        )

    with st.container(border=True):

        st.markdown("### 選考情報")

        col19, col20 = st.columns(2)

        with col19:
            document_screening_status = st.selectbox(
                "書類選考",
                options_with_current(
                    SELECTION_STEP_OPTIONS,
                    st.session_state.get(
                        "job_form_document_screening_status",
                        "",
                    ),
                ),
                key="job_form_document_screening_status",
            )

            document_screening = st.text_input(
                "書類選考の補足",
                placeholder=(
                    "例：履歴書・職務経歴書による選考"
                ),
                key="job_form_document_screening",
            )

            aptitude_test_status = st.selectbox(
                "適性検査",
                options_with_current(
                    SELECTION_STEP_OPTIONS,
                    st.session_state.get(
                        "job_form_aptitude_test_status",
                        "",
                    ),
                ),
                key="job_form_aptitude_test_status",
            )

            aptitude_test = st.text_input(
                "適性検査の補足",
                placeholder="例：Web適性検査、SPI",
                key="job_form_aptitude_test",
            )

            expected_join_date = st.text_input(
                "入社予定・入社可能時期",
                key="job_form_expected_join_date",
            )

        with col20:
            interview = st.text_input(
                "面接",
                key="job_form_interview",
            )

            has_interview_count = st.checkbox(
                "面接回数の記載あり",
                key="job_form_has_interview_count",
            )

            if has_interview_count:
                interview_count_col1, interview_count_col2 = (
                    st.columns(2)
                )

                with interview_count_col1:
                    interview_count_min = st.number_input(
                        "面接回数（下限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：1",
                        key="job_form_interview_count_min",
                    )

                with interview_count_col2:
                    interview_count_max = st.number_input(
                        "面接回数（上限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：2",
                        key="job_form_interview_count_max",
                    )

                st.caption(
                    "単位：回。面接が2回と確定している場合は、"
                    "下限と上限へ同じ回数を入力します。"
                )

            else:
                interview_count_min = None
                interview_count_max = None

    st.divider()

    edit_job_id = st.session_state.get(
        JOB_EDIT_ID_KEY
    )

    save_button_label = (
        "変更内容を確認する"
        if edit_job_id is not None
        else "登録内容を確認する"
    )

    interview_count_error = ""

    if (
        interview_count_min is not None
        and interview_count_max is not None
        and interview_count_min > interview_count_max
    ):
        interview_count_error = (
            "面接回数の下限が上限を超えています。"
        )

    employee_count_error = ""

    if (
        employee_count_min is not None
        and employee_count_max is not None
        and employee_count_min > employee_count_max
    ):
        employee_count_error = (
            "従業員数の下限が上限を超えています。"
        )

    salary_range_errors: list[str] = []

    salary_ranges = (
        (
            monthly_salary_min,
            monthly_salary_max,
            "月給",
        ),
        (
            base_salary_min,
            base_salary_max,
            "基本給",
        ),
        (
            expected_salary_min,
            expected_salary_max,
            "想定年収",
        ),
        (
            fixed_overtime_pay_min,
            fixed_overtime_pay_max,
            "固定残業代",
        ),
    )

    for (
        minimum_value,
        maximum_value,
        salary_label,
    ) in salary_ranges:
        if (
            minimum_value is not None
            and maximum_value is not None
            and minimum_value > maximum_value
        ):
            salary_range_errors.append(
                f"{salary_label}の最低額が"
                "最高額を超えています。"
            )

    if st.button(
        save_button_label,
        key="job_form_save",
        type="primary",
        use_container_width=True,
    ):
        required_errors = validate_required_job_fields(
            company_name=company_name,
            source_type=source_type,
            source_name=source_name,
            occupation=occupation,
            job_summary=job_summary,
        )
        general_errors: list[str] = []
        if interview_count_error:
            general_errors.append(interview_count_error)
        if employee_count_error:
            general_errors.append(employee_count_error)
        general_errors.extend(salary_range_errors)

        st.session_state[JOB_FORM_ERRORS_KEY] = required_errors
        st.session_state[JOB_FORM_GENERAL_ERRORS_KEY] = general_errors
        if required_errors or general_errors:
            st.session_state[JOB_SCROLL_TO_ERRORS_KEY] = True
            st.rerun()
        job = Job(
            registration_method=st.session_state[
                JOB_REGISTRATION_MODE_KEY
            ],
            source_url=st.session_state.get(
                "job_registration_url",
                "",
            ),
            source_text=st.session_state.get(
                "job_registration_text",
                "",
            ),
            acquired_at="",
            source_type=source_type,
            source_name=source_name,

            company_name=company_name,
            job_title=job_title,
            job_number=job_number,
            publication_start_date=date_to_text(
                publication_start_date
            ),
            publication_end_date=date_to_text(
                publication_end_date
            ),
            industry=industry,
            business_description=business_description,
            employee_count_min=integer_to_text(
                employee_count_min
            ),
            employee_count_max=integer_to_text(
                employee_count_max
            ),
            employee_count=(
                integer_to_text(employee_count_min)
                if (
                    employee_count_min is not None
                    and employee_count_min
                    == employee_count_max
                )
                else ""
            ),
            established_date=established_date,
            capital=capital,
            listing_status=listing_status,

            occupation=occupation,
            department=department,
            planned_hires=integer_to_text(
                planned_hires
            ),
            recruitment_reason=recruitment_reason,

            job_summary=job_summary,
            responsibility_scope=responsibility_scope,
            customers=customers,
            internal_stakeholders=internal_stakeholders,
            external_partners=external_partners,
            goals_kpi=goals_kpi,
            expected_results=expected_results,
            organizational_culture=organizational_culture,

            employment_type=employment_type,
            probation_period_status=(
                probation_period_status
            ),
            probation_period_months=integer_to_text(
                probation_period_months
            ),
            probation_period=probation_period,
            prefecture=prefecture,
            municipality=municipality,
            nearest_station=nearest_station,
            transfer_required=transfer_required,
            work_style=work_style,
            start_time=time_to_text(
                start_time
            ),
            end_time=time_to_text(
                end_time
            ),
            break_minutes=(
                integer_to_text(break_minutes)
                if break_minutes is not None
                else st.session_state.get(
                    "job_form_break_minutes_legacy",
                    "",
                )
            ),
            scheduled_work_hours=(
                hour_to_text(scheduled_work_hours)
                if scheduled_work_hours is not None
                else st.session_state.get(
                    "job_form_scheduled_work_hours_legacy",
                    "",
                )
            ),
            flextime=flextime,
            overtime=(
                integer_to_text(overtime)
                if overtime is not None
                else st.session_state.get(
                    "job_form_overtime_legacy",
                    "",
                )
            ),
            holidays=holidays,
            annual_holidays=integer_to_text(
                annual_holidays
            ),

            wage_type=wage_type,
            monthly_salary_min=integer_to_text(
                monthly_salary_min
            ),
            monthly_salary_max=integer_to_text(
                monthly_salary_max
            ),
            base_salary_min=integer_to_text(
                base_salary_min
            ),
            base_salary_max=integer_to_text(
                base_salary_max
            ),

            monthly_salary=st.session_state.get(
                "job_form_monthly_salary",
                "",
            ),
            annual_salary=st.session_state.get(
                "job_form_annual_salary",
                "",
            ),
            expected_salary_min=integer_to_text(
                expected_salary_min
            ),
            expected_salary_max=integer_to_text(
                expected_salary_max
            ),
            fixed_overtime_system=fixed_overtime_system,
            fixed_overtime_pay_min=integer_to_text(
                fixed_overtime_pay_min
            ),
            fixed_overtime_pay_max=integer_to_text(
                fixed_overtime_pay_max
            ),
            overtime_extra_pay=overtime_extra_pay,

            fixed_overtime_hours=integer_to_text(
                fixed_overtime_hours
            ),
            fixed_overtime_pay=integer_to_text(
                fixed_overtime_pay_min
            ),
            bonus=bonus,
            salary_increase=salary_increase,
            incentive=incentive,

            social_insurance=social_insurance,
            commuting_allowance=commuting_allowance,
            housing_allowance=housing_allowance,
            retirement_plan=retirement_plan,
            qualification_support=qualification_support,
            training_program=training_program,

            document_screening_status=(
                document_screening_status
            ),
            document_screening=document_screening,
            interview=interview,
            aptitude_test_status=(
                aptitude_test_status
            ),
            aptitude_test=aptitude_test,
            interview_count_min=integer_to_text(
                interview_count_min
            ),
            interview_count_max=integer_to_text(
                interview_count_max
            ),
            interview_count=(
                integer_to_text(interview_count_min)
                if (
                    interview_count_min is not None
                    and interview_count_min
                    == interview_count_max
                )
                else ""
            ),
            expected_join_date=expected_join_date,

            job_details=text_to_list(
                job_details_text
            ),
            required_experience=text_to_list(
                required_experience_text
            ),
            required_skills=text_to_list(
                required_skills_text
            ),
            required_qualifications=text_to_list(
                required_qualifications_text
            ),
            preferred_experience=text_to_list(
                preferred_experience_text
            ),
            preferred_skills=text_to_list(
                preferred_skills_text
            ),
            desired_personality=text_to_list(
                desired_personality_text
            ),
            not_listed_fields=text_to_list(
                not_listed_fields_text
            ),
        )

        st.session_state[
            JOB_CONFIRM_DATA_KEY
        ] = job

        st.session_state[
            JOB_FORM_STEP_KEY
        ] = "confirm"

        st.rerun()


# ========================================
# 登録内容の最終確認
# ========================================

def render_job_confirmation() -> None:
    """保存前の求人情報を確認する画面。"""

    job = st.session_state.get(
        JOB_CONFIRM_DATA_KEY
    )

    if job is None:
        st.error(
            "確認する求人情報を取得できませんでした。"
        )

        if st.button(
            "入力画面へ戻る",
            key="job_confirm_missing_back",
        ):
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "form"

            st.session_state[
                "job_extraction_completed"
            ] = False

            st.rerun()

        return

    render_registration_progress(4)

    st.markdown(
        """
        <div class="job-section-title">
            登録内容を確認してください
        </div>
        <div class="job-section-description">
            以下の内容で求人情報を登録します。
            誤りがある場合は入力画面へ戻って修正してください。
        </div>
        """,
        unsafe_allow_html=True,
    )

    def show_value(
        label: str,
        value,
    ) -> None:
        """確認用にラベルと値を表示する。"""

        if isinstance(value, list):
            display_value = "\n".join(
                f"・{item}"
                for item in value
                if str(item).strip()
            )
        else:
            display_value = str(
                value or ""
            ).strip()

        if not display_value:
            display_value = "未入力"

        st.markdown(f"**{label}**")
        st.text(display_value)

    with st.container(border=True):
        st.markdown("### 求人基本情報")

        confirm_col1, confirm_col2 = st.columns(2)

        with confirm_col1:
            show_value(
                "会社名",
                job.company_name,
            )
            show_value(
                "求人名",
                job.job_title,
            )
            show_value(
                "募集ポジション（職種）",
                job.occupation,
            )
            show_value(
                "業種",
                job.industry,
            )

        with confirm_col2:
            show_value(
                "紹介経路の種別",
                job.source_type,
            )
            show_value(
                "紹介経路の具体名",
                job.source_name,
            )
            show_value(
                "求人番号",
                job.job_number,
            )
            show_value(
                "配属部署",
                job.department,
            )

    with st.container(border=True):
        st.markdown("### 仕事内容・応募条件")

        show_value(
            "仕事内容・業務概要",
            job.job_summary,
        )
        show_value(
            "具体的な業務内容",
            job.job_details,
        )
        show_value(
            "必須経験",
            job.required_experience,
        )
        show_value(
            "必須スキル",
            job.required_skills,
        )
        show_value(
            "必須資格",
            job.required_qualifications,
        )
        show_value(
            "歓迎経験",
            job.preferred_experience,
        )
        show_value(
            "歓迎スキル",
            job.preferred_skills,
        )
        show_value(
            "求める人物像",
            job.desired_personality,
        )
        show_value(
            "組織風土・企業文化",
            job.organizational_culture,
        )

    with st.container(border=True):
        st.markdown("### 勤務条件")

        condition_col1, condition_col2 = (
            st.columns(2)
        )

        with condition_col1:
            show_value(
                "雇用形態",
                job.employment_type,
            )
            show_value(
                "勤務地",
                (
                    f"{job.prefecture}"
                    f"{job.municipality}"
                ),
            )
            show_value(
                "勤務形態・働き方",
                job.work_style,
            )
            show_value(
                "転勤",
                job.transfer_required,
            )

        with condition_col2:
            show_value(
                "始業時間",
                job.start_time,
            )
            show_value(
                "終業時間",
                job.end_time,
            )
            show_value(
                "月平均残業時間",
                job.overtime,
            )
            show_value(
                "年間休日数",
                job.annual_holidays,
            )

    with st.container(border=True):
        st.markdown("### 給与・選考")

        salary_col, selection_col = st.columns(2)

        with salary_col:
            show_value(
                "賃金形態",
                job.wage_type,
            )
            show_value(
                "想定年収最低額（万円）",
                job.expected_salary_min,
            )
            show_value(
                "想定年収最高額（万円）",
                job.expected_salary_max,
            )
            show_value(
                "固定残業制",
                job.fixed_overtime_system,
            )

        with selection_col:
            show_value(
                "書類選考",
                job.document_screening_status,
            )
            show_value(
                "適性検査",
                job.aptitude_test_status,
            )
            show_value(
                "面接回数（下限）",
                job.interview_count_min,
            )
            show_value(
                "面接回数（上限）",
                job.interview_count_max,
            )

    if job.not_listed_fields:
        with st.container(border=True):
            st.markdown(
                "### 未入力・確認が必要な項目"
            )

            show_value(
                "求人票から確認できなかった内容",
                job.not_listed_fields,
            )

    confirm_back_col, confirm_save_col = (
        st.columns(2)
    )

    with confirm_back_col:
        if st.button(
            "入力画面へ戻って修正する",
            key="job_confirm_back",
            use_container_width=True,
        ):
            apply_extracted_job_data(
                asdict(job)
            )

            st.session_state[
                "job_form_source_type"
            ] = job.source_type

            st.session_state[
                "job_form_source_name"
            ] = job.source_name

            st.session_state[
                "job_form_publication_start"
            ] = parse_date_value(
                job.publication_start_date
            )

            st.session_state[
                "job_form_publication_end"
            ] = parse_date_value(
                job.publication_end_date
            )

            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "form"

            st.rerun()

    with confirm_save_col:
        if st.button(
            "この内容で登録する",
            key="job_confirm_save",
            type="primary",
            use_container_width=True,
        ):
            edit_job_id = st.session_state.get(
                JOB_EDIT_ID_KEY
            )

            if edit_job_id is not None:
                errors = update_job_data(
                    edit_job_id,
                    job,
                )

                if errors:
                    for error in errors:
                        st.error(error)

                    return

                move_to_job_completion_after_ai_evaluation(
                    message="求人情報を更新しました。",
                    job_id=edit_job_id,
                )

            duplicate_type, existing_job_id, errors = (
                save_job_data(job)
            )

            if errors:
                for error in errors:
                    st.error(error)

                return

            if duplicate_type == DUPLICATE_NONE:
                same_company_job = next(
                    (
                        (saved_job_id, saved_job)
                        for saved_job_id, saved_job in load_jobs()
                        if saved_job.company_name.strip().casefold()
                        == job.company_name.strip().casefold()
                    ),
                    None,
                )
                if same_company_job is not None:
                    st.session_state[JOB_PENDING_DATA_KEY] = job
                    st.session_state[JOB_DUPLICATE_ID_KEY] = same_company_job[0]
                    st.session_state[JOB_DUPLICATE_TYPE_KEY] = SAME_COMPANY_OTHER_JOB
                    st.session_state[JOB_FORM_STEP_KEY] = "duplicate"
                    st.rerun()

                job_id, create_errors = (
                    create_job_data(job)
                )

                if create_errors:
                    for error in create_errors:
                        st.error(error)

                    return

                move_to_job_completion_after_ai_evaluation(
                    message="求人情報を保存しました。",
                    job_id=job_id,
                )

            if duplicate_type == DUPLICATE_POSSIBLE:
                if existing_job_id is None:
                    st.error(
                        "類似する求人情報を取得できませんでした。"
                    )
                    return

                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = job

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = existing_job_id

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = DUPLICATE_POSSIBLE

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "duplicate"

                st.rerun()

            if duplicate_type == DUPLICATE_EXACT:
                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = job

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = existing_job_id

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = DUPLICATE_EXACT

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "duplicate"

                st.rerun()

            if (
                duplicate_type
                == DUPLICATE_DIFFERENT_SOURCE
            ):
                if existing_job_id is None:
                    st.error(
                        "登録済み求人を取得できませんでした。"
                    )
                    return

                st.session_state[JOB_PENDING_DATA_KEY] = job
                st.session_state[JOB_DUPLICATE_ID_KEY] = existing_job_id
                st.session_state[JOB_DUPLICATE_TYPE_KEY] = DUPLICATE_DIFFERENT_SOURCE
                st.session_state[JOB_FORM_STEP_KEY] = "duplicate"
                st.rerun()


def move_to_job_completion(
    message: str,
    job_id: int,
    note: str = "",
) -> None:
    """保存完了画面へ移動する。"""

    delete_draft(
        user_id=get_current_user_id(),
        form_name=JOB_REGISTRATION_DRAFT_FORM_NAME,
    )

    st.session_state[
        JOB_CONFIRM_DATA_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_MESSAGE_KEY
    ] = message

    st.session_state[
        JOB_COMPLETE_NOTE_KEY
    ] = note

    st.session_state[
        JOB_COMPLETE_JOB_ID_KEY
    ] = job_id

    st.session_state[
        JOB_FORM_STEP_KEY
    ] = "complete"

    st.rerun()


def move_to_job_completion_after_ai_evaluation(
    message: str,
    job_id: int,
) -> None:
    """求人保存後にAI評価を予約し、待たずに完了画面へ移動する。"""

    queued = enqueue_job_evaluation(job_id=job_id)
    completion_message = message
    note = (
        "AIがマッチ度を確認しています。"
        "評価が完了すると、求人一覧から確認画面を開けるようになります。"
        if queued else
        "AI評価はすでに処理中です。完了後に求人一覧から確認できます。"
    )

    move_to_job_completion(
        message=completion_message,
        job_id=job_id,
        note=note,
    )


def render_job_completion() -> None:
    """求人情報の保存完了画面を表示する。"""

    message = st.session_state.get(
        JOB_COMPLETE_MESSAGE_KEY
    )

    note = st.session_state.get(
        JOB_COMPLETE_NOTE_KEY,
        "",
    )

    job_id = st.session_state.get(
        JOB_COMPLETE_JOB_ID_KEY
    )

    if not message or job_id is None:
        st.error(
            "保存した求人情報を取得できませんでした。"
        )

        if st.button(
            "求人一覧へ戻る",
            key="job_complete_error_back",
        ):
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

            st.query_params["page"] = "job_list"
            st.rerun()

        return

    complete_icon = svg_data_uri("value-check.svg")
    is_ai_pending = "AI" in note and (
        "確認" in note or "評価" in note
    )
    status_title = (
        "AIマッチングを確認中"
        if is_ai_pending
        else "確認しておきたいこと"
    )

    with st.container(border=True):
        st.markdown(
            '<div class="job-registration-shell-marker"></div>',
            unsafe_allow_html=True,
        )
        render_registration_progress(5)
        st.markdown(
            f"""
            <div class="job-complete-content">
                <div class="job-complete-icon">
                    <img src="{complete_icon}" alt="">
                </div>
                <h1 class="job-complete-title">{message}</h1>
                <p class="job-complete-description">
                    求人情報の登録が完了しました。<br>
                    登録した内容は、求人一覧からいつでも確認できます。
                </p>
                {(
                    f'<div class="job-complete-status">'
                    f'<span class="job-complete-status-mark"></span>'
                    f'<div><strong>{status_title}</strong>'
                    f'<span>{note}</span></div></div>'
                    if note else ''
                )}
                <span class="job-complete-id">求人ID：{job_id}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="job-complete-actions-marker"></div>',
            unsafe_allow_html=True,
        )
        list_col, new_col = st.columns(2, gap="medium")

        with list_col:
            if st.button(
                "求人一覧へ戻る",
                key="job_complete_to_list",
                type="primary",
                use_container_width=True,
            ):
                st.query_params["page"] = "job_list"
                st.query_params.pop("job_id", None)
                st.rerun()

        with new_col:
            if st.button(
                "続けて求人を登録する",
                key="job_complete_register_another",
                use_container_width=True,
            ):
                start_new_job_registration()
                st.rerun()

def render_duplicate_confirmation() -> None:
    """登録済みの同一求人を案内する画面。"""

    render_registration_progress(4)

    duplicate_type = st.session_state.get(
        JOB_DUPLICATE_TYPE_KEY
    )

    pending_job = st.session_state.get(
        JOB_PENDING_DATA_KEY
    )

    existing_job_id = st.session_state.get(
        JOB_DUPLICATE_ID_KEY
    )

    if (
        duplicate_type
        not in (
            DUPLICATE_EXACT,
            DUPLICATE_POSSIBLE,
            DUPLICATE_DIFFERENT_SOURCE,
            SAME_COMPANY_OTHER_JOB,
        )
        or pending_job is None
        or existing_job_id is None
    ):
        st.error(
            "重複確認に必要な情報を取得できませんでした。"
        )

        if st.button(
            "求人登録へ戻る",
            key="duplicate_missing_back",
        ):
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

            st.session_state[
                JOB_PENDING_DATA_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_ID_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_TYPE_KEY
            ] = None

            st.rerun()

        return

    existing_job = load_job(
        existing_job_id
    )

    if existing_job is None:
        st.error(
            "登録済みの求人情報を取得できませんでした。"
        )
        return

    if duplicate_type == SAME_COMPANY_OTHER_JOB:
        st.warning(
            "同じ会社に登録済みの別求人があります。複数ポジションへの応募状況を確認してから登録してください。"
        )
        st.markdown("### 同じ会社の登録済み求人")
    elif duplicate_type == DUPLICATE_POSSIBLE:
        st.warning(
            "同じ求人の可能性がある求人が見つかりました。"
            "内容を確認して、同じ求人かどうか判断してください。"
        )

        st.markdown("### 類似する登録済み求人")

    else:
        st.warning(
            "この求人はすでに登録されています。"
            "同じ求人を重複して登録することはできません。"
        )

        st.markdown("### 登録済みの求人")

    related_jobs = [(existing_job_id, existing_job)]
    if duplicate_type == SAME_COMPANY_OTHER_JOB:
        related_jobs = [
            (job_id, job)
            for job_id, job in load_jobs()
            if job.company_name.strip().casefold()
            == pending_job.company_name.strip().casefold()
        ]
    related_job_ids = {job_id for job_id, _ in related_jobs}
    related_job_names = {
        job_id: (job.job_title or job.occupation or "求人名未入力")
        for job_id, job in related_jobs
    }
    for related_job_id, related_job in related_jobs:
        with st.container(border=True):
            st.markdown(f"**{escape(related_job.company_name)}**")
            st.write(related_job_names[related_job_id])
            st.caption(
                f"紹介経路：{related_job.source_type or '未設定'}／"
                f"{related_job.source_name or '未設定'}"
            )
            st.caption(f"求人ID：{related_job_id}")

    applications = [
        item for item in get_applications(get_current_user_id(), include_closed=True)
        if item.job_id in related_job_ids
    ]
    decisions = load_job_application_decisions()
    related_decisions = [
        (job_id, decisions[job_id])
        for job_id in related_job_ids
        if job_id in decisions and decisions[job_id].decision_status
    ]
    st.markdown("### 過去の応募・検討状況")
    if applications:
        for application in applications:
            result_text = application.selection_result or "未設定"
            job_label = related_job_names.get(application.job_id, "求人名未入力")
            st.markdown(
                f"- 求人：**{escape(job_label)}**　"
                f"応募経路：**{escape(str(application.actual_route or '未設定'))}**　"
                f"応募日：**{escape(str(application.application_date or '未登録'))}**　"
                f"結果：**{escape(result_text)}**　現在地：**{escape(application.current_phase or '未設定')}**"
            )
        st.error(
            f"今回の紹介経路は「{pending_job.source_name or pending_job.source_type or '未設定'}」です。"
            "二重応募・再応募を避けるため、登録後に応募する前に紹介元へ確認してください。"
        )
    elif related_decisions:
        for decision_job_id, decision in related_decisions:
            st.info(
                f"「{related_job_names.get(decision_job_id, '求人名未入力')}」の過去の応募判断は"
                f"「{decision.decision_status}」です。実際の応募履歴はありません。"
                "今回あらためて検討する求人か確認してください。"
            )
    else:
        st.info("この求人に紐づく過去の応募履歴はありません。")

    differences = compare_jobs(
        existing_job,
        pending_job,
    )

    if differences:
        st.markdown(
            "### 登録済み情報との違い"
        )

        st.caption(
            "今回入力した内容には以下の違いがあります。"
            "この画面から既存求人を上書きすることはありません。"
        )

        comparison_rows = "".join(
            "<tr>"
            f"<th scope='row'>{escape(str(label))}</th>"
            f"<td>{escape(str(old_value or '未登録'))}</td>"
            f"<td>{escape(str(new_value or '未登録'))}</td>"
            "</tr>"
            for label, old_value, new_value in differences
        )
        st.markdown(
            """
            <style>
            .job-difference-wrap{width:100%;overflow:hidden;border:1px solid #dce3ed;border-radius:10px;background:#fff}
            .job-difference-table{width:100%;table-layout:fixed;border-collapse:collapse;color:#263a58;font-size:12px;line-height:1.65}
            .job-difference-table col:first-child{width:20%}.job-difference-table col:nth-child(2),.job-difference-table col:nth-child(3){width:40%}
            .job-difference-table th,.job-difference-table td{padding:10px 12px;border-right:1px solid #e3e8f0;border-bottom:1px solid #e3e8f0;vertical-align:top;text-align:left;white-space:normal;overflow-wrap:anywhere;word-break:break-word}
            .job-difference-table thead th{background:#f7f9fc;color:#607087;font-weight:800}
            .job-difference-table tbody th{background:#fbfcfe;color:#40536d;font-weight:750}
            .job-difference-table tr>*:last-child{border-right:0}.job-difference-table tbody tr:last-child>*{border-bottom:0}
            @media(max-width:700px){.job-difference-table{font-size:11px}.job-difference-table th,.job-difference-table td{padding:8px}.job-difference-table col:first-child{width:24%}.job-difference-table col:nth-child(2),.job-difference-table col:nth-child(3){width:38%}}
            </style>
            <div class="job-difference-wrap"><table class="job-difference-table">
              <colgroup><col><col><col></colgroup>
              <thead><tr><th>項目</th><th>登録済み情報</th><th>今回の入力</th></tr></thead>
              <tbody>"""
            + comparison_rows
            + "</tbody></table></div>",
            unsafe_allow_html=True,
        )

    else:
        st.info(
            "登録済み情報と今回の入力内容は同じです。"
        )

    if duplicate_type in {DUPLICATE_POSSIBLE, DUPLICATE_DIFFERENT_SOURCE}:
        st.markdown("### この求人をどう登録しますか？")

        st.caption(
            "同じ求人で紹介経路だけが異なる場合は、"
            "既存求人へ紹介経路を追加してください。"
        )

        same_job_col, new_job_col = st.columns(2)

        with same_job_col:
            if st.button(
                "同じ求人として紹介経路を追加する",
                key="possible_add_source",
                type="primary",
                use_container_width=True,
            ):
                source_errors = add_job_source_data(
                    existing_job_id,
                    pending_job,
                )

                if source_errors:
                    for error in source_errors:
                        st.error(error)

                    return

                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = None

                st.session_state[
                    JOB_CONFIRM_DATA_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = None

                move_to_job_completion(
                    message=(
                        "登録済みの求人へ、"
                        "新しい紹介経路を追加しました。"
                    ),
                    job_id=existing_job_id,
                    note=(
                        "二重応募を避けるため、"
                        "応募前に紹介元のエージェント等へ"
                        "応募経路を確認してください。"
                    ),
                )

        with new_job_col:
            if duplicate_type == DUPLICATE_POSSIBLE:
                if st.button(
                    "別の求人として登録する",
                    key="possible_register_as_new",
                    use_container_width=True,
                ):
                    job_id, create_errors = create_job_data(
                        pending_job
                    )

                    if create_errors:
                        for error in create_errors:
                            st.error(error)

                        return

                    st.session_state[
                        JOB_PENDING_DATA_KEY
                    ] = None

                    st.session_state[
                        JOB_CONFIRM_DATA_KEY
                    ] = None

                    st.session_state[
                        JOB_DUPLICATE_ID_KEY
                    ] = None

                    st.session_state[
                        JOB_DUPLICATE_TYPE_KEY
                    ] = None

                    move_to_job_completion_after_ai_evaluation(
                        message="別の求人として保存しました。",
                        job_id=job_id,
                    )
            else:
                st.caption("同一求人のため、求人本体を重複登録せず紹介経路だけを追加します。")

    elif duplicate_type == SAME_COMPANY_OTHER_JOB:
        st.markdown("### 今回の求人")
        st.write(pending_job.job_title or pending_job.occupation or "求人名未入力")
        st.caption(
            f"紹介経路：{pending_job.source_name or pending_job.source_type or '未設定'}"
        )
        if st.button(
            "別求人として登録する",
            key="same_company_register_new_job",
            type="primary",
            use_container_width=True,
        ):
            job_id, create_errors = create_job_data(pending_job)
            if create_errors:
                for error in create_errors:
                    st.error(error)
                return
            st.session_state[JOB_PENDING_DATA_KEY] = None
            st.session_state[JOB_CONFIRM_DATA_KEY] = None
            st.session_state[JOB_DUPLICATE_ID_KEY] = None
            st.session_state[JOB_DUPLICATE_TYPE_KEY] = None
            move_to_job_completion_after_ai_evaluation(
                message="同じ会社の別求人として保存しました。",
                job_id=job_id,
            )

    detail_col, back_col = st.columns(2)

    with detail_col:
        if st.button(
            "登録済みの求人を確認する",
            key="duplicate_open_existing",
            type="primary",
            use_container_width=True,
        ):
            st.session_state[
                JOB_PENDING_DATA_KEY
            ] = None

            st.session_state[
                JOB_CONFIRM_DATA_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_ID_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_TYPE_KEY
            ] = None

            st.query_params["page"] = (
                "job_detail"
            )

            st.query_params["job_id"] = str(
                existing_job_id
            )

            st.rerun()

    with back_col:
        if st.button(
            "入力画面へ戻る",
            key="duplicate_back_to_form",
            use_container_width=True,
        ):
            apply_extracted_job_data(
                asdict(pending_job)
            )

            st.session_state[
                "job_form_source_type"
            ] = pending_job.source_type

            st.session_state[
                "job_form_source_name"
            ] = pending_job.source_name

            st.session_state[
                "job_form_publication_start"
            ] = parse_date_value(
                pending_job.publication_start_date
            )

            st.session_state[
                "job_form_publication_end"
            ] = parse_date_value(
                pending_job.publication_end_date
            )

            st.session_state[
                JOB_PENDING_DATA_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_ID_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_TYPE_KEY
            ] = None

            st.session_state[
                JOB_CONFIRM_DATA_KEY
            ] = pending_job

            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "form"

            st.rerun()
# ========================================
# 画面本体
# ========================================

def show_page() -> None:
    """求人登録画面を表示する。"""

    restore_extracted_job_draft()

    render_job_navigation("job_registration")
    render_styles()

    if JOB_REGISTRATION_MODE_KEY not in st.session_state:
        st.session_state[
            JOB_REGISTRATION_MODE_KEY
        ] = ""

    if JOB_FORM_STEP_KEY not in st.session_state:
        st.session_state[
            JOB_FORM_STEP_KEY
        ] = "select"

    if JOB_EDIT_ID_KEY not in st.session_state:
        st.session_state[
            JOB_EDIT_ID_KEY
        ] = None

    current_step = st.session_state[
        JOB_FORM_STEP_KEY
    ]

    if current_step == "form":
        render_job_form()
        return

    if current_step == "confirm":
        render_job_confirmation()
        return

    if current_step == "complete":
        render_job_completion()
        return

    if current_step == "duplicate":
        render_duplicate_confirmation()
        return

    if current_step == "source":
        # 旧状態から、新しい同一画面内入力へ移行する。
        st.session_state[JOB_FORM_STEP_KEY] = "select"
        st.rerun()

    st.markdown(
        """
        <a class="job-list-back-link" href="?page=job_list" target="_self">
            ← 求人一覧に戻る
        </a>
        """,
        unsafe_allow_html=True,
    )

    selected_mode = st.session_state.get(
        JOB_REGISTRATION_MODE_KEY,
        "",
    )

    registration_col, guide_col = st.columns(
        [3.1, 1.25],
        gap="large",
    )

    with registration_col:
        with st.container(border=True):
            st.markdown(
                """
                <div class="job-registration-shell-marker"></div>
                <div class="job-page-title">
                    求人を登録する
                </div>
                <div class="job-page-description">
                    気になる求人を、あなたに合った方法で登録できます。
                    AIが整理した内容は、保存する前に確認・修正できます。
                </div>
                """,
                unsafe_allow_html=True,
            )
            render_registration_progress(
                2 if selected_mode in {"pdf", "text", "url"} else 1
            )
            render_method_selection()

    with guide_col:
        render_registration_method_guide()
