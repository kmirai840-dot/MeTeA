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
    extract_text_from_pdf,
    parse_career_document,
)
from ui.design_system import render_field_error as render_common_field_error
from ui.design_system import render_save_failure, render_validation_summary


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
CAREER_ACTIVE_ERRORS_KEY = "career_active_errors"


def save_career_with_feedback(
    career_items: list[tuple[Career, list[CareerHistory]]],
) -> tuple[list[str], bool]:
    """職務経歴を保存し、システム上の失敗は共通通知で案内する。"""

    try:
        return save_career_data(career_items), False
    except Exception:
        render_save_failure(
            "職務経歴・スキル",
            recovery="入力中の内容は画面に残っています。時間をおいて、もう一度保存してください。",
        )
        return [], True


def apply_career_page_styles(errors: list[str]) -> None:
    """他の「自分を知る」画面と同じレスポンシブ表示を適用する。"""

    field_error_css = ""
    if any("会社名" in message for message in errors):
        field_error_css += (
            '.st-key-career_company_name [data-baseweb="input"]'
            '{border:1.5px solid #ef4444!important;'
            'box-shadow:0 0 0 1px rgba(239,68,68,.08)!important;}'
        )
    if any("業種" in message for message in errors):
        field_error_css += (
            '.st-key-career_industry [data-baseweb="input"]'
            '{border:1.5px solid #ef4444!important;'
            'box-shadow:0 0 0 1px rgba(239,68,68,.08)!important;}'
        )
    if any("職種" in message for message in errors):
        field_error_css += (
            '.st-key-career_occupation [data-baseweb="input"],'
            'div[class*="st-key-career_ai_occupation_"] [data-baseweb="input"]'
            '{border:1.5px solid #ef4444!important;'
            'box-shadow:0 0 0 1px rgba(239,68,68,.08)!important;}'
        )

    st.markdown(
        """
        <span class="metea-career-page-marker"></span>
        <style>
        [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker) {
          width:calc(100vw - 272px);max-width:none;height:calc(100dvh - 84px);
          margin:66px 28px 18px 244px;padding:14px 30px 20px;overflow-y:auto;
          background:#fff;border:1px solid var(--metea-line);border-radius:18px;
          box-shadow:var(--metea-shadow);
        }
        [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker)>
        [data-testid="stVerticalBlock"] {gap:.68rem;}
        [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker) h1 {
          padding:0!important;margin:0 0 .7rem!important;font-size:2.25rem;line-height:1.18;
        }
        [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker) h2,
        [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker) h3 {
          padding:0!important;margin:.25rem 0 .35rem!important;line-height:1.28;
        }
        [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker) hr {margin:.6rem 0;}
        [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker)
        [data-testid="stVerticalBlockBorderWrapper"] {
          border:1px solid #d6e1ef!important;border-radius:12px!important;
          box-shadow:0 4px 12px rgba(31,65,114,.055);overflow:hidden;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-method-illustration) {
          min-height:285px;padding:8px!important;
        }
        .metea-method-illustration {margin-bottom:8px!important;}
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-method-section-marker) {
          padding:14px 14px 16px!important;background:#fff!important;
          border:1px solid #cbd9ea!important;border-radius:14px!important;
          box-shadow:0 5px 16px rgba(31,65,114,.06)!important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-method-section-marker) h2 {
          margin-top:0!important;
        }
        .metea-career-method-title {
          margin:0 0 4px;color:#146cff;font-size:1.12rem;line-height:1.4;font-weight:800;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        >[data-testid="stColumn"] {
          display:flex;align-self:stretch;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        >[data-testid="stColumn"]>[data-testid="stVerticalBlock"] {
          width:100%;height:100%;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        >[data-testid="stColumn"]>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]:has(.metea-method-illustration) {
          display:flex;height:100%!important;flex:1;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        >[data-testid="stColumn"]>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]:has(.metea-method-illustration--upload) {
          background:#f3f8ff!important;border:1.5px solid #7fb2ff!important;
          border-radius:13px!important;box-shadow:0 5px 14px rgba(20,108,255,.08)!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        >[data-testid="stColumn"]>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]:has(.metea-method-illustration--manual) {
          background:#fff8ef!important;border:1.5px solid #f1b56e!important;
          border-radius:13px!important;box-shadow:0 5px 14px rgba(238,126,34,.08)!important;
        }
        [data-testid="stLayoutWrapper"]:has(.metea-career-method-section-marker) {
          background:#fff!important;border-color:#cbd9ea!important;
          box-shadow:0 5px 16px rgba(31,65,114,.06)!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-career-method-section-marker)
        >[data-testid="stColumn"]:first-child>[data-testid="stVerticalBlock"]
        >[data-testid="stLayoutWrapper"]:has(.metea-career-method-section-marker) {
          background:#fff!important;border:1px solid #cbd9ea!important;
          box-shadow:0 5px 16px rgba(31,65,114,.06)!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-career-method-section-marker)
        >[data-testid="stColumn"]:first-child>[data-testid="stVerticalBlock"]
        >[data-testid="stLayoutWrapper"]:has(.metea-career-method-section-marker)
        >[data-testid="stVerticalBlock"] {
          display:flex!important;flex-direction:column!important;justify-content:flex-start!important;
          min-height:0!important;gap:.68rem!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-career-method-section-marker)
        >[data-testid="stColumn"]:first-child>[data-testid="stVerticalBlock"]
        >[data-testid="stLayoutWrapper"]:has(.metea-career-method-section-marker)
        >[data-testid="stVerticalBlock"]>* {
          grid-column:auto!important;grid-row:auto!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        >[data-testid="stColumn"]>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]
        >[data-testid="stVerticalBlock"]:has(.metea-method-illustration) {
          position:relative;display:grid;grid-template-columns:64px minmax(0,1fr);align-content:center;
          column-gap:12px;row-gap:.72rem!important;
          width:100%;height:100%!important;min-height:356px!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        [data-testid="stVerticalBlock"]:has(.metea-method-illustration)>:nth-child(1) {
          grid-column:1;grid-row:1;align-self:center;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        [data-testid="stVerticalBlock"]:has(.metea-method-illustration)>:nth-child(2) {
          grid-column:2;grid-row:1;align-self:center;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        [data-testid="stVerticalBlock"]:has(.metea-method-illustration)>:nth-child(n+3) {
          grid-column:1 / -1;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        [data-testid="stVerticalBlock"]:has(.metea-method-illustration) h3 {
          margin:.18rem 0 .32rem!important;line-height:1.3!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        .metea-method-illustration {
          margin:0!important;transform:none;
        }
        .metea-method-illustration svg {display:block;width:34px;height:34px;}
        .metea-method-heading {display:block;min-width:0;}
        .metea-method-heading h3 {margin:0!important;font-size:1.08rem!important;line-height:1.35!important;}
        .metea-method-recommended {
          position:absolute;top:10px;right:10px;display:inline-flex;align-items:center;padding:3px 8px;
          border:1px solid #8cbcff;border-radius:999px;background:#fff;color:#146cff;
          font-size:.72rem;font-weight:800;line-height:1.2;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        [data-testid="stCaptionContainer"] {
          color:#667085!important;line-height:1.55!important;
        }
        [data-testid="stHorizontalBlock"]:has(.metea-method-illustration--upload):has(.metea-method-illustration--manual)
        [data-testid="stFileUploaderDropzone"] {
          height:66px!important;min-height:66px!important;padding:.25rem .6rem!important;
        }
        .metea-career-guide {margin-top:6px!important;padding:13px!important;border-radius:12px!important;box-shadow:none!important;}
        .metea-career-guide ul {margin-top:6px!important;}
        .metea-career-guide li {margin:2px 0!important;}
        .metea-career-guide p {margin-top:6px!important;line-height:1.55!important;}
        .metea-career-ai-results-marker {display:none;}
        [data-testid="stLayoutWrapper"]:has(.metea-career-ai-results-marker) {
          margin-top:14px;background:#fff!important;border:1px solid #bdd4f6!important;
          border-radius:14px!important;box-shadow:0 5px 16px rgba(31,65,114,.06)!important;
        }
        .metea-career-ai-results-title {margin:0;color:#0b2b55;font-size:1.14rem;font-weight:800;}
        .metea-career-ai-compact-status {
          display:flex;align-items:center;gap:8px;padding:9px 11px;
          border:1px solid #b7d3ff;border-radius:10px;background:#edf5ff;
          color:#0c57c7;font-size:.9rem;font-weight:700;line-height:1.4;
        }
        .metea-career-ai-compact-status>span {
          display:grid;place-items:center;flex:0 0 20px;height:20px;border-radius:50%;
          background:#146cff;color:#fff;font-size:.75rem;font-weight:900;
        }
        [data-testid="stExpander"]:has(.metea-career-ai-result-item-marker) {
          margin:5px 0!important;overflow:hidden!important;background:#fff!important;
          border:1px solid #cfdaea!important;border-radius:12px!important;
          box-shadow:0 3px 10px rgba(31,65,114,.05)!important;
        }
        [data-testid="stExpander"]:has(.metea-career-ai-result-item-marker) details,
        [data-testid="stExpander"]:has(.metea-career-ai-result-item-marker) summary {
          border-radius:11px!important;
        }
        [data-testid="stExpander"]:has(.metea-career-ai-result-item-marker) summary {
          min-height:44px;padding:8px 12px!important;background:#fff!important;
        }
        [data-testid="stExpander"]:has(.metea-career-ai-result-item-marker) details[open] summary {
          border-radius:11px 11px 0 0!important;border-bottom:1px solid #e2e8f0!important;
        }
        .st-key-career_ai_apply button {
          color:#fff!important;background:#146cff!important;border-color:#146cff!important;
          font-weight:800!important;box-shadow:0 4px 12px rgba(20,108,255,.15)!important;
        }
        .metea-career-review-marker,.metea-career-review-company-marker,
        .metea-career-review-history-marker {display:none;}
        .metea-career-review-progress {
          display:flex;align-items:center;gap:8px;margin:.1rem 0 .25rem;color:#64748b;font-size:.86rem;
        }
        .metea-career-review-progress b {
          display:inline-flex;padding:4px 10px;border-radius:999px;background:#e8f2ff;color:#146cff;font-weight:800;
        }
        .metea-career-review-notice {
          display:flex;flex-direction:column;gap:3px;margin:.45rem 0 .75rem;padding:12px 14px;
          border:1px solid #b7d3ff;border-radius:12px;background:#f3f8ff;color:#24466f;
        }
        .metea-career-review-notice b {color:#0b2b55;font-size:.96rem;}
        .metea-career-review-notice span {font-size:.88rem;line-height:1.55;}
        .metea-career-review-notice--warning {
          border-color:#ffc5c9;background:#fff7f7;color:#5f3540;
          box-shadow:0 3px 10px rgba(220,53,69,.05);
        }
        .metea-career-review-notice--warning b {color:#dc3545;}
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-review-history-marker) {
          margin:.45rem 0!important;padding:14px 16px!important;background:#fff!important;
          border:1px solid #cfdaea!important;border-radius:12px!important;
          box-shadow:0 3px 10px rgba(31,65,114,.05)!important;overflow:visible!important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-review-company-marker) {
          margin:.2rem 0 .7rem!important;padding:14px 16px!important;background:#fff!important;
          border:1px solid #cfdaea!important;border-radius:12px!important;
          box-shadow:0 3px 10px rgba(31,65,114,.05)!important;overflow:visible!important;
        }
        .metea-career-final-review-marker,.metea-career-final-company-marker,
        .metea-career-final-history-marker {display:none;}
        .metea-career-review-overview {
          display:grid;grid-template-columns:repeat(3,minmax(120px,.7fr)) minmax(280px,2fr);
          gap:10px;margin:.35rem 0 1rem;
        }
        .metea-career-review-overview>div {
          display:flex;flex-direction:column;justify-content:center;gap:4px;min-height:76px;
          padding:12px 14px;border:1px solid #cbdcf3;border-radius:12px;background:#f7faff;
        }
        .metea-career-review-overview span {color:#64748b;font-size:.8rem;}
        .metea-career-review-overview b {color:#0b2b55;font-size:1.12rem;}
        .metea-career-review-overview b.is-complete {color:#146cff;}
        .metea-career-review-overview b.is-warning {color:#dc3545;}
        .metea-career-review-overview .metea-career-review-guide {
          background:#edf5ff;border-color:#b7d3ff;
        }
        .metea-career-review-guide b {font-size:.94rem;}
        .metea-career-review-guide span {font-size:.84rem;line-height:1.5;}
        [data-testid="stExpander"]:has(.metea-career-final-company-marker) {
          margin:.65rem 0!important;overflow:hidden!important;background:#fff!important;
          border:1px solid #cfdaea!important;border-radius:12px!important;
          box-shadow:0 4px 12px rgba(31,65,114,.055)!important;
        }
        [data-testid="stExpander"]:has(.metea-career-final-company-marker) summary {
          min-height:48px;padding:9px 13px!important;background:#fff!important;
          border-radius:11px!important;font-weight:700!important;
        }
        [data-testid="stExpander"]:has(.metea-career-final-company-marker) details[open] summary {
          border-radius:11px 11px 0 0!important;border-bottom:1px solid #e2e8f0!important;
        }
        .metea-career-review-tags {display:flex;flex-wrap:wrap;align-items:center;gap:7px;min-height:38px;}
        .metea-career-review-tags span {
          display:inline-flex;padding:4px 9px;border-radius:999px;background:#edf3fb;color:#385470;
          font-size:.78rem;font-weight:700;
        }
        .metea-career-review-tags span.is-current {background:#eef0ff;color:#5264d6;}
        .metea-career-review-tags span.is-complete {background:#e8f2ff;color:#146cff;}
        .metea-career-review-section-title {
          margin:12px 0 7px;padding-left:9px;border-left:3px solid #146cff;
          color:#0b2b55;font-size:.95rem;font-weight:800;
        }
        [data-testid="stExpander"]:has(.metea-career-final-company-marker) [data-testid="stColumn"] small {
          display:block;margin-bottom:3px;color:#718096;font-size:.76rem;
        }
        [data-testid="stExpander"]:has(.metea-career-final-company-marker) [data-testid="stColumn"] strong {
          display:block;color:#0b2b55;font-size:.9rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-final-history-marker) {
          margin:.45rem 0!important;padding:12px 14px!important;background:#fbfdff!important;
          border:1px solid #d6e1ef!important;border-radius:11px!important;
          box-shadow:none!important;overflow:visible!important;
        }
        .metea-career-review-history-heading {display:flex;align-items:center;gap:9px;margin-bottom:5px;}
        .metea-career-review-history-heading>b {
          display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#e8f2ff;
          color:#146cff;font-size:.76rem;
        }
        .metea-career-review-history-heading>strong {color:#0b2b55;font-size:.95rem;}
        .metea-career-review-history-heading>span {margin-left:auto;color:#718096;font-size:.78rem;}
        .metea-career-complete-notice {
          display:flex;align-items:center;gap:10px;margin:.65rem 0;padding:13px 15px;
          border:1px solid #b7d3ff;border-radius:12px;background:#edf5ff;color:#0b2b55;
          font-weight:800;box-shadow:0 3px 10px rgba(20,108,255,.06);
        }
        .metea-career-complete-notice>span {
          display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#146cff;
          color:#fff;font-size:.8rem;
        }
        .metea-career-manual-form-marker,.metea-career-manual-company-marker,
        .metea-career-manual-history-marker,.metea-career-manual-history-form-marker {display:none;}
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-manual-company-marker),
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-manual-history-form-marker) {
          margin:.35rem 0 .75rem!important;padding:14px 16px!important;background:#fff!important;
          border:1px solid #cfdaea!important;border-radius:12px!important;
          box-shadow:0 3px 10px rgba(31,65,114,.05)!important;overflow:visible!important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-manual-history-marker) {
          margin:.45rem 0!important;padding:12px 14px!important;background:#fbfdff!important;
          border:1px solid #d6e1ef!important;border-radius:11px!important;
          box-shadow:none!important;overflow:visible!important;
        }
        .metea-career-form-subtitle {
          margin:10px 0 6px;padding-left:9px;border-left:3px solid #146cff;
          color:#0b2b55;font-size:.9rem;font-weight:800;
        }
        .metea-career-empty-notice {
          margin:.4rem 0 .75rem;padding:11px 13px;border:1px solid #d6e1ef;border-radius:11px;
          background:#f7faff;color:#52657c;font-size:.88rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-career-review-history-marker) h4 {
          color:#0b2b55!important;font-size:1.05rem!important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-method-illustration--upload),
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-method-illustration--manual) {
          background:#f7fbff!important;border-color:#bed8ff!important;
        }
        .st-key-career_manual button {
          color:#df741c!important;background:#fffaf5!important;border:1.5px solid #e99a4d!important;
          font-weight:800;box-shadow:0 3px 10px rgba(223,116,28,.10);
        }
        [data-testid="stExpander"]:has(.metea-career-company-marker) {
          margin-bottom:4px;overflow:hidden;border:1px solid #cfdaea!important;
          border-radius:12px!important;background:#fff;
          box-shadow:0 4px 12px rgba(31,65,114,.055);
        }
        [data-testid="stExpander"]:has(.metea-career-company-marker) details,
        [data-testid="stExpander"]:has(.metea-career-company-marker) summary {
          border-radius:11px!important;
        }
        [data-testid="stExpander"]:has(.metea-career-company-marker) details[open] summary {
          border-radius:11px 11px 0 0!important;
        }
        [data-testid="stExpander"]:has(.metea-career-company-marker) summary {
          min-height:44px;padding:8px 10px!important;background:#fff;
        }
        div[class*="st-key-career_delete_"] button,
        div[class*="st-key-career_history_delete_"] button {
          color:#dc3545!important;border-color:#ffc3c8!important;background:#fff8f8!important;
        }
        .st-key-career_add_company_top button {
          color:#0c57c7!important;background:#eaf3ff!important;border-color:#75aaff!important;
          font-weight:700!important;
        }
        .metea-career-error-summary {display:flex;gap:11px;margin:12px 0;padding:13px 15px;
          border:1px solid #ff9b9b;border-radius:12px;background:#fff6f6;color:#dc2626;}
        .metea-career-error-summary>span {display:grid;place-items:center;flex:0 0 24px;height:24px;
          border:2px solid #ef4444;border-radius:7px;font-weight:800;}
        .metea-career-error-summary ul {margin:6px 0 0;padding-left:20px;}
        __FIELD_ERROR_CSS__
        @media(max-width:1100px) {
          [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker) {
            width:calc(100vw - 228px);margin-left:202px;padding:14px 22px 18px;
          }
        }
        @media(max-width:700px) {
          [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker) {
            width:calc(100vw - 20px);height:auto;min-height:calc(100dvh - 78px);
            margin:70px 10px 12px;padding:16px 14px;border-radius:14px;overflow:visible;
          }
          [data-testid="stMainBlockContainer"]:has(.metea-career-page-marker)
          [data-testid="stHorizontalBlock"] {flex-wrap:wrap;}
          [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-method-illustration) {min-height:auto;}
          .metea-career-review-overview {grid-template-columns:repeat(2,minmax(0,1fr));}
          .metea-career-review-overview .metea-career-review-guide {grid-column:1/-1;}
        }
        </style>
        """.replace("__FIELD_ERROR_CSS__", field_error_css),
        unsafe_allow_html=True,
    )


def render_career_error_summary(errors: list[str]) -> None:
    """入力エラーを画面上部へまとめて表示する。"""

    render_validation_summary(errors)


def render_career_field_error(keyword: str) -> None:
    """該当入力欄の直下へ個別エラーを表示する。"""

    errors = st.session_state.get(CAREER_ACTIVE_ERRORS_KEY, [])
    message = next((item for item in errors if keyword in item), None)
    if message:
        render_common_field_error(message)

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

    st.session_state["career_history_start_year"] = 2020
    st.session_state["career_history_start_month"] = 4
    st.session_state["career_history_end_year"] = 2025
    st.session_state["career_history_end_month"] = 10
    st.session_state["career_history_is_current"] = False

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
        "career_history_is_current",
        False,
    )

    end_year = None
    end_month = None

    if not is_current:
        end_year = st.session_state.get(
            "career_history_end_year"
        )

        end_month = st.session_state.get(
            "career_history_end_month"
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
            "career_history_start_year",
            2020,
        ),
        start_month=st.session_state.get(
            "career_history_start_month",
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
        "career_ai_start_year_",
        "career_ai_start_month_",
        "career_ai_end_year_",
        "career_ai_end_month_",
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
            start_year=st.session_state.get(
                f"career_ai_start_year_{review_index}_{index}", history.start_year
            ),
            start_month=st.session_state.get(
                f"career_ai_start_month_{review_index}_{index}", history.start_month
            ),
            end_year=st.session_state.get(
                f"career_ai_end_year_{review_index}_{index}", history.end_year
            ),
            end_month=st.session_state.get(
                f"career_ai_end_month_{review_index}_{index}", history.end_month
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

    st.session_state["career_history_start_year"] = history.start_year or 2020
    st.session_state["career_history_start_month"] = history.start_month or 4
    st.session_state["career_history_end_year"] = history.end_year or 2025
    st.session_state["career_history_end_month"] = history.end_month or 10
    st.session_state["career_history_is_current"] = history.end_year is None

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

    st.session_state[
        CAREER_ITEMS_KEY
    ] = career_items

    if ai_reviewing:

        save_errors, save_failed = save_career_with_feedback(
            career_items
        )

        if save_failed:
            return

        if save_errors:
            st.session_state[CAREER_ERRORS_KEY] = save_errors
            return

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

    st.session_state[CAREER_MESSAGE_KEY] = (
        "会社情報を入力内容へ追加しました。正式登録前に内容を確認してください。"
    )

    st.session_state[
        CAREER_COMPLETE_KEY
    ] = True

    st.session_state[
        CAREER_REVIEW_CONFIRMED_KEY
    ] = False

    st.session_state[
        CAREER_SCROLL_TO_FORM_KEY
    ] = True


def finalize_career_registration() -> None:
    """確認済みの職務経歴をDBへ正式保存する。"""

    career_items = list(st.session_state.get(CAREER_ITEMS_KEY, []))
    save_errors, save_failed = save_career_with_feedback(career_items)

    if save_failed:
        st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = False
        return

    if save_errors:
        st.session_state[CAREER_ERRORS_KEY] = save_errors
        st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = False
        return

    st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = True


def add_company_from_review() -> None:
    """最終確認から会社追加フォームへ戻る。"""

    reset_current_career_form_state()
    st.session_state[CAREER_COMPLETE_KEY] = False
    st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = False
    st.session_state[CAREER_SCROLL_TO_FORM_KEY] = True


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

    save_errors, save_failed = save_career_with_feedback(
        updated_items
    )

    if save_failed:
        return

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
        "職種 :red[*]",
        placeholder="例：業務企画",
        key="career_occupation",
    )
    render_career_field_error("職種")

    st.markdown('<div class="metea-career-form-subtitle">この部署・役割の担当期間</div>', unsafe_allow_html=True)
    period_columns = st.columns(2)
    with period_columns[0]:
        start_columns = st.columns(2)
        with start_columns[0]:
            st.number_input("開始年", min_value=1950, max_value=2100, key="career_history_start_year")
        with start_columns[1]:
            st.number_input("開始月", min_value=1, max_value=12, key="career_history_start_month")
    with period_columns[1]:
        is_current = st.checkbox("現在まで担当", key="career_history_is_current")
        if not is_current:
            end_columns = st.columns(2)
            with end_columns[0]:
                st.number_input("終了年", min_value=1950, max_value=2100, key="career_history_end_year")
            with end_columns[1]:
                st.number_input("終了月", min_value=1, max_value=12, key="career_history_end_month")

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
            st.markdown('<span class="metea-career-manual-history-marker"></span>', unsafe_allow_html=True)

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

            history_end = (
                "現在"
                if history.end_year is None
                else f"{history.end_year}/{history.end_month}"
            )
            st.caption(
                f"担当期間：{history.start_year}/{history.start_month} ～ {history_end}"
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
        st.markdown(
            '<div class="metea-career-review-notice metea-career-review-notice--warning">'
            '<b>部署・役割を確認できませんでした</b>'
            '<span>部署・役割を1件以上入力してください。</span></div>',
            unsafe_allow_html=True,
        )
        return

    st.caption("AIが読み取った内容を確認してください。すべての項目をこの画面で直接修正できます。")

    for index, history in enumerate(
        histories,
        start=1,
    ):

        with st.container(
            border=True
        ):
            st.markdown('<span class="metea-career-review-history-marker"></span>', unsafe_allow_html=True)

            department_name = (
                history.department
                or "部署名未入力"
            )

            st.markdown(
                f"#### {index}. "
                f"{department_name}"
            )

            identity_columns = st.columns(3)
            with identity_columns[0]:
                st.text_input("部署名", value=history.department, key=f"career_ai_department_{review_index}_{index}")
            with identity_columns[1]:
                st.text_input("役職", value=history.position, key=f"career_ai_position_{review_index}_{index}")
            with identity_columns[2]:
                st.text_input("職種 :red[*]", value=history.occupation, key=f"career_ai_occupation_{review_index}_{index}")
            render_career_field_error("職種")

            year_options = [None, *range(1950, 2101)]
            month_options = [None, *range(1, 13)]
            format_period = lambda value: "未設定" if value is None else str(value)
            period_columns = st.columns(4)
            with period_columns[0]:
                st.selectbox("開始年", year_options, index=year_options.index(history.start_year) if history.start_year in year_options else 0, format_func=format_period, key=f"career_ai_start_year_{review_index}_{index}")
            with period_columns[1]:
                st.selectbox("開始月", month_options, index=month_options.index(history.start_month) if history.start_month in month_options else 0, format_func=format_period, key=f"career_ai_start_month_{review_index}_{index}")
            with period_columns[2]:
                st.selectbox("終了年", year_options, index=year_options.index(history.end_year) if history.end_year in year_options else 0, format_func=format_period, key=f"career_ai_end_year_{review_index}_{index}")
            with period_columns[3]:
                st.selectbox("終了月", month_options, index=month_options.index(history.end_month) if history.end_month in month_options else 0, format_func=format_period, key=f"career_ai_end_month_{review_index}_{index}")

            st.text_area(
                "業務内容",
                value=(
                    history.job_description
                ),
                max_chars=1000,
                height=112,
                key=(
                    "career_ai_job_description_"
                    f"{review_index}_{index}"
                ),
            )

            st.text_area(
                "実績・成果",
                value=history.achievements,
                max_chars=1000,
                height=112,
                key=(
                    "career_ai_achievements_"
                    f"{review_index}_{index}"
                ),
            )


def render_company_form(ai_reviewing: bool) -> None:
    """会社情報を共通カード内に表示する。"""

    wrapper = st.container(border=True)
    with wrapper:
        if ai_reviewing:
            st.markdown('<span class="metea-career-review-company-marker"></span>', unsafe_allow_html=True)
            st.markdown("#### 会社情報")
        else:
            st.markdown('<span class="metea-career-manual-company-marker"></span>', unsafe_allow_html=True)
            st.markdown("#### 会社情報")
            st.caption("勤務先の基本情報と在籍期間を入力してください。")

        st.text_input("会社名 :red[*]", key="career_company_name")
        render_career_field_error("会社名")

        detail_columns = st.columns(2)
        with detail_columns[0]:
            st.selectbox(
                "雇用形態",
                ["正社員", "契約社員", "派遣社員", "アルバイト", "その他"],
                key="career_employment_type",
            )
        with detail_columns[1]:
            st.text_input(
                "業種 :red[*]",
                placeholder="例：金融・クレジットカード",
                key="career_industry",
            )
            render_career_field_error("業種")

        start_columns = st.columns(2)
        with start_columns[0]:
            st.number_input("入社年", min_value=1950, max_value=2100, key="career_start_year")
        with start_columns[1]:
            st.number_input("入社月", min_value=1, max_value=12, key="career_start_month")

        is_current = st.checkbox("現在も在職中", key="career_is_current")
        if not is_current:
            end_columns = st.columns(2)
            with end_columns[0]:
                st.number_input("退社年", min_value=1950, max_value=2100, key="career_end_year")
            with end_columns[1]:
                st.number_input("退社月", min_value=1, max_value=12, key="career_end_month")


# ==========================================
# 登録済み会社一覧
# ==========================================

def render_company_list() -> None:
    """登録済み会社一覧を表示する。"""

    career_items = st.session_state.get(
        CAREER_ITEMS_KEY,
        [],
    )

    header_left, header_mode, header_right = (
        st.columns(
            [3, 1.2, 1]
        )
    )

    with header_left:
        st.subheader(
            "登録済みの会社"
        )

    with header_mode:
        if st.button(
            "登録方法を変更",
            key="career_change_entry_mode",
            use_container_width=True,
        ):
            st.session_state[CAREER_ENTRY_MODE_KEY] = None
            st.rerun()

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
        st.markdown(
            '<div class="metea-career-empty-notice">まだ会社は登録されていません。'
            '「会社を追加」から最初の職務経歴を登録してください。</div>',
            unsafe_allow_html=True,
        )
        return

    for index, (
        career,
        histories,
    ) in enumerate(
        career_items,
        start=1,
    ):
        if career.is_current:
            period = f"{career.start_year}/{career.start_month} ～ 現在"
        else:
            period = (
                f"{career.start_year}/{career.start_month} ～ "
                f"{career.end_year}/{career.end_month}"
            )

        with st.expander(f"{career.company_name}　{period}"):
            st.markdown(
                '<span class="metea-career-company-marker"></span>',
                unsafe_allow_html=True,
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
                    icon=":material/edit:",
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
                    icon=":material/delete_outline:",
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

    from html import escape

    career_items = st.session_state.get(CAREER_ITEMS_KEY, [])
    history_count = sum(len(histories) for _, histories in career_items)
    review_errors = validate_careers(career_items)
    status_label = "要確認" if review_errors else "入力済み"
    status_class = "is-warning" if review_errors else "is-complete"

    st.markdown(
        '<span class="metea-career-final-review-marker"></span>'
        '<div class="metea-career-review-overview">'
        f'<div><span>登録企業</span><b>{len(career_items)}社</b></div>'
        f'<div><span>部署・役割</span><b>{history_count}件</b></div>'
        f'<div><span>必須項目</span><b class="{status_class}">{status_label}</b></div>'
        '<div class="metea-career-review-guide"><b>最終確認</b>'
        '<span>会社ごとに内容を確認し、問題がなければ登録を完了してください。</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if review_errors:
        render_career_error_summary(review_errors)

    for company_index, (career, histories) in enumerate(career_items):
        period_end = "現在" if career.is_current else f"{career.end_year}/{career.end_month}"
        period = f"{career.start_year}/{career.start_month} ～ {period_end}"
        company_label = f"{career.company_name}　｜　{period}　｜　部署・役割 {len(histories)}件"

        with st.expander(company_label, expanded=company_index == 0):
            st.markdown('<span class="metea-career-final-company-marker"></span>', unsafe_allow_html=True)

            header_columns = st.columns([4, 1])
            with header_columns[0]:
                tags = "".join(
                    f'<span>{escape(value)}</span>'
                    for value in (career.employment_type, career.industry)
                    if value
                )

                current_tag = '<span class="is-current">在職中</span>' if career.is_current else ""
                st.markdown(
                    f'<div class="metea-career-review-tags">{tags}{current_tag}'
                    '<span class="is-complete">確認可能</span></div>',
                    unsafe_allow_html=True,
                )
            with header_columns[1]:
                if st.button(
                    "編集する",
                    key=f"career_review_edit_{company_index}",
                    use_container_width=True,
                ):
                    st.session_state[CAREER_COMPLETE_KEY] = False
                    st.session_state[CAREER_REVIEW_CONFIRMED_KEY] = False
                    load_company_for_edit(company_index)
                    st.rerun()

            st.markdown('<div class="metea-career-review-section-title">会社情報</div>', unsafe_allow_html=True)
            company_details = st.columns(3)
            company_details[0].markdown(f"<small>雇用形態</small><strong>{escape(career.employment_type or '未設定')}</strong>", unsafe_allow_html=True)
            company_details[1].markdown(f"<small>業種</small><strong>{escape(career.industry or '未設定')}</strong>", unsafe_allow_html=True)
            company_details[2].markdown(f"<small>在籍期間</small><strong>{escape(period)}</strong>", unsafe_allow_html=True)

            st.markdown('<div class="metea-career-review-section-title">部署・役割</div>', unsafe_allow_html=True)
            for history_index, history in enumerate(histories, start=1):
                history_end = (
                    f"{history.end_year}/{history.end_month}"
                    if history.end_year and history.end_month
                    else "現在・未設定"
                )
                history_period = (
                    f"{history.start_year}/{history.start_month} ～ {history_end}"
                    if history.start_year and history.start_month
                    else "期間未設定"
                )
                with st.container(border=True):
                    st.markdown('<span class="metea-career-final-history-marker"></span>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="metea-career-review-history-heading"><b>{history_index}</b>'
                        f'<strong>{escape(history.occupation or "職種未設定")}</strong>'
                        f'<span>{escape(history_period)}</span></div>',
                        unsafe_allow_html=True,
                    )
                    identity = " / ".join(
                        value for value in (history.department, history.position) if value
                    )
                    if identity:
                        st.caption(identity)
                    detail_columns = st.columns(2)
                    with detail_columns[0]:
                        st.markdown("**業務内容**")
                        st.write(history.job_description or "未入力")
                    with detail_columns[1]:
                        st.markdown("**実績・成果**")
                        st.write(history.achievements or "未入力")

# ==========================================
# 職務経歴画面
# ==========================================

def show_page() -> None:
    """職務経歴入力画面を表示する。"""

    apply_self_discovery_theme(current_step=5)

    initialize_career_state()

    # 確認画面の「PDF・Wordから取り込む」から来た場合は、保存済みの
    # 職務経歴を維持したまま登録方法の選択画面を表示する。
    if st.query_params.get("entry") == "document":
        st.session_state[CAREER_ENTRY_MODE_KEY] = None
        st.query_params.pop("entry", None)

    career_errors = st.session_state.pop(CAREER_ERRORS_KEY, [])
    st.session_state[CAREER_ACTIVE_ERRORS_KEY] = career_errors
    apply_career_page_styles(career_errors)

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

    st.caption(
        "これまでの職務経歴を会社ごとに登録します。"
    )

    st.caption(
        "既に職務経歴書をお持ちの方はアップロード、"
        "初めて作成する方は手入力がおすすめです。"
    )

    st.progress(
        1.0,
        text="自分を知る 5 / 5　職務経歴・スキル",
    )

    render_career_error_summary(career_errors)

    # ======================================
    # 登録方法選択
    # ======================================

    entry_mode = st.session_state.get(
        CAREER_ENTRY_MODE_KEY
    )

    if entry_mode is None:

        main_method_col, guidance_col = st.columns([2.5, 1])
        method_section = main_method_col.container(border=True)
        method_section.markdown(
            '<span class="metea-career-method-section-marker"></span>',
            unsafe_allow_html=True,
        )

        method_section.markdown(
            '<div class="metea-career-method-title">登録方法を選択してください</div>',
            unsafe_allow_html=True,
        )

        upload_col, manual_col = (
            method_section.columns(2)
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
                    "aria-hidden='true'><svg viewBox='0 0 40 40' fill='none' "
                    "xmlns='http://www.w3.org/2000/svg'><path d='M10 4h14l7 7v25H10V4Z' "
                    "stroke='#146CFF' stroke-width='2.6' stroke-linejoin='round'/>"
                    "<path d='M24 4v8h7M15 19h11M15 25h11M15 31h8' stroke='#146CFF' "
                    "stroke-width='2.3' stroke-linecap='round'/></svg></div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "<div class='metea-method-heading'><h3>職務経歴書から取り込む</h3>"
                    "<span class='metea-method-recommended'>おすすめ</span></div>",
                    unsafe_allow_html=True,
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

                st.markdown(
                    """
                    <div style="position:relative;margin:12px 0 15px;padding:13px 15px 13px 46px;
                                border:1px solid #f4bd72;border-radius:12px;background:#fff8ee;
                                color:#74430a;line-height:1.65;">
                        <span aria-hidden="true" style="position:absolute;top:14px;left:16px;
                              display:grid;place-items:center;width:20px;height:20px;border:2px solid #e98a22;
                              border-radius:50%;color:#d97400;font-size:13px;font-weight:900;line-height:1;">!</span>
                        <div style="font-weight:700;color:#9a5708;margin-bottom:3px;">PDFの文字情報について</div>
                        <div style="font-size:0.9rem;">
                            画像として保存・スキャンされたPDFは読み取れません。
                            文字を選択・コピーできる状態のPDFをご利用ください。
                            文字を選択できない場合は、文字情報を含むPDFまたはWordファイルへ変換してからお試しください。
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
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

                    read_failed = False
                    try:
                        if file_name.endswith(".docx"):
                            extracted_text = extract_text_from_docx(
                                uploaded_career_file
                            )
                            file_type_label = "Word"
                        else:
                            extracted_text = extract_text_from_pdf(
                                uploaded_career_file
                            )
                            file_type_label = "PDF"
                    except Exception:
                        read_failed = True
                        extracted_text = ""
                        st.markdown(
                            '<div class="metea-career-review-notice metea-career-review-notice--warning">'
                            '<b>ファイルを読み取れませんでした</b>'
                            '<span>破損していないPDFまたはWordファイルか確認してください。</span></div>',
                            unsafe_allow_html=True,
                        )

                    if not extracted_text.strip() and not read_failed:
                        st.markdown(
                            '<div class="metea-career-review-notice"><b>文字情報を取得できませんでした</b>'
                            '<span>文字を選択・コピーできるPDF、または文字情報を含むWordファイルへ変換してから再度お試しください。</span></div>',
                            unsafe_allow_html=True,
                        )
                    elif extracted_text.strip():
                        parsed_careers = st.session_state.get("career_ai_parsed", [])
                        if parsed_careers:
                            st.markdown(
                                '<div class="metea-career-ai-compact-status">'
                                '<span>✓</span>'
                                f'<div>{len(parsed_careers)}社の職務経歴を抽出しました。</div>'
                                '</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div class="metea-career-ai-compact-status"><span>✓</span>'
                                f'<div>{file_type_label}ファイルを読み取りました。</div></div>',
                                unsafe_allow_html=True,
                            )
                            if st.button(
                                "AIで職務経歴を整理する",
                                key="career_ai_parse",
                                use_container_width=True,
                            ):
                                with st.spinner("AIが職務経歴を整理しています..."):
                                    parsed_careers = parse_career_document(extracted_text)
                                st.session_state["career_ai_parsed"] = parsed_careers
                                st.rerun()

        # ----------------------------------
        # 手入力
        # ----------------------------------

        with manual_col:

            with st.container(
                border=True
            ):

                st.markdown(
                    "<div class='metea-method-illustration metea-method-illustration--manual' "
                    "aria-hidden='true'><svg viewBox='0 0 40 40' fill='none' "
                    "xmlns='http://www.w3.org/2000/svg'><path d='m9 29-1 7 7-1 18-18-6-6L9 29Z' "
                    "stroke='#EE7A1A' stroke-width='2.7' stroke-linejoin='round'/>"
                    "<path d='m23 15 6 6M8 36l7-1-6-6-1 7Z' stroke='#EE7A1A' "
                    "stroke-width='2.3' stroke-linejoin='round'/></svg></div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "<div class='metea-method-heading'><h3>手入力する</h3></div>",
                    unsafe_allow_html=True,
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

        with guidance_col:
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

        parsed_careers = st.session_state.get("career_ai_parsed", [])
        if parsed_careers:
            with st.container(border=True):
                st.markdown(
                    '<span class="metea-career-ai-results-marker"></span>'
                    '<div class="metea-career-ai-results-title">AIによる取り込み結果</div>',
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"{len(parsed_careers)}社の職務経歴を抽出しました。"
                    "内容を確認し、必要に応じて修正してください。"
                )

                for career in parsed_careers:
                    company_label = career.company_name or "会社名未設定"
                    with st.expander(
                        f"{company_label}　部署・役割：{len(career.histories)}件",
                        expanded=False,
                    ):
                        st.markdown(
                            '<span class="metea-career-ai-result-item-marker"></span>',
                            unsafe_allow_html=True,
                        )
                        if career.industry:
                            st.write(f"業種：{career.industry}")
                        st.write(f"部署・役割：{len(career.histories)}件")

                st.button(
                    "この内容を入力フォームに反映する",
                    key="career_ai_apply",
                    use_container_width=True,
                    on_click=apply_ai_careers_to_form,
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

        st.caption("登録後も職務経歴・スキルの内容は変更できます。")

        review_columns = st.columns([1, 2])
        with review_columns[0]:
            st.button(
                "＋ 会社を追加する",
                key="career_review_add_company",
                use_container_width=True,
                on_click=add_company_from_review,
            )

        with review_columns[1]:
            st.button(
                "この内容で登録する",
                key="career_review_confirm",
                type="primary",
                use_container_width=True,
                on_click=finalize_career_registration,
            )

        if st.session_state.get(CAREER_REVIEW_CONFIRMED_KEY, False):
            st.markdown(
                '<div class="metea-career-complete-notice" role="status">'
                '<span>✓</span><div>プロフィールの登録が完了しました。</div></div>',
                unsafe_allow_html=True,
            )
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

    # AI取込確認中は確認対象だけに集中できるよう、登録済み一覧を表示しない。
    if not is_ai_career_reviewing():
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

        st.markdown('<span class="metea-career-review-marker"></span>', unsafe_allow_html=True)
        st.subheader("AI取込内容を確認")
        st.markdown(
            f'<div class="metea-career-review-progress"><b>{review_index + 1}社目</b>'
            f'<span>全{len(ai_items)}社</span></div>',
            unsafe_allow_html=True,
        )
        st.progress((review_index + 1) / len(ai_items))

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

            st.markdown(
                f'<div class="metea-career-review-notice metea-career-review-notice--warning">'
                f'<b>「{company_name}」はすでに登録されています</b>'
                '<span>内容を確認し、既存情報を更新するか今回の取込をスキップしてください。</span></div>',
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                '<div class="metea-career-review-notice"><b>取り込んだ内容を確認してください</b>'
                '<span>AIが整理した内容です。内容を確認・修正してから保存してください。</span></div>',
                unsafe_allow_html=True,
            )

    elif edit_index is None:

        st.markdown('<span class="metea-career-manual-form-marker"></span>', unsafe_allow_html=True)
        st.subheader("会社情報を追加")
        st.markdown(
            '<div class="metea-career-review-notice"><b>勤務先ごとに職務経歴を登録します</b>'
            '<span>会社情報を入力した後、部署・役割を1件以上追加してください。会社名・業種・職種は必須です。</span></div>',
            unsafe_allow_html=True,
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

        st.markdown(
            f'<div class="metea-career-review-notice"><b>「{editing_company_name}」を編集中です</b>'
            '<span>内容を修正した後、「変更を保存する」を押してください。</span></div>',
            unsafe_allow_html=True,
        )

        st.subheader(
            "会社情報を編集："
            f"{editing_company_name}"
        )

    # ======================================
    # 会社情報
    # ======================================

    render_company_form(ai_reviewing)

    # ======================================
    # 部署・役割
    # ======================================

    st.subheader("部署・役割")
    if not ai_reviewing:
        st.caption("同じ会社で部署・役割が変わった場合は、担当期間ごとに分けて登録してください。")

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

                st.markdown('<span class="metea-career-manual-history-form-marker"></span>', unsafe_allow_html=True)

                st.markdown("#### 新しい部署・役割")
                st.caption("担当した仕事と成果を、実際の内容に沿って入力してください。")

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
        st.toast(
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

            save_column, skip_column = st.columns([2, 1])
            with save_column:
                st.button(
                    "内容を保存して次へ",
                    key="career_ai_save",
                    type="primary",
                    use_container_width=True,
                    on_click=save_current_company,
                )
            with skip_column:
                st.button(
                    "この会社をスキップ",
                    key="career_ai_skip",
                    use_container_width=True,
                    on_click=skip_ai_career,
                )

    elif edit_index is None:

        action_columns = st.columns(
            [1, 1, 1]
        )

        with action_columns[1]:

            st.button(
                "この会社を入力内容に追加する",
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
                "変更を反映して確認へ",
                key="career_update",
                type="primary",
                use_container_width=True,
                on_click=(
                    save_current_company
                ),
            )
