"""応募管理・選考通過率レポート画面（カード内編集対応）。"""

import calendar
import base64
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

import streamlit as st

from models import ApplicationMilestone
from pages.job_layout import render_job_navigation
from ui.design_system import render_save_failure
from services.application_management_service import (
    MILESTONE_TYPES,
    PHASE_OPTIONS,
    RESULT_OPTIONS,
    SELECTION_STAGES,
    ApplicationManagementError,
    add_custom_preparation,
    add_milestone_data,
    cancel_milestone,
    complete_milestone,
    delete_milestone_data,
    delete_custom_preparation,
    is_milestone_overdue,
    is_milestone_upcoming,
    milestone_status_label,
    postpone_milestone,
    update_milestone_schedule,
    load_application_detail,
    load_application_views,
    load_preparation_items,
    load_global_preparation_templates,
    copy_global_preparations_to_application,
    copy_application_preparations_to_selection,
    operational_summary,
    sync_applications_from_decisions,
    update_application_data,
    register_selection_result,
    save_preparation_item,
    save_global_preparation_template,
    selection_pass_report,
)
from services.selection_preparation_ai_service import (
    SelectionPreparationAIError,
    format_preparation_material,
    generate_preparation_material,
)


BLUE = "#1268f3"
PHASE_CATEGORIES = ("応募準備", "書類選考", "適性検査", "面接", "オファー・条件確認", "内定", "保留", "終了")


def _svg_data_uri(filename: str) -> str:
    asset_path = Path(__file__).resolve().parents[1] / "assets" / filename
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


TIMELINE_COMPLETE_ICON = _svg_data_uri("timeline_complete.svg")
TIMELINE_WARNING_ICON = _svg_data_uri("timeline_warning.svg")
PHASE_COLORS = {
    "応募準備": "#4f7df3", "応募": "#269ee8", "書類選考": "#16a3a6",
    "適性検査": "#56b7b2", "面接": "#6e819d", "オファー・条件確認": "#f2a52b",
    "内定": "#23a46f", "保留": "#805ad5", "終了": "#aab3c3",
}


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background:#f4f7fb; color:#0d2548; }
        .block-container { max-width:1320px; padding-top:1.25rem !important; padding-bottom:2.25rem !important; }
        .stApp, .stApp button, .stApp input, .stApp textarea, .stApp select {
          font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif!important;
        }
        .application-page-head { margin:2px 0 14px; padding-bottom:0; }
        .application-page-head h1 { margin:0; color:#071a36; font-size:clamp(2rem,2.15vw,2.3rem); line-height:1.28;
          letter-spacing:.01em; font-weight:750; }
        .application-page-head p { margin:7px 0 0; color:#66768d; font-size:13.5px; line-height:1.65; }
        .app-tabs { display:flex; gap:8px; margin:4px 0 22px; }
        .app-tabs a { padding:10px 18px; border-radius:9px; color:#52647d;
          text-decoration:none!important; font-weight:700; border:1px solid #dbe3ef; background:#fff; }
        .app-tabs a.active { color:#fff; background:#1268f3; border-color:#1268f3; }
        .page-lead { color:#6d7c90; margin-top:-8px; margin-bottom:20px; }
        .summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:18px; margin:24px 0; }
        .summary-card,.panel,.application-card { background:#fff; border:1px solid #dbe3ef;
          border-radius:14px; box-shadow:0 6px 18px rgba(31,65,115,.045); }
        .summary-card { min-height:132px; padding:20px 18px 18px; display:flex; flex-direction:column;
          align-items:center; justify-content:center; text-align:center; }
        .summary-icon { width:38px; height:38px; margin-bottom:10px; display:grid; place-items:center;
          border-radius:12px; background:#eaf2ff; color:#1268f3; font-size:17px; font-weight:800; }
        .summary-label { color:#263a58; font-size:14px; font-weight:800; }
        .summary-value { display:flex; align-items:baseline; gap:4px; margin-top:6px; color:#0d2548;
          font-size:32px; line-height:1; font-weight:850; }
        .summary-value small { font-size:14px; font-weight:700; }
        .summary-card.alert { border-color:#ffd5d6; }
        .summary-card.alert .summary-icon { background:#fff0f0; color:#e5484d; }
        .summary-card.alert .summary-value { color:#e5484d; }
        .summary-card.offer { border-color:#cfeee0; background:#fbfffd; }
        .summary-card.offer .summary-icon { background:#eaf8f1; color:#14976b; }
        .summary-card.offer .summary-value { color:#14976b; }
        .summary-link { color:inherit!important; text-decoration:none!important; }
        .summary-link .summary-card {
            height:100%; transition:transform .16s ease, border-color .16s ease, box-shadow .16s ease;
        }
        .summary-link:hover .summary-card {
            transform:translateY(-2px); border-color:#9fc1ff;
            box-shadow:0 8px 18px rgba(18,104,243,.10);
        }
        .summary-link.selected .summary-card {
            border-color:#1268f3; box-shadow:0 0 0 2px rgba(18,104,243,.10);
        }
        .application-summary-grid { gap:14px; margin:10px 0 12px; }
        .application-summary-grid .summary-card { min-height:50px; padding:8px 13px;
          display:grid; grid-template-columns:28px minmax(0,1fr) auto; column-gap:10px;
          text-align:left; justify-content:initial; }
        .application-summary-grid .summary-icon { width:28px; height:28px; margin:0;
          border-radius:9px; grid-column:1; }
        .application-summary-grid .summary-icon svg { width:17px; height:17px; fill:none;
          stroke:currentColor; stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }
        .application-summary-grid .summary-label { grid-column:2; align-self:center; font-size:13px; white-space:nowrap; }
        .application-summary-grid .summary-value { grid-column:3; align-self:center; margin:0; font-size:21px; }
        .application-summary-grid .summary-value small { font-size:12px; }
.application-summary-grid .summary-link.selected .summary-card {
    background:#f7faff; border-color:#1268f3;
    box-shadow:0 0 0 2px rgba(18,104,243,.12),0 8px 22px rgba(31,65,115,.08);
}
.summary-link.disabled { cursor:default; pointer-events:none; }
.summary-link.disabled .summary-card { opacity:.52; box-shadow:none; }
.application-focus-context {
    display:flex; align-items:center; justify-content:space-between; gap:16px;
    padding:13px 16px; margin:4px 0 14px;
    background:#eef5ff; border:1px solid #cfe0ff; border-radius:12px; color:#174b91;
}
.application-focus-context strong { font-size:15px; }
[class*="st-key-application_focus_context"] { margin:4px 0 14px; padding:8px 12px;
    background:#eef5ff; border:1px solid #cfe0ff; border-radius:12px; }
[class*="st-key-application_focus_context"] [data-testid="stHorizontalBlock"] { align-items:center; }
[class*="st-key-application_focus_context"] [data-testid="stMarkdownContainer"] p {
    margin:0; color:#174b91; font-size:13px; font-weight:800; }
[class*="st-key-application_focus_context"] button { min-height:31px!important; padding:4px 10px!important;
    border-color:#a9c7fb!important; color:#1268f3!important; font-size:11px!important; }
.application-anchor { display:block; height:0; scroll-margin-top:24px; }
        .panel { padding:20px; margin:14px 0; }
        .panel h3 { margin:0 0 14px; font-size:18px; }
        .attention-panel {
          margin:12px 0 14px; padding:14px 16px 13px 19px; background:#fff;
          border:1px solid #f3c7ca; border-left:4px solid #e5484d; border-radius:13px;
          box-shadow:0 6px 18px rgba(31,65,115,.04);
        }
        .panel-heading { display:flex; align-items:center; gap:10px; margin-bottom:12px;
          color:#0d2548; font-size:18px; font-weight:800; }
        .panel-heading.attention { color:#d7353b; margin-bottom:4px; }
        .panel-heading-icon { width:29px; height:29px; display:grid; place-items:center;
          border-radius:9px; background:#eaf2ff; color:#1268f3; font-size:13px; font-weight:900; }
        .panel-heading-icon svg { display:block; width:17px; height:17px; fill:none;
          stroke:currentColor; stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }
        .panel-heading.attention .panel-heading-icon { background:#ffe5e6; color:#d7353b; }
        .attention-heading-icon svg { display:block; width:17px; height:17px; }
        .attention-count {
          display:inline-flex; align-items:center; justify-content:center; min-width:24px;
          height:24px; padding:0 8px; margin-left:2px; border-radius:999px;
          background:#ffe5e6; color:#d7353b; font-size:12px; font-weight:800;
        }
        .attention-description {
          margin:0 0 9px 39px; color:#6f7f94; font-size:12px; line-height:1.45;
        }
        .attention-list { margin:0; padding:0; list-style:none; }
        .attention-row {
          display:grid; grid-template-columns:auto minmax(0,1fr) auto auto; gap:16px;
          align-items:center; padding:9px 12px; margin-top:7px; background:#fff;
          border:1px solid #ffd8da; border-radius:11px; color:inherit!important;
          transition:transform .16s ease,box-shadow .16s ease;
        }
        .attention-row:hover { transform:translateY(-1px); box-shadow:0 6px 16px rgba(31,65,115,.09); }
        .attention-status {
          display:inline-flex; align-items:center; justify-content:center; min-width:54px;
          height:24px; padding:0 9px; border-radius:999px; background:#fff0f0;
          color:#d7353b; font-size:12px; font-weight:800;
        }
        .attention-main { color:#40526b; font-size:14px; line-height:1.6; }
        .attention-main strong {
          display:block; margin-bottom:2px; color:#0d2548; font-size:15px;
        }
        .attention-action { color:#40526b; }
        .attention-deadline {
          min-width:112px; padding-left:14px; border-left:1px solid #ffe0e1;
          text-align:right; white-space:nowrap;
        }
        .attention-deadline-label {
          display:block; margin-bottom:2px; color:#8a97a8; font-size:11px; font-weight:700;
        }
        .attention-date { color:#d7353b; font-size:13px; font-weight:800; }
        .attention-button { display:inline-flex; align-items:center; justify-content:center;
          min-width:84px; min-height:34px; padding:7px 13px; border-radius:8px;
          background:#1268f3; color:#fff!important; text-decoration:none!important;
          font-size:13px; font-weight:850; box-shadow:0 4px 10px rgba(18,104,243,.18); }
        .attention-button:hover { background:#0d59d4; transform:translateY(-1px); }
        @media (max-width:900px) {
          .attention-row { grid-template-columns:auto minmax(0,1fr); }
          .attention-deadline {
            grid-column:2; padding-left:0; border-left:0; text-align:left;
          }
          .attention-button { grid-column:2; justify-self:start; }
        }
        [class*="st-key-application_workspace"] { background:#fff; border:1px solid #dbe3ef;
          border-radius:13px; padding:13px 16px 8px; margin:6px 0 10px;
          box-shadow:0 4px 14px rgba(31,65,115,.035); }
        [class*="st-key-application_workspace"] [data-testid="stHorizontalBlock"] { gap:12px; }
        [class*="st-key-application_workspace"] h3 { margin:0 0 8px; color:#0d2548;
          font-size:16px; font-weight:800; }
        [class*="st-key-application_workspace"] [data-testid="stWidgetLabel"] p {
          color:#53647b; font-size:12px; font-weight:700; }
        [class*="st-key-application_workspace"] [data-baseweb="input"],
        [class*="st-key-application_workspace"] [data-baseweb="select"] > div {
          min-height:38px; background:#f8faff; border-color:#dbe3ef; }
        .schedule-panel { padding:0; margin:0; border:0; border-radius:0; box-shadow:none; }
        .schedule-panel .panel-heading { margin-bottom:8px; }
        .schedule-list { display:grid; gap:6px; }
        .schedule-row { display:grid; grid-template-columns:105px minmax(0,1fr) 20px;
          align-items:center; gap:10px; padding:8px 12px; border:1px solid #e4eaf3;
          border-radius:10px; background:#f8faff; color:inherit!important;
          text-decoration:none!important; transition:transform .16s ease,box-shadow .16s ease; }
        .schedule-row:hover { transform:translateY(-1px); box-shadow:0 6px 14px rgba(31,65,115,.08); }
        .schedule-date { color:#263a58; font-weight:800; }
        .schedule-title { min-width:0; color:#0d2548; font-size:14px; font-weight:750;
          line-height:1.45; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .schedule-meta { color:#7a899d; font-size:12px; font-weight:500; }
        .schedule-arrow { display:grid; place-items:center; color:#1268f3; }
        .schedule-arrow svg { width:17px; height:17px; fill:none; stroke:currentColor;
          stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
        .schedule-empty { padding:12px; border:1px dashed #cdd8e8; border-radius:10px;
          color:#718096; background:#f8faff; text-align:center; }
        [class*="st-key-application_overview"] { margin:8px 0 14px; padding:13px 15px 14px;
          background:#fff; border:1px solid #dbe3ef; border-radius:14px;
          box-shadow:0 6px 18px rgba(31,65,115,.045); }
        .application-overview-heading { margin:0 0 5px; color:#0d2548; font-size:16px; line-height:1.45; font-weight:850; }
        [class*="st-key-application_overview"] .summary-card { background:#f8faff; box-shadow:none; }
        [class*="st-key-application_status_"] [data-testid="stButton"] { margin:0; }
        [class*="st-key-application_status_"] [data-testid="stButton"] button {
          position:relative; width:100%; min-height:62px; padding:9px 58px 22px 50px !important;
          border:1px solid #d4e0f2 !important; border-radius:12px !important;
          background:linear-gradient(135deg,#fff 0%,#f5f8ff 100%) !important;
          color:#0d2548 !important; box-shadow:0 4px 12px rgba(31,65,115,.055) !important;
          cursor:pointer; transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease; }
        [class*="st-key-application_status_"] [data-testid="stButton"] button:hover:not(:disabled) {
          transform:translateY(-2px); border-color:#78a8fa !important;
          box-shadow:0 8px 18px rgba(18,104,243,.13) !important; }
        [class*="st-key-application_status_"] [data-testid="stButton"] button:disabled {
          cursor:default; opacity:.62; }
        [class*="st-key-application_status_"] [data-testid="stButton"] button p {
          width:100%; margin:0; text-align:left; color:#0d2548; font-size:13px;
          font-weight:850; line-height:1.25; }
        [class*="st-key-application_status_"] [data-testid="stButton"] button span[data-testid="stIconMaterial"] {
          position:absolute; left:13px; top:13px; display:grid; place-items:center;
          width:34px; height:34px; border-radius:10px; background:#e8f1ff;
          color:#1268f3; font-size:19px; }
        [class*="st-key-application_status_"] [data-testid="stButton"] button::before {
          position:absolute; right:12px; top:12px; display:inline-flex; align-items:center;
          justify-content:center; min-width:42px; min-height:26px; padding:3px 9px;
          border-radius:999px; color:#0d2548; font-size:15px; line-height:1;
          font-weight:850; white-space:nowrap; }
        [class*="st-key-application_status_"] [data-testid="stButton"] button::after {
          position:absolute; left:50px; bottom:8px; color:#7a899d; font-size:9.5px;
          font-weight:650; line-height:1; white-space:nowrap; }
        .application-notifications { margin-top:2px; border-top:1px solid #e6ebf2; padding-top:10px; }
        .notification-heading { display:flex; align-items:center; justify-content:space-between; gap:14px; margin-bottom:6px; }
        .notification-heading>div { display:flex; align-items:baseline; gap:10px; min-width:0; }
        .notification-heading strong { color:#0d2548; font-size:15px; font-weight:850; }
        .notification-heading>div>span { color:#7a899d; font-size:11px; }
        .notification-filter { flex:0 0 auto; padding:4px 9px; border-radius:999px; background:#eef5ff; color:#1268f3; font-size:10.5px; font-weight:800; }
        .notification-filter.active { background:#e4f6f3; color:#138c88; }
        .notification-filter.upcoming { background:#efedff; color:#6655d9; }
        .notification-filter.attention { background:#ffe8e9; color:#e4474d; }
        .notification-list { display:grid; gap:5px; margin:0; padding:0; list-style:none; }
        .notification-more {
            margin:7px 2px 0;
            color:#6b7d96;
            font-size:12px;
            line-height:1.55;
        }
        .notification-row { display:grid; grid-template-columns:102px 75px minmax(0,1fr) auto; align-items:center; gap:9px; min-height:40px; padding:5px 8px; border:1px solid transparent; border-radius:9px; background:#f7f9fc; }
        .notification-row.preparation { border-color:#c8dcff; background:#f3f7ff; }
        .notification-row.active { border-color:#bee4e1; background:#f1faf8; }
        .notification-row.upcoming { border-color:#d7d0fa; background:#f7f5ff; }
        .notification-row.attention { border-color:#ffc7ca; background:#fff4f4; }
        .notification-kind { display:flex; align-items:center; gap:6px; color:#40526b; font-size:10.5px; font-weight:800; white-space:nowrap; }
        .notification-kind svg { width:16px; height:16px; fill:none; stroke:currentColor; stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }
        .notification-row.preparation .notification-kind,.notification-row.preparation .notification-date { color:#1268f3; }
        .notification-row.active .notification-kind,.notification-row.active .notification-date { color:#138c88; }
        .notification-row.upcoming .notification-kind,.notification-row.upcoming .notification-date { color:#6655d9; }
        .notification-row.attention .notification-kind,.notification-row.attention .notification-date { color:#e4474d; }
        .notification-date { color:#64758c; font-size:10.5px; font-weight:800; white-space:nowrap; }
        .notification-main { display:grid; grid-template-columns:minmax(150px,42%) minmax(0,1fr); align-items:center; gap:18px; min-width:0; }
        .notification-main>strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#0d2548; font-size:12.5px; line-height:1.45; }
        .notification-meta { position:relative; display:grid; grid-template-columns:minmax(105px,.8fr) minmax(130px,1.2fr); align-items:center; gap:12px; min-width:0; }
        .notification-meta::before { content:""; position:absolute; left:-9px; top:50%; width:1px; height:28px; background:#d7e0ed; transform:translateY(-50%); }
        .notification-field { display:flex; align-items:center; gap:6px; min-width:0; }
        .notification-field-label { flex:0 0 auto; padding:2px 5px; border-radius:5px; background:rgba(255,255,255,.72); color:#718096; font-size:9px; line-height:1.35; font-weight:800; }
        .notification-field-value { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#40526b; font-size:12px; line-height:1.45; font-weight:700; }
        .notification-action { display:inline-flex; align-items:center; justify-content:center; width:100%; min-width:70px; min-height:30px; padding:4px 9px; border:1px solid #a9c7fb; border-radius:8px; background:#fff; color:#1268f3!important; text-decoration:none!important; font-family:inherit; font-size:10.5px; line-height:1.2; font-weight:850; cursor:pointer; }
        .notification-row.active .notification-action { border-color:#8ccfca; color:#138c88!important; }
        .notification-row.upcoming .notification-action { border-color:#bcb2f2; color:#6655d9!important; }
        .notification-row.attention .notification-action { border-color:#e4474d; background:#e4474d; color:#fff!important; box-shadow:0 3px 8px rgba(228,71,77,.16); }
        .notification-empty { padding:12px; border-radius:9px; background:#f8faff; color:#718096; text-align:center; font-size:12px; }
        [class*="st-key-notification_item_"] { min-height:40px; margin:5px 0 0; padding:5px 8px;
          border:1px solid transparent; border-radius:9px; background:#f7f9fc; }
        [class*="st-key-notification_item_preparation_"] { border-color:#c8dcff; background:#f3f7ff; }
        [class*="st-key-notification_item_active_"] { border-color:#bee4e1; background:#f1faf8; }
        [class*="st-key-notification_item_upcoming_"] { border-color:#d7d0fa; background:#f7f5ff; }
        [class*="st-key-notification_item_attention_"] { border-color:#ffc7ca; background:#fff4f4; }
        [class*="st-key-notification_item_"] [data-testid="stHorizontalBlock"] { align-items:center; gap:9px; }
        [class*="st-key-notification_item_"] [data-testid="stMarkdownContainer"] p { margin:0; }
        [class*="st-key-notification_item_"] [data-testid="stButton"] button {
          min-height:30px; padding:4px 9px; border-radius:8px; font-size:10.5px; font-weight:850; }
        [class*="st-key-notification_item_attention_"] [data-testid="stButton"] button {
          border-color:#e4474d; background:#e4474d; color:#fff; box-shadow:0 3px 8px rgba(228,71,77,.16); }
        [class*="st-key-notification_item_preparation_"] .notification-action {
          border-color:#a9c7fb; background:#fff; color:#1268f3!important; }
        [class*="st-key-notification_item_active_"] .notification-action {
          border-color:#8ccfca; background:#fff; color:#138c88!important; }
        [class*="st-key-notification_item_upcoming_"] .notification-action {
          border-color:#bcb2f2; background:#fff; color:#6655d9!important; }
        [class*="st-key-notification_item_attention_"] .notification-action {
          border-color:#e4474d; background:#e4474d; color:#fff!important;
          box-shadow:0 3px 8px rgba(228,71,77,.16); }
        .notification-inline-card { margin:10px 0 2px; padding:14px 16px; border:1px solid #bcd3fb;
          border-radius:12px; background:#fff; box-shadow:0 7px 18px rgba(31,65,115,.08); }
        .notification-inline-head { display:flex; align-items:flex-start; justify-content:space-between;
          gap:16px; margin-bottom:11px; }
        .notification-inline-head h3 { margin:0; color:#0d2548; font-size:17px; font-weight:850; }
        .notification-inline-head p { margin:3px 0 0; color:#6b7d96; font-size:12px; }
        .notification-inline-grid { display:grid; grid-template-columns:1fr 1fr 1.2fr; gap:9px; }
        .notification-inline-field { padding:9px 11px; border:1px solid #e1e8f2; border-radius:9px; background:#f8faff; }
        .notification-inline-field span { display:block; margin-bottom:3px; color:#7a899d; font-size:9.5px; font-weight:750; }
        .notification-inline-field strong { display:block; color:#0d2548; font-size:12.5px; line-height:1.45; }
        @media(max-width:900px) { .notification-row { grid-template-columns:94px minmax(0,1fr) auto; } .notification-date { display:none; } .notification-main { display:block; } .notification-main>strong { display:block; margin-bottom:5px; } .notification-meta { grid-template-columns:1fr; gap:4px; } .notification-meta::before { display:none; } }
        .application-filter-heading { display:flex; align-items:center; gap:9px; margin:1px 0 6px;
          color:#0d2548; font-size:15px; font-weight:850; }
        .application-filter-heading svg { width:18px; height:18px; fill:none; stroke:#1268f3;
          stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }
        [class*="st-key-application_filters"] { margin:7px 0 11px; padding:10px 13px 4px;
          background:#fff; border:1px solid #dbe3ef; border-radius:13px;
          box-shadow:0 4px 14px rgba(31,65,115,.035); }
        [class*="st-key-application_filters"] [data-testid="stHorizontalBlock"] { gap:9px; align-items:end; }
        [class*="st-key-application_filters"] [data-testid="stWidgetLabel"] p {
          color:#53647b; font-size:11px; font-weight:750; }
        [class*="st-key-application_filters"] [data-baseweb="input"],
        [class*="st-key-application_filters"] [data-baseweb="select"] > div {
          min-height:36px; background:#f8faff; border-color:#dbe3ef; }
        [class*="st-key-application_filters"] [data-testid="stCheckbox"] { padding-bottom:5px; }
        [class*="st-key-notification_schedule_filter_context"] { margin:7px 0 9px; padding:8px 10px;
          border:1px solid #c8dcff; border-radius:10px; background:#f3f7ff; }
        [class*="st-key-notification_schedule_filter_context"] [data-testid="stHorizontalBlock"] {
          align-items:center; gap:10px; }
        .schedule-filter-context { display:flex; align-items:center; gap:12px; min-height:31px;
          color:#53647b; font-size:12px; line-height:1.45; }
        .schedule-filter-context strong { color:#0d2548; font-size:13px; font-weight:850; }
        [class*="st-key-notification_schedule_filter_context"] [data-testid="stButton"] button {
          min-height:31px; border:1px solid #a9c7fb; border-radius:8px; background:#fff;
          color:#1268f3; font-size:11px; font-weight:800; }
        [class*="st-key-application_schedule_section"] { width:calc(100% + 144px) !important; max-width:none !important; margin-top:12px;
          margin-left:-72px; margin-right:-72px; padding:22px 20px 18px;
          background:#fff; border:1px solid #d8e3f1; border-radius:18px;
          box-shadow:0 12px 34px rgba(31,65,115,.07); }
        .application-filter-state { display:flex; align-items:center; gap:8px; min-height:34px;
          color:#66768d; font-size:11px; }
        .application-filter-state strong { color:#1268f3; font-size:12px; }
        .application-list-head { display:flex; align-items:center; justify-content:space-between;
          gap:16px; margin:0 0 8px; }
        @media(max-width:1500px) {
          [class*="st-key-application_schedule_section"] { width:calc(100% + 64px) !important; margin-left:-32px; margin-right:-32px; }
        }
        @media(max-width:1100px) {
          [class*="st-key-application_schedule_section"] { width:100% !important; margin-left:0; margin-right:0; }
        }
        .application-list-title-wrap { display:flex; align-items:center; gap:12px; min-width:0; }
        .application-list-title-icon { flex:0 0 auto; display:grid; place-items:center; width:38px; height:38px;
          border:1px solid #d5e4fb; border-radius:11px; background:linear-gradient(145deg,#f4f8ff,#e8f1ff);
          color:#1268f3; box-shadow:0 4px 10px rgba(18,104,243,.07); }
        .application-list-title-icon svg { width:20px; height:20px; fill:none; stroke:currentColor;
          stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; }
        .application-list-title-copy { min-width:0; }
        .application-list-eyebrow { display:block; margin-bottom:1px; color:#1268f3;
          font-size:9.5px; line-height:1.3; font-weight:850; letter-spacing:.08em; }
        .application-list-title { display:flex; align-items:center; gap:8px; margin:0 !important;
          color:#0d2548; font-size:23px !important; line-height:1.3 !important; letter-spacing:.005em; font-weight:800 !important; }
        .application-list-caption { margin:3px 0 0; color:#718096; font-size:11px; line-height:1.5; }
        .application-list-count { display:inline-flex; align-items:center; justify-content:center;
          min-height:22px; padding:2px 8px; border:1px solid #d5e4fb; border-radius:999px;
          background:#f1f6ff; color:#1268f3; font-size:11px; font-weight:800; white-space:nowrap; }
        .application-list-info { display:inline-grid; place-items:center; width:18px; height:18px;
          color:#1268f3; }
        .application-list-info svg { width:18px; height:18px; fill:none; stroke:currentColor;
          stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }
        [class*="st-key-application_list_heading"] [data-testid="stHorizontalBlock"] {
          align-items:center; margin:2px 0 6px; }
        [class*="st-key-application_list_heading"] [data-testid="stColumn"]:last-child {
          display:flex; justify-content:flex-end; transform:none; }
        [class*="st-key-wbs_view_control"] { display:flex; justify-content:flex-end; width:100%; }
        [class*="st-key-wbs_view_control"] [role="radiogroup"] { display:flex; justify-content:flex-end; gap:4px;
          width:max-content; padding:4px; border:1px solid #dbe3ef; border-radius:10px; background:#eef3fa;
          box-shadow:0 3px 9px rgba(31,65,115,.055); }
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"] { min-width:72px; min-height:34px;
          margin:0; padding:7px 14px; justify-content:center; border-radius:7px;
          color:#52647d; font-size:12px; font-weight:800; transition:background .15s ease,color .15s ease; }
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"][data-selected="true"] {
          background:#1268f3; color:#fff; box-shadow:0 2px 6px rgba(18,104,243,.18); }
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"][data-selected="true"] *,
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"][aria-checked="true"] * {
          color:#fff !important; }
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"] > div > div > div:first-child {
          display:none; }
        [class*="st-key-wbs_view_control"] [data-testid="stMarkdownContainer"] p { font-size:12px; }
        .application-table-wrap { overflow-x:auto; margin:14px 0 0; background:#fff;
          border:1px solid #d9e3f0; border-radius:14px;
          box-shadow:0 10px 28px rgba(31,65,115,.055); scrollbar-color:#b9c9df #f3f6fa;
          scrollbar-width:thin; position:relative; isolation:isolate; overscroll-behavior-inline:contain; }
        .application-table-wrap:focus-visible { outline:3px solid rgba(18,104,243,.22); outline-offset:3px; }
        .schedule-period-bar { display:flex;align-items:center;justify-content:space-between;gap:12px;
          padding:8px 10px;border-left:1px solid #cfdbeb;border-right:1px solid #cfdbeb;
          background:#fff;color:#53647b;font-size:11px; }
        .schedule-period-label { color:#0d2548;font-size:12px;font-weight:850;letter-spacing:.01em; }
        .schedule-scroll-hint { display:none;color:#718096;font-size:10px;white-space:nowrap; }
        .schedule-period-actions { display:flex;align-items:center;gap:6px; }
        .schedule-period-button { min-width:30px;min-height:28px;padding:4px 9px;border:1px solid #c8d7ec;
          border-radius:7px;background:#fff;color:#315273;font-size:11px;font-weight:800;cursor:pointer; }
        .schedule-period-button:hover { border-color:#8db4f7;background:#f1f6ff;color:#1268f3; }
        .schedule-period-button:focus-visible,.next-cell-action:focus-visible,.schedule-prep-link:focus-visible {
          outline:3px solid rgba(18,104,243,.25);outline-offset:2px; }
        [class*="st-key-application_schedule_period_control"] { margin:0;padding:8px 12px;border-left:1px solid #cfdbeb;
          border-right:1px solid #cfdbeb;border-top:0;border-bottom:1px solid #dbe5f2;background:#fbfcfe; }
        [class*="st-key-application_schedule_period_control"] [data-testid="stHorizontalBlock"] { align-items:center;gap:6px; }
        [class*="st-key-application_schedule_period_control"] [data-testid="stButton"] button {
          min-height:29px;padding:4px 8px;border:1px solid #c8d7ec;border-radius:7px;background:#fff;
          color:#315273;font-size:10px;font-weight:800;box-shadow:none; }
        [class*="st-key-application_schedule_period_control"] [data-testid="stButton"] button:hover {
          border-color:#8db4f7;background:#f1f6ff;color:#1268f3; }
          .application-table { --company-width:150px; --next-width:120px; --prep-width:126px;
          --route-width:88px; --phase-width:95px; --status-width:75px; --timeline-width:128px;
          --management-width:calc(var(--company-width) + var(--next-width) + var(--route-width) + var(--phase-width) + var(--status-width) + var(--prep-width));
          width:calc(var(--management-width) + var(--timeline-total-width));
          min-width:calc(var(--management-width) + var(--timeline-total-width));
          max-width:none; border-collapse:separate;
          border-spacing:0; table-layout:fixed; }
        .application-table col.company-col { width:var(--company-width); }
        .application-table col.next-col { width:var(--next-width); }
        .application-table col.route-col { width:var(--route-width); }
        .application-table col.phase-col { width:var(--phase-width); }
        .application-table col.status-col { width:var(--status-width); }
        .application-table col.prep-col { width:var(--prep-width); }
        .application-table col.timeline-col { width:var(--timeline-width); }
        .application-table.two_weeks { --timeline-width:64px; }
        .application-table.month { --timeline-width:32px; }
        .application-table th { position:sticky;top:0;z-index:4;padding:10px 9px; background:#f8fafd;
          border-bottom:1px solid #dce5f0; border-right:1px solid #edf1f6;
          color:#40546f; font-size:10.5px; line-height:1.35;
          text-align:left; font-weight:800; }
        .application-table .schedule-group-head th { position:static;padding:9px 12px;background:#fff;
          border-right:0;color:#718097;font-size:9.5px;letter-spacing:.04em; }
        .application-table .schedule-group-head .timeline-group { border-left:1px solid #d8e3f1;
          color:#1268f3;background:#f8fbff; }
        .application-table .schedule-column-head th { top:0; }
        .application-table th:last-child { border-right:0; }
        .application-table td { padding:10px 9px; border-bottom:1px solid #e6edf5;
          border-right:1px solid #f1f4f8; color:#263a58; font-size:11.5px; line-height:1.45;
          vertical-align:middle; background:#fff; transition:background .16s ease; }
        .application-table tbody tr { position:relative; }
        .application-table tbody tr:nth-child(even) td { background:#fbfcfe; }
        .application-table tbody tr:hover td,
        .application-table tbody tr:focus-within td { background:#f7faff; }
        .application-table tr:last-child td { border-bottom:0; }
        .application-table td:last-child { border-right:0; }
        .application-table .company-cell { width:var(--company-width);min-width:var(--company-width);
          max-width:var(--company-width);box-sizing:border-box; }
        .application-table tbody .company-cell { box-shadow:inset 3px 0 0 #e0eafb; }
        .schedule-company-actions{display:flex;flex-direction:column;align-items:flex-start;gap:5px}
        .schedule-prep-link{display:inline-flex;align-items:center;justify-content:center;min-height:29px;
          width:100%;padding:4px 5px;box-sizing:border-box;border:0;border-radius:7px;background:transparent;
          color:#1268f3 !important;font-size:9.5px;font-weight:800;text-decoration:none !important;line-height:1.35}
        .schedule-prep-link:hover{background:#edf4ff;text-decoration:none !important}
        .application-table .phase-cell { width:var(--phase-width);min-width:var(--phase-width);
          max-width:var(--phase-width);box-sizing:border-box; }
        .application-table .route-cell { width:var(--route-width);min-width:var(--route-width);
          max-width:var(--route-width);box-sizing:border-box; }
        .application-table .next-cell { position:relative;width:var(--next-width);min-width:var(--next-width);
          max-width:var(--next-width);box-sizing:border-box; }
        .application-table .prep-cell { width:var(--prep-width);min-width:var(--prep-width);
          max-width:var(--prep-width);box-sizing:border-box; }
        .schedule-row-actions { display:flex;flex-direction:column;gap:6px;width:100%; }
        .schedule-row-action { display:inline-flex;align-items:center;justify-content:center;width:100%;
          min-height:30px;padding:5px 7px;box-sizing:border-box;border:1px solid #b9d1f8;
          border-radius:8px;background:#fff;color:#1268f3!important;font-size:9.5px;font-weight:850;
          line-height:1.3;text-decoration:none!important;cursor:pointer;transition:.15s ease; }
        .schedule-row-action.primary { border-color:#1268f3;background:#1268f3;color:#fff!important;
          box-shadow:0 4px 10px rgba(18,104,243,.16); }
        .schedule-row-action:hover { border-color:#72a5f7;background:#edf5ff;text-decoration:none!important; }
        .schedule-row-action.primary:hover { border-color:#075ad9;background:#075ad9; }
        .application-table .wbs-day { width:128px; padding:8px 5px; text-align:center; position:relative; }
        .application-table th.wbs-day,
        .application-table td.wbs-day { border-right:0; }
        .application-table tbody td.wbs-day::after { content:'';position:absolute;left:0;right:0;top:50%;
          height:2px;background:#e3eaf4;z-index:0; }
        .application-table tbody td.wbs-day:first-of-type::after { left:10px; }
        .application-table tbody td.wbs-day:last-child::after { right:10px; }
        .application-table .prep-cell { border-right:1px solid #c9d6e7; }
        .application-table.two_weeks .wbs-day { width:64px; }
        .application-table.month .wbs-day { width:32px; }
        .wbs-date-head { display:block; color:#40526b; font-size:10px; white-space:nowrap; text-align:center; }
        .wbs-date-head.today { margin:-4px -3px;padding:4px 3px;border-radius:6px;
          background:#eaf2ff;color:#1268f3;font-weight:900; }
        .wbs-events { position:relative;z-index:1;display:flex; flex-direction:column; align-items:center;
          justify-content:center; gap:7px; min-height:48px; }
        .wbs-event { display:flex; position:relative; flex-direction:column;align-items:center;justify-content:center;gap:4px;
          min-height:42px;width:calc(100% - 6px);margin:0;padding:4px 3px 3px;box-sizing:border-box;
          border:0;border-radius:8px;background:transparent;color:#52647d;font-size:8.5px;font-weight:700;
          line-height:1.22;white-space:normal;word-break:keep-all;overflow-wrap:anywhere;text-align:center;
          transition:background .14s ease,transform .14s ease; }
        .wbs-event:hover { background:#f4f8ff;transform:translateY(-1px); }
        .timeline-state-icon { display:block;width:21px;height:21px;flex:0 0 21px;object-fit:contain; }
        .timeline-dot { display:block;width:14px;height:14px;flex:0 0 14px;border:3px solid #1268f3;
          border-radius:50%;background:#fff;box-sizing:border-box;box-shadow:0 0 0 3px #fff; }
        .timeline-event-label { color:#334155;font:inherit;font-weight:750;line-height:1.22; }
        .wbs-event.done .timeline-event-label { color:#334155; }
        .wbs-event.overdue { color:#d7353b; font-weight:850;background:#fff7f7; }
        .wbs-event.overdue .timeline-event-label { color:#d7353b; }
        .wbs-event.urgent { color:#0d55a5;font-weight:850;background:#f3f8ff; }
        .wbs-event.urgent .timeline-dot { width:16px;height:16px;flex-basis:16px;border-color:#1268f3;
          box-shadow:0 0 0 3px #fff,0 0 0 5px #dceaff; }
        .wbs-event.inactive { color:#8a97a8; }
        .wbs-event.inactive .timeline-dot { border-color:#b9c5d6;background:#eef2f7; }
        .wbs-event.personal .timeline-dot { border-color:#7185a3; }
        .wbs-event.agent .timeline-dot { border-color:#e39a34; }
        .wbs-event.company .timeline-dot { border-color:#1268f3; }
        .application-table.two_weeks .wbs-event { min-height:39px;padding:3px 2px 2px;
          font-size:7.5px;white-space:normal;overflow:hidden;display:flex; }
        .application-table.month .wbs-events { min-height:28px;align-items:center;justify-content:center;
          flex-direction:row;flex-wrap:wrap;gap:3px; }
        .application-table.month .wbs-event { width:14px;height:14px;min-height:14px;padding:0;border:0;
          background:transparent;font-size:0;overflow:hidden; }
        .application-table.month .timeline-state-icon { width:14px;height:14px;flex-basis:14px; }
        .application-table.month .timeline-dot { width:10px;height:10px;flex-basis:10px;border-width:2px;box-shadow:none; }
        .application-table.month .timeline-event-label { display:none; }
        .wbs-more { display:inline-flex;align-items:center;justify-content:center;min-height:20px;padding:2px 5px;
          border-radius:999px;background:#eef3fa;color:#52647d;font-size:8px;font-weight:850;white-space:nowrap; }
        .application-table.month .wbs-more { min-width:18px;min-height:18px;padding:1px 4px; }
        .wbs-empty-day { display:block; min-height:34px; }
        .wbs-period-empty { display:flex;align-items:center;justify-content:center;min-height:34px;
          color:#9aa7b9;font-size:9px;font-weight:700;white-space:nowrap; }
        .wbs-legend { display:flex; align-items:center; flex-wrap:wrap; gap:8px 18px; padding:11px 15px;
          border-top:1px solid #e6edf5;background:#fbfcfe;color:#66768d;font-size:9.5px; }
        .wbs-legend span { display:inline-flex; align-items:center; gap:6px; white-space:nowrap; }
        .legend-dot.personal { border-color:#7185a3; }
        .legend-dot.agent { border-color:#e39a34; background:#fff7e8; }
        .legend-dot.company { border-color:#1268f3; background:#edf5ff; }
        .legend-dot { width:9px; height:9px; border:3px solid #1268f3; border-radius:50%; background:#fff; }
        .legend-state-icon { display:block;width:15px;height:15px;object-fit:contain; }
        .ended-applications { margin-top:14px; }
        .ended-application-list { display:grid; gap:8px; padding:4px 0 2px; }
        .ended-application-row { display:grid; grid-template-columns:minmax(180px,1.6fr) minmax(110px,.8fr) minmax(100px,.7fr);
          align-items:center; gap:14px; min-height:46px; padding:8px 14px; border:1px solid #e1e8f2;
          border-radius:10px; background:#fff; color:#334155; }
        .ended-application-row strong { color:#0d2548; font-size:12px; }
        .ended-application-row span { color:#66768d; font-size:10.5px; }
        .ended-application-result { justify-self:start; display:inline-flex; align-items:center;
          min-height:24px; padding:3px 9px; border-radius:999px; background:#f1f4f8;
          color:#52647d!important; font-weight:800; }
        .table-company { display:block; color:#0d2548!important; font-size:12px; font-weight:850;
          line-height:1.4;text-decoration:none!important;display:-webkit-box;-webkit-line-clamp:3;
          -webkit-box-orient:vertical;overflow:hidden; }
        .table-company:hover { color:#1268f3!important; }
        .table-job { display:block; margin-top:2px; color:#708097; font-size:10px; }
        .route-cell,.next-cell { overflow:hidden; text-overflow:ellipsis; overflow-wrap:anywhere; }
        .table-phase { display:inline-flex;align-items:center;padding:5px 8px;border:1px solid #c9dcfb;
          border-radius:999px;background:#eef5ff;color:#1268f3;font-size:9.5px;font-weight:800; }
        .table-status { display:inline-flex;align-items:center;padding:4px 7px;border-radius:999px;
          background:#f1f4f8;color:#607087;font-size:9.5px;font-weight:800;white-space:nowrap; }
        .table-status.attention { background:#fff0f1;color:#d7353b; }
        .table-status.upcoming { background:#f0edff;color:#6655d9; }
        .table-status.normal { background:#f3f5f8;color:#6f7e91; }
        .table-next { color:#0d2548;font-weight:800;line-height:1.4; }
        .next-cell-action { position:absolute; inset:4px; display:flex; width:calc(100% - 8px); height:calc(100% - 8px);
          min-height:100%; margin:0; padding:10px 9px; box-sizing:border-box;
          flex-direction:column; justify-content:center; color:#0d2548 !important;
          background:transparent !important; text-decoration:none !important; border-radius:8px;
          transition:background .16s ease, box-shadow .16s ease; }
        .next-cell-action:hover { background:#f2f7ff !important;
          box-shadow:inset 0 0 0 1.5px #9fc0fb; }
        .next-cell-action small { display:block; margin-top:5px; color:#1268f3; font-size:11px;
            font-weight:750; }
        .next-cell-action { border:0; cursor:pointer; text-align:left; font:inherit; }
        .application-table td[data-schedule-application] { cursor:pointer; }
        .application-table td[data-schedule-application]:hover { background:#edf5ff !important; }
        .application-table th.company-cell,.application-table td.company-cell,
        .application-table th.next-cell,.application-table td.next-cell,
        .application-table th.prep-cell,.application-table td.prep-cell,
        .application-table th.route-cell,.application-table td.route-cell,
        .application-table th.phase-cell,.application-table td.phase-cell,
        .application-table th.status-cell,.application-table td.status-cell { position:sticky;z-index:3; }
        .application-table th.company-cell,.application-table td.company-cell { left:0; }
        .application-table th.next-cell,.application-table td.next-cell { left:var(--company-width); }
        .application-table th.route-cell,.application-table td.route-cell {
          left:calc(var(--company-width) + var(--next-width)); }
        .application-table th.phase-cell,.application-table td.phase-cell {
          left:calc(var(--company-width) + var(--next-width) + var(--route-width)); }
        .application-table th.status-cell,.application-table td.status-cell {
          left:calc(var(--company-width) + var(--next-width) + var(--route-width) + var(--phase-width)); }
        .application-table th.prep-cell,.application-table td.prep-cell {
          left:calc(var(--company-width) + var(--next-width) + var(--route-width) + var(--phase-width) + var(--status-width));
          box-shadow:8px 0 14px rgba(31,65,115,.10); }
        .application-table thead .schedule-column-head th.company-cell,
        .application-table thead .schedule-column-head th.next-cell,
        .application-table thead .schedule-column-head th.prep-cell,
        .application-table thead .schedule-column-head th.route-cell,
        .application-table thead .schedule-column-head th.phase-cell,
        .application-table thead .schedule-column-head th.status-cell { z-index:7;background:#f8fafd; }
        .application-table td.company-cell,.application-table td.next-cell,
        .application-table td.prep-cell,
        .application-table td.route-cell,
        .application-table td.phase-cell,.application-table td.status-cell { background:#fff; }
        .application-table td.company-cell { box-shadow:inset 3px 0 0 #d9e7fb; }
        .application-table tbody tr:nth-child(even) td.company-cell,
        .application-table tbody tr:nth-child(even) td.next-cell,
        .application-table tbody tr:nth-child(even) td.prep-cell,
        .application-table tbody tr:nth-child(even) td.route-cell,
        .application-table tbody tr:nth-child(even) td.phase-cell,
        .application-table tbody tr:nth-child(even) td.status-cell { background:#fbfcfe; }
        .application-table tbody tr:hover td.company-cell,
        .application-table tbody tr:hover td.next-cell,
        .application-table tbody tr:hover td.prep-cell,
        .application-table tbody tr:hover td.route-cell,
        .application-table tbody tr:hover td.phase-cell,
        .application-table tbody tr:hover td.status-cell { background:#f6f9fe; }
        .application-table .schedule-group-head .management-group { position:sticky;left:0;z-index:8;
          width:var(--management-width);min-width:var(--management-width);max-width:var(--management-width);
          box-sizing:border-box;background:#fff;box-shadow:8px 0 14px rgba(31,65,115,.10); }
        .application-table .weekend .wbs-date-head { color:#7b6ab7; }
        .application-table .today-column { background:#fbfdff; }
        .application-table.month td { height:54px; }
        .application-table.two_weeks td { height:62px; }
        .schedule-empty-state { display:flex;align-items:flex-start;gap:11px;margin:0;padding:18px;
          border:1px solid #cfdbeb;border-top:0;border-radius:0 0 12px 12px;background:#fff;color:#53647b; }
        .schedule-empty-state strong { display:block;margin-bottom:3px;color:#0d2548;font-size:13px; }
        .schedule-empty-state span { display:block;font-size:11px;line-height:1.55; }
        .schedule-empty-state-icon { display:grid;place-items:center;flex:0 0 32px;width:32px;height:32px;
          border-radius:9px;background:#edf5ff;color:#1268f3;font-size:17px;font-weight:900; }
        [class*="st-key-application_list_header_filters"] { margin:10px 0 0;padding:12px 14px 8px;
          border:1px solid #d8e3f1;border-radius:12px;background:#f8fafd; }
        [class*="st-key-application_list_header_filters"] [data-testid="stHorizontalBlock"] { gap:8px;align-items:end; }
        [class*="st-key-application_list_header_filters"] label p { color:#52647d;font-size:10px;font-weight:800; }
        [class*="st-key-application_list_header_filters"] [data-baseweb="input"] > div,
        [class*="st-key-application_list_header_filters"] [data-baseweb="select"] > div {
          min-height:36px;background:#fff;border-color:#d4deec;border-radius:8px; }
        [class*="st-key-application_list_header_filters"] [data-testid="stButton"] button {
          min-height:36px;border-radius:8px;font-size:10px;font-weight:800; }
        [class*="st-key-application_list_header_filters"] [data-testid="stCheckbox"] { margin-top:4px; }
        .schedule-toolbar-title { display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px; }
        .schedule-toolbar-title > div { display:flex;align-items:baseline;gap:8px;min-width:0; }
        .schedule-toolbar-title strong { color:#0d2548;font-size:12px; }
        .schedule-toolbar-title span:not(.schedule-filter-state) { color:#7a899d;font-size:10px; }
        .schedule-filter-state { flex:0 0 auto;padding:4px 8px;border-radius:999px;background:#eaf2ff;
          color:#1268f3;font-size:9px;font-weight:850; }
        .schedule-toolbar-spacer { height:18px; }
        .schedule-action-list { margin:12px 0 0; border:1px solid #d9e3f0; border-radius:14px;
          background:#fff; overflow:hidden; box-shadow:0 8px 22px rgba(31,65,115,.055); }
        .schedule-list-topline { display:flex; align-items:center; justify-content:flex-end; min-height:30px;
          padding:6px 14px 5px; background:#fff; }
        .schedule-list-topline .wbs-legend { justify-content:flex-end;padding:0;border:0;background:transparent; }
        .schedule-action-head,.schedule-action-row { display:grid;
          grid-template-columns:minmax(160px,1.35fr) minmax(135px,.95fr) minmax(165px,1.2fr)
          minmax(210px,1.55fr) 210px; align-items:center; column-gap:12px; }
        .schedule-action-head { min-height:38px; padding:0 14px; background:#f7faff;
          border-bottom:1px solid #dfe8f3; color:#52657f; font-size:10px; font-weight:850; }
        .schedule-action-row { min-height:64px; padding:8px 14px; border-bottom:1px solid #e7edf5;
          transition:background .15s ease,box-shadow .15s ease; }
        .schedule-action-row:last-of-type { border-bottom:0; }
        .schedule-action-row:hover { background:#fbfdff; box-shadow:inset 3px 0 0 #87b4ff; }
        .schedule-list-company { min-width:0; }
        .schedule-list-company .table-company { display:block; overflow:hidden; text-overflow:ellipsis;
          white-space:nowrap; color:#0d2548; font-size:13px; font-weight:850; text-decoration:none; }
        .schedule-list-sub { display:block; margin-top:3px; overflow:hidden; text-overflow:ellipsis;
          white-space:nowrap; color:#8290a4; font-size:10px; line-height:1.35; }
        .schedule-list-state { display:flex; align-items:center; flex-wrap:wrap; gap:5px; min-width:0; }
        .schedule-list-state .table-phase,.schedule-list-state .table-status { max-width:100%;
          overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .schedule-list-next { display:flex; align-items:center; justify-content:space-between; gap:8px;
          width:100%; min-width:0; padding:8px 10px; border:1px solid #c9dcfb; border-radius:9px;
          background:#f5f9ff; color:#0d4f9a; cursor:pointer; text-align:left; }
        .schedule-list-next:hover { border-color:#82aff5; background:#edf5ff; }
        .schedule-list-next strong { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
          font-size:11px; font-weight:850; }
        .schedule-list-next small { display:block; margin-top:2px; color:#6f829d; font-size:9px; }
        .schedule-list-next svg { flex:0 0 auto; width:15px; height:15px; fill:none; stroke:currentColor;
          stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }
        .schedule-list-events { display:flex; align-items:center; gap:8px; min-width:0; overflow:hidden; }
        .schedule-list-event { display:inline-flex; flex:0 0 58px; flex-direction:column; align-items:center;
          justify-content:center; min-width:0; max-width:58px; padding:1px 2px; color:#51637b;
          font-size:8px; font-weight:750; line-height:1.2; white-space:nowrap; text-align:center; }
        .schedule-list-event::before { content:""; width:17px; height:17px; margin-bottom:4px;
          border:3px solid #1268f3; border-radius:50%; background:#fff; box-sizing:border-box;
          box-shadow:0 0 0 3px #edf4ff; }
        .schedule-list-event > span { display:block; width:100%; overflow:hidden; text-overflow:ellipsis; }
        .schedule-list-event time { margin-right:2px; color:#718096; font-size:7px; font-weight:800; }
        .schedule-list-event.done::before { border-color:#18a978; background:#18a978;
          box-shadow:0 0 0 3px #e5f8f1; }
        .schedule-list-event.agent::before { border-color:#e3951d; box-shadow:0 0 0 3px #fff3de; }
        .schedule-list-event.personal::before { border-color:#8394ab; box-shadow:0 0 0 3px #eef2f7; }
        .schedule-list-event.overdue::before { border-color:#e2444b; box-shadow:0 0 0 3px #fff0f0; }
        .schedule-list-no-event { color:#94a0b1; font-size:10px; }
        .schedule-list-actions { display:flex; align-items:center; justify-content:flex-end; gap:6px; }
        .schedule-list-update,.schedule-list-prep { display:inline-flex; align-items:center; justify-content:center;
          min-height:32px; padding:6px 10px; border-radius:8px; font-size:10px; font-weight:850;
          white-space:nowrap; text-decoration:none !important; cursor:pointer; }
        .schedule-list-update { border:1px solid #1268f3; background:#1268f3; color:#fff; }
        .schedule-list-update:hover { background:#075ad9; }
        .schedule-list-prep { border:1px solid #bdd3f5; background:#fff; color:#1268f3; }
        .schedule-list-prep:hover { background:#f2f7ff; }
        .schedule-list-legend { display:flex; align-items:center; justify-content:flex-end; flex-wrap:wrap;
          gap:5px 12px; color:#718096; font-size:8px; }
        @media (max-width:1280px) {
          .schedule-action-head,.schedule-action-row { grid-template-columns:minmax(145px,1.25fr) minmax(120px,.9fr)
            minmax(150px,1.15fr) minmax(170px,1.3fr) 190px; column-gap:8px; }
        }
        @media(max-width:1100px) {
          .schedule-scroll-hint { display:inline; }
          .application-table th,.application-table td { font-size:11px; }
          .application-table { --company-width:110px; --next-width:105px;
            --prep-width:86px; --route-width:78px; --phase-width:86px; --status-width:70px; }
        }
        @media(max-width:760px) {
          [class*="st-key-application_schedule_section"] { padding:12px 8px; }
          .application-list-title { font-size:18px; }
          .application-list-title-icon { width:34px;height:34px; }
          [class*="st-key-application_list_heading"] [data-testid="stHorizontalBlock"] { flex-wrap:wrap; }
          [class*="st-key-wbs_view_control"] { justify-content:flex-start; }
          [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"] { min-width:66px;padding:6px 9px; }
        }
        .st-key-schedule_modal_triggers { display:none !important; }
        .table-detail-link { display:block; margin-top:5px; color:#1268f3!important;
          font-size:10px; font-weight:800; text-decoration:none!important; }
        .application-card { padding:18px; margin:12px 0; }
        .app-head { display:flex; justify-content:space-between; gap:14px; align-items:flex-start; }
        .company { font-size:18px; font-weight:800; color:#1268f3; text-decoration:none!important; }
        .job-title { color:#53647b; margin-top:5px; }
        .badge { display:inline-block; padding:5px 10px; border-radius:999px; font-size:12px;
          font-weight:800; background:#eaf2ff; color:#1268f3; }
        .app-meta { display:grid; grid-template-columns:1.1fr 1fr 1.5fr; gap:12px; margin:16px 0; }
        .meta-box { background:#f7f9fc; border-radius:9px; padding:10px 12px; }
        .meta-label { color:#77869b; font-size:12px; } .meta-value { margin-top:3px; font-weight:700; }
        .wbs { display:flex; align-items:flex-start; margin-top:14px; overflow-x:auto; padding-bottom:4px; }
        .wbs-step { position:relative; min-width:110px; text-align:center; color:#718096; font-size:11px; }
        .wbs-step:before { content:''; display:block; width:11px; height:11px; margin:0 auto 7px;
          border:3px solid #b9c5d6; border-radius:50%; background:#fff; position:relative; z-index:2; }
        .wbs-step:not(:last-child):after { content:''; position:absolute; top:6px; left:55%; right:-45%; height:2px; background:#d8e0ec; }
        .wbs-step.done:before { border-color:#1aa06d; background:#1aa06d; }
        .wbs-step.overdue:before { border-color:#e5484d; background:#fff; }
        .wbs-step.overdue { color:#d7353b; font-weight:700; }
        .wbs-step.upcoming:before { border-color:#1268f3; background:#fff; }
        .wbs-step.inactive { color:#9aa7b9; }
        .wbs-step.inactive:before { border-color:#cbd4e1; background:#eef2f7; }
        .bar-row { display:grid; grid-template-columns:170px 1fr 70px; gap:14px; align-items:center; margin:12px 0; }
        .bar-track { height:12px; border-radius:999px; background:#e9eef6; overflow:hidden; }
        .bar-fill { height:100%; border-radius:999px; }
        .funnel { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
        .funnel-card { padding:16px; border:1px solid #dbe3ef; border-radius:12px; text-align:center; background:#fff; }
        .funnel-card strong { display:block; font-size:25px; margin-top:5px; }
        .route-table { width:100%; border-collapse:collapse; }
        .route-table th,.route-table td { padding:11px; border-bottom:1px solid #e4eaf2; text-align:left; }
        .route-table th { color:#61728a; font-size:13px; }
        .detail-hero {display:grid;grid-template-columns:minmax(0,1.7fr) repeat(3,minmax(135px,.72fr));
          background:#fff;border:1px solid #dbe3ef;border-radius:14px;margin:14px 0 22px;overflow:hidden;
          box-shadow:0 6px 20px rgba(36,62,101,.045)}
        .detail-hero>div{padding:12px 15px;border-right:1px solid #e6ebf2;min-width:0}.detail-hero>div:last-child{border:0}
        .company-row{display:flex;align-items:center}.detail-company{font-size:20px;font-weight:850;line-height:1.45}
        .detail-role{margin-top:5px;color:#52647d;font-size:13px;line-height:1.55}.detail-label{font-size:11px;color:#75849a;font-weight:750}
        .detail-value{margin-top:7px;font-weight:800;font-size:14px;line-height:1.5}.phase-pill{display:inline-flex;padding:6px 11px;
          border:1px solid #b8d0fa;border-radius:8px;background:#f1f6ff;color:#1268f3;font-weight:800;font-size:12px}
        .detail-section-title{display:flex;align-items:center;gap:9px;margin:17px 0 5px;color:#08264d;font-size:18px;font-weight:850}
        .detail-section-title:before{content:'';width:4px;height:22px;border-radius:99px;background:#1268f3}
        .detail-section-copy{margin:0 0 9px;color:#65758d;font-size:12px}
        .detail-attention{display:flex;align-items:flex-start;gap:11px;padding:13px 15px;margin:4px 0 18px;border:1px solid #ffc9ce;
          border-radius:11px;background:#fff7f7;color:#9f2730;font-size:13px;line-height:1.6}
        .detail-attention-mark{display:grid;place-items:center;flex:0 0 22px;height:22px;border:1px solid #ef5964;border-radius:50%;
          color:#e63f4b;font-weight:900}.detail-subtitle{margin:11px 0 3px;color:#10284a;font-size:15px;font-weight:850}
        .detail-subcopy{margin:0 0 10px;color:#6f7f94;font-size:12px}
        .detail-empty{padding:17px;border:1px dashed #cdd9ea;border-radius:10px;background:#f8fbff;color:#687a92;text-align:center;font-size:13px}
        [class*="st-key-detail_milestone_"]{background:#fff;border:1px solid #dbe3ef;border-radius:10px;padding:8px 11px!important;
          margin:6px 0;box-shadow:0 2px 8px rgba(36,62,101,.03)}
        [class*="st-key-detail_milestone_pending_"]{border-left:3px solid #4b8df8}
        [class*="st-key-detail_milestone_overdue_"]{border-color:#ffc9ce;border-left:3px solid #ef5964;background:#fffafa}
        .milestone-name{font-size:14px;font-weight:850;color:#10284a}.milestone-meta{margin-top:4px;color:#66768d;font-size:12px}
        .milestone-status{display:inline-flex;margin-left:7px;padding:3px 8px;border-radius:99px;background:#edf4ff;color:#1268f3;font-size:10px;font-weight:850}
        .milestone-status.history{background:#f0f3f7;color:#65758d}.action-panel{border-color:#ffd3d5;background:#fffafa}
        [class*="st-key-overdue_action_"]{padding:15px 16px 9px;margin:10px 0;border:1px solid #ffd7d9;border-radius:11px;background:#fff}
        [class*="st-key-overdue_action_target_"]{border:2px solid #1268f3;background:#f7faff;box-shadow:0 0 0 4px rgba(18,104,243,.09)}
        .overdue-action-title{font-weight:800;color:#10284a}.overdue-action-meta{margin-top:4px;color:#6f7f94;font-size:12px}
        .detail-grid{display:grid;grid-template-columns:1fr 1.45fr 1fr;gap:14px}.status-card{background:#fff;border:1px solid #dbe3ef;
          border-radius:12px;padding:18px}.status-card h4{margin:0 0 14px}.detail-timeline{border-left:2px solid #dce5f2;margin-left:10px;padding-left:24px}
        .activity-row{position:relative;padding:10px 0;border-bottom:1px solid #edf1f6}.activity-row:before{content:'';position:absolute;
          width:9px;height:9px;border-radius:50%;background:#9db2d1;left:-30px;top:16px}.activity-date{color:#708097;font-size:12px}
        @media(max-width:900px){.detail-hero{grid-template-columns:1fr 1fr}.detail-hero>div{border-bottom:1px solid #e6ebf2}}
        .prep-page-title{font-size:30px!important;line-height:1.35!important;margin:14px 0 8px!important;letter-spacing:.01em!important}
        .prep-chooser-lead{margin:4px 0 22px;color:#66768d;font-size:13px;line-height:1.7}
        .prep-chooser-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
        .prep-chooser-card{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:16px;padding:18px 20px;border:1px solid #dbe3ef;border-radius:13px;background:#fff;box-shadow:0 5px 16px rgba(31,65,115,.04);text-decoration:none!important}
        .prep-chooser-card:hover{border-color:#9fc1ff;background:#fbfdff}
        .prep-chooser-card b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#102846;font-size:15px}
        .prep-chooser-card span{display:block;margin-top:6px;color:#718198;font-size:11px}
        .prep-chooser-card i{display:grid;place-items:center;width:34px;height:34px;border-radius:9px;background:#eaf2ff;color:#1268f3;font-size:18px;font-style:normal;font-weight:800}
        .prep-chooser-empty{padding:32px;border:1px dashed #ccd9ea;border-radius:13px;background:#fff;text-align:center;color:#718198;font-size:13px}
        .prep-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin:2px 0 20px;padding-bottom:20px;border-bottom:1px solid #dfe6f0}
        .prep-company{margin-top:12px;color:#1f3454;font-size:14px;font-weight:750}.prep-meta{display:flex;gap:13px;align-items:center;padding-top:14px;white-space:nowrap}
        .progress-track{width:220px;height:10px;background:#e7edf7;border-radius:99px;overflow:hidden}.progress-fill{height:100%;background:#1268f3;border-radius:99px}
        .prep-actions{display:flex;justify-content:flex-end;gap:10px;margin:-4px 0 16px}.prep-action{padding:8px 14px;border:1px solid #a9c7fb;border-radius:8px;background:#fff;color:#1268f3!important;text-decoration:none!important;font-size:13px;font-weight:800}
        .prep-tabs{display:flex;gap:38px;border-bottom:1px solid #dce4ef;margin-bottom:24px}.prep-tab{padding:12px 2px;color:#53647b!important;text-decoration:none!important;font-size:14px;font-weight:800;border-bottom:3px solid transparent}
        .prep-tab.active{color:#1268f3!important;border-bottom-color:#1268f3}.prep-layout{display:grid;grid-template-columns:minmax(0,1fr) 285px;gap:24px;align-items:start}
        [class*="st-key-selection_preparation_scope_"] { margin:0 0 24px; padding-bottom:10px; border-bottom:1px solid #dce4ef; }
        [class*="st-key-selection_preparation_scope_"] [data-testid="stSegmentedControl"] { width:100%; }
        [class*="st-key-selection_preparation_scope_"] [data-testid="stSegmentedControl"] > div { gap:8px; }
        [class*="st-key-selection_preparation_scope_"] button { min-height:38px; font-weight:800; }
        .prep-section-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.prep-section-head h2{margin:0;font-size:18px}.prep-sort{font-size:12px;color:#687a92}
        .prep-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px}.prep-card{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:16px;min-height:250px;display:flex;flex-direction:column;box-shadow:0 3px 10px rgba(36,62,101,.035)}
        .prep-card.done{border-top:3px solid #1ca978}.prep-card.warn{border-top:3px solid #ef8f34}.prep-card-top{display:flex;justify-content:space-between;align-items:center}.prep-icon{width:48px;height:48px;border-radius:50%;display:grid;place-items:center;background:#eaf2ff;color:#1268f3;font-size:23px}
        .prep-card:nth-child(4n+2) .prep-icon{background:#f2edff;color:#7958dd}.prep-card:nth-child(4n+3) .prep-icon{background:#fff1df;color:#f08022}.prep-card:nth-child(4n) .prep-icon{background:#e9f8f3;color:#159a70}
        .prep-card h3{font-size:14px;line-height:1.5;margin:14px 0 8px}.prep-card p{font-size:12px;color:#66768d;line-height:1.65;flex:1;margin:0 0 12px}.prep-state{padding:4px 8px;border-radius:99px;background:#edf9f4;font-size:10px;font-weight:800;color:#14976b}
        .prep-state.todo{background:#fff4e8;color:#df7a22}.prep-open{display:block;padding:9px;text-align:center;border:1px solid #9fc1ff;border-radius:8px;color:#1268f3!important;text-decoration:none!important;font-size:13px;font-weight:800}.prep-updated{text-align:center;color:#8190a4;font-size:10px;margin-top:10px}
        [class*="st-key-prep_card_"]{position:relative;background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:20px!important;margin-bottom:16px;box-shadow:0 4px 14px rgba(36,62,101,.045)}
        [class*="st-key-prep_card_"] .prep-card-body{min-height:280px;display:flex;flex-direction:column}
        [class*="st-key-prep_card_"] .prep-card-body h3{font-size:16px;line-height:1.5;margin:14px 0 8px}
        [class*="st-key-prep_card_"] .prep-card-body p{font-size:12px;color:#8290a3;line-height:1.65;margin:0 0 12px}
        .prep-card-top{padding-right:0}.prep-note{flex:1;margin-top:5px;padding:16px;border-radius:10px;background:#f7f9fd;color:#263a58;font-size:13px;line-height:1.85;white-space:pre-wrap;overflow:visible;word-break:break-word}
        .prep-note.empty{border:1px dashed #d7e0ed;background:#fbfcfe;color:#98a5b6;display:flex;align-items:center;justify-content:center;text-align:center;font-size:11px}
        [class*="st-key-prep_edit_"]{display:block;width:34px;margin-left:auto!important;margin-right:0!important;margin-bottom:-34px;position:relative;z-index:4}
        [class*="st-key-prep_edit_"] [data-testid="stPopover"] button{width:34px!important;height:32px!important;min-height:32px!important;padding:0!important;border:1px solid #c9d9f3!important;border-radius:8px!important;color:#1268f3!important;background:#fff!important;font-size:14px!important}
        [class*="st-key-prep_edit_"] [data-testid="stPopover"] button p{font-size:0!important}
        [class*="st-key-prep_edit_"] [data-testid="stPopover"] button p:after{content:'✎';font-size:14px}
        [class*="st-key-prep_card_"] textarea{min-height:150px!important;background:#f8faff}
        .prep-editor{margin-top:2px}.prep-editor-title{font-size:13px;font-weight:800;margin-bottom:8px;color:#263a58}
        [class*="st-key-prep_theme_"]{margin-bottom:12px}
        [class*="st-key-prep_theme_"] details{overflow:hidden;border:1px solid #dbe3ef!important;border-radius:12px!important;background:#fff!important;box-shadow:0 4px 14px rgba(36,62,101,.04)}
        [class*="st-key-prep_theme_"] details summary{min-height:64px;padding:12px 16px!important;background:#fff!important}
        [class*="st-key-prep_theme_"] details summary:hover{background:#f8fbff!important}
        [class*="st-key-prep_theme_"] details summary p{color:#17304f!important;font-size:14px!important;font-weight:850!important}
        [class*="st-key-prep_theme_"] details[open] summary{border-bottom:1px solid #e7ecf3;background:#f9fbff!important}
        [class*="st-key-prep_theme_"] [data-testid="stExpanderDetails"]{padding:14px 16px 16px!important}
        [class*="st-key-prep_theme_"] [data-testid="stTextArea"] textarea{min-height:210px!important;border:1px solid #dce5f1!important;border-radius:10px!important;background:#f7f9fd!important;color:#263a58!important;font-size:13px!important;line-height:1.75!important}
        [class*="st-key-prep_theme_"] .prep-theme-description{margin:0 0 9px;color:#74849a;font-size:12px;line-height:1.6}
        [class*="st-key-prep_theme_"] .prep-theme-updated{color:#8795a8;font-size:10px;text-align:right}
        [class*="st-key-prep_theme_"] [class*="st-key-prep_save_"] button{min-height:39px;border-radius:8px;font-size:13px;font-weight:850}
        .prep-side{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:18px;height:max-content;position:sticky;top:20px}.prep-side h3{font-size:16px;margin:0 0 16px}.prep-side dl{display:grid;grid-template-columns:78px 1fr;gap:12px 8px;font-size:12px}.prep-side dt{color:#738299}.prep-side dd{margin:0;font-weight:700}.prep-side-section{margin-top:18px;padding-top:18px;border-top:1px solid #e4e9f1}.prep-side-button{display:block;margin-top:12px;padding:9px;text-align:center;border:1px solid #a9c7fb;border-radius:8px;color:#1268f3!important;text-decoration:none!important;font-size:12px;font-weight:800}
        [class*="st-key-prep_sidebar_"]{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:18px;position:sticky;top:20px}
        [class*="st-key-prep_sidebar_"]>div[data-testid="stVerticalBlock"]{gap:.55rem}
        [class*="st-key-prep_sidebar_"] .prep-side-overview h3,
        [class*="st-key-prep_sidebar_"] .prep-ai-heading h3,
        [class*="st-key-prep_sidebar_"] .prep-reflection h3{margin:0 0 12px;color:#102846;font-size:16px;font-weight:800}
        [class*="st-key-prep_sidebar_"] .prep-side-overview dl{display:grid;grid-template-columns:72px 1fr;gap:10px 7px;margin:0;font-size:12px}
        [class*="st-key-prep_sidebar_"] .prep-side-overview dt{color:#738299}
        [class*="st-key-prep_sidebar_"] .prep-side-overview dd{margin:0;color:#102846;font-weight:700}
        [class*="st-key-prep_sidebar_"] .prep-ai-heading{margin-top:8px;padding-top:17px;border-top:1px solid #e4e9f1}
        [class*="st-key-prep_sidebar_"] .prep-ai-heading p,
        [class*="st-key-prep_sidebar_"] .prep-reflection p{margin:0;color:#66768d;font-size:12px;line-height:1.65}
        [class*="st-key-prep_sidebar_"] [data-testid="stSelectbox"] label p{color:#33465f;font-size:12px;font-weight:500}
        [class*="st-key-prep_sidebar_"] [data-baseweb="select"]>div{min-height:36px;border:0;background:#f5f7fa;border-radius:8px;font-size:12px}
        [class*="st-key-prep_sidebar_"] [class*="st-key-prep_ai_generate_"] button{min-height:37px;border:1px solid #a9c7fb;border-radius:8px;background:#fff;color:#1268f3;font-size:12px;font-weight:800;box-shadow:none}
        [class*="st-key-prep_sidebar_"] [class*="st-key-prep_ai_generate_"] button:hover{border-color:#1268f3;background:#f6f9ff;color:#1268f3}
        [class*="st-key-prep_sidebar_"] .prep-reflection{margin-top:8px;padding-top:17px;border-top:1px solid #e4e9f1}
        .analytics-page{margin-top:4px}.analytics-kicker{color:#1268f3;font-size:11px;font-weight:850;letter-spacing:.08em}.analytics-title{margin:5px 0 4px;color:#071a36;font-size:clamp(2rem,2.15vw,2.3rem);line-height:1.28;font-weight:800}.analytics-lead{margin:0;color:#66768d;font-size:13px;line-height:1.65}
        .analytics-section{margin:22px 0 0;padding:18px;background:#fff;border:1px solid #dbe3ef;border-radius:15px;box-shadow:0 8px 24px rgba(31,65,115,.045)}
        [class*="st-key-analytics_row_"]{gap:14px!important;margin-top:14px}[class*="st-key-analytics_row_"] .analytics-section{height:auto;margin:0}[class*="st-key-analytics_row_top"] .analytics-section{min-height:322px}[class*="st-key-analytics_row_bottom"] .analytics-section{min-height:336px}
        [class*="st-key-analytics_row_top"] .analytics-donut-layout{grid-template-columns:116px minmax(0,1fr);gap:9px}[class*="st-key-analytics_row_top"] .analytics-donut{width:112px;height:112px}[class*="st-key-analytics_row_top"] .analytics-chart-card{min-height:250px;padding:14px}[class*="st-key-analytics_row_top"] .analytics-legend{gap:5px}[class*="st-key-analytics_row_top"] .analytics-legend-row{gap:5px;padding-bottom:5px}
        [class*="st-key-analytics_row_bottom"] .analytics-route-grid{grid-template-columns:minmax(0,1.55fr) minmax(150px,.75fr);gap:10px}[class*="st-key-analytics_row_bottom"] .analytics-table th{padding:6px 4px;font-size:8px}[class*="st-key-analytics_row_bottom"] .analytics-table td{padding:7px 4px;font-size:9px}[class*="st-key-analytics_row_bottom"] .analytics-route-bars{padding:12px}[class*="st-key-analytics_row_bottom"] .analytics-route-bar{grid-template-columns:66px 1fr 28px;gap:6px;margin:9px 0;font-size:9px}
        .analytics-section-head{display:flex;align-items:center;gap:9px;margin-bottom:14px;color:#0d2548;font-size:16px;font-weight:850}.analytics-index{display:grid;place-items:center;width:23px;height:23px;border:1.5px solid #1268f3;border-radius:50%;color:#1268f3;font-size:11px;font-weight:900}
        .analytics-overview{display:grid;grid-template-columns:1fr;gap:0}.analytics-total-card{display:flex;align-items:center;justify-content:space-between;min-height:72px;padding:14px 18px;border:1px solid #cfe0f8;border-radius:13px;background:linear-gradient(145deg,#f7faff,#fff)}.analytics-total-card span{color:#526b8e;font-size:12px;font-weight:850}.analytics-total-card strong{color:#0d2548;font-size:30px;line-height:1;font-weight:900}.analytics-total-card strong small{font-size:11px;margin-left:4px}.analytics-breakdown{position:relative;margin-top:14px;padding:27px 0 0;border-top:1px solid #e8edf5}.analytics-breakdown:before{content:'全体の内訳';position:absolute;top:8px;left:2px;color:#8090a5;font-size:10px;font-weight:850}.analytics-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.analytics-metric{display:grid;grid-template-columns:36px minmax(0,1fr) auto;align-items:center;gap:10px;min-height:78px;padding:12px 14px;border:1px solid #dce5f2;border-radius:12px;background:linear-gradient(145deg,#fff,#f8fbff)}.analytics-metric.offer{border-color:#cceadf;background:linear-gradient(145deg,#fff,#f3fcf8)}
        .analytics-metric-icon{display:grid;place-items:center;width:36px;height:36px;border-radius:10px;background:#eaf2ff;color:#1268f3}.analytics-metric.offer .analytics-metric-icon{background:#e5f7ef;color:#159a70}.analytics-metric-icon svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}.analytics-metric-label{color:#52647d;font-size:11px;font-weight:800}.analytics-metric strong{color:#0d2548;font-size:24px;line-height:1;font-weight:900}.analytics-metric strong small{font-size:11px;margin-left:3px}.analytics-metric.offer strong{color:#138c71}
        .analytics-phase-grid{display:grid;grid-template-columns:minmax(0,1.08fr) minmax(0,.92fr);gap:14px}.analytics-chart-card{min-height:250px;padding:18px;border:1px solid #e0e7f1;border-radius:13px;background:#fff}.analytics-detail-card{position:relative;background:#fbfcfe;border-color:#e6ebf3}.analytics-detail-card:before{content:'大分類の内訳';position:absolute;right:16px;top:17px;padding:3px 7px;border-radius:999px;background:#eef3f8;color:#77879c;font-size:8px;font-weight:850}.analytics-card-title{display:flex;align-items:center;gap:7px;margin-bottom:16px;color:#263a58;font-size:13px;font-weight:850}.analytics-card-title i{width:7px;height:7px;border-radius:50%;background:#9fc5f8}
        .analytics-donut-layout{display:grid;grid-template-columns:178px minmax(0,1fr);align-items:center;gap:24px}.analytics-donut{position:relative;width:162px;height:162px;margin:auto}.analytics-donut svg{display:block;width:100%;height:100%;overflow:visible}.analytics-donut-track{fill:none;stroke:#f0f3f7;stroke-width:17}.analytics-donut-segment{fill:none;stroke-width:17;stroke-linecap:butt;transition:opacity .16s ease}.analytics-donut-center{position:absolute;inset:0;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#8794a5;font-size:9px;font-weight:750}.analytics-donut-center strong{margin-top:3px;color:#0d2548;font-size:27px;font-weight:900}.analytics-donut-center small{font-size:10px;margin-left:2px}.analytics-legend{display:grid;gap:9px}.analytics-legend-row{display:grid;grid-template-columns:9px minmax(0,1fr) auto auto;align-items:center;gap:8px;padding-bottom:7px;border-bottom:1px solid #f0f3f7;color:#53647b;font-size:11px}.analytics-legend-row:last-child{border-bottom:0}.analytics-legend-row i{width:8px;height:8px;border-radius:50%}.analytics-legend-row b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#435570}.analytics-legend-row span{font-weight:850;color:#0d2548}.analytics-legend-row em{min-width:34px;color:#8a98aa;font-size:9px;font-style:normal;text-align:right}
        .analytics-distribution-total{display:flex;align-items:baseline;gap:6px;margin:2px 0 18px;color:#708199;font-size:10px;font-weight:750}.analytics-distribution-total strong{color:#0d2548;font-size:28px;font-weight:900}.analytics-distribution-track{display:flex;width:100%;height:18px;overflow:hidden;border:4px solid #f3f6fa;border-radius:999px;background:#edf2f7;box-shadow:inset 0 0 0 1px #e6ebf2}.analytics-distribution-segment{height:100%;min-width:3px}.analytics-distribution-label{margin:8px 0 16px;color:#8795a7;font-size:9px}.analytics-distribution-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px 16px}.analytics-distribution-row{display:grid;grid-template-columns:9px minmax(0,1fr) auto;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #eef2f6;font-size:11px}.analytics-distribution-row i{width:8px;height:8px;border-radius:50%}.analytics-distribution-row b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#435570}.analytics-distribution-row span{color:#0d2548;font-weight:850}.analytics-distribution-row small{margin-left:4px;color:#8c9aab;font-size:9px}
        .analytics-flow{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:24px;margin-top:3px}.analytics-flow-step{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:83px;padding:11px;border:1px solid #e2e9f3;border-radius:12px;background:linear-gradient(160deg,#fff,#fafcff);text-align:center;color:#52647d;font-size:11px;font-weight:800}.analytics-flow-step:not(:last-child):after{content:'›';position:absolute;right:-17px;top:50%;transform:translateY(-54%);color:#b7cff5;font-size:27px;font-weight:500}.analytics-flow-step strong{margin-top:7px;color:#0d2548;font-size:24px;line-height:1;font-weight:900}.analytics-flow-step small{font-size:10px;margin-left:2px}.analytics-flow-step.final{border-color:#d9eee6;background:linear-gradient(160deg,#fff,#f7fcfa)}.analytics-flow-step.final strong{color:#398d75}.analytics-rate-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px}.analytics-rate{padding:14px;border:1px solid #e2e9f3;border-radius:11px;background:linear-gradient(180deg,#fff,#fcfdff);text-align:center;color:#52647d;font-size:11px;font-weight:800}.analytics-rate strong{display:block;margin:6px 0 3px;color:#0d2548;font-size:26px;font-weight:900}.analytics-rate span{color:#6685b5;font-size:9px}.analytics-rate.primary{border-color:#d4e3fa;background:linear-gradient(160deg,#f8fbff,#fff);box-shadow:inset 0 3px 0 #a8c9f8}.analytics-rate.primary strong{color:#356da9}.analytics-chart-note{margin:-8px 0 14px;color:#8290a3;font-size:10px;line-height:1.55}.analytics-detail-list{display:grid;gap:7px}.analytics-detail-row{display:grid;grid-template-columns:9px minmax(0,1fr) auto;align-items:center;gap:9px;min-height:30px;padding:4px 6px;border-bottom:1px solid #edf1f6;color:#52647d;font-size:11px}.analytics-detail-row:last-child{border-bottom:0}.analytics-detail-row i{width:8px;height:8px;border-radius:50%;box-shadow:0 0 0 3px rgba(157,190,231,.14)}.analytics-detail-row b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#263a58}.analytics-detail-row span{color:#0d2548;font-weight:850}.analytics-detail-row small{margin-left:3px;color:#8b99aa;font-size:9px}
        .analytics-route-grid{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.72fr);gap:16px}.analytics-table-wrap{overflow:auto;border:1px solid #e1e7f0;border-radius:11px}.analytics-table{width:100%;border-collapse:collapse;font-size:10px}.analytics-table th{padding:9px 10px;background:#f8faff;color:#60728c;text-align:center;white-space:nowrap}.analytics-table th:first-child{text-align:left}.analytics-table .analytics-group-head th{padding:7px 10px;background:#fbfcfe;color:#8996a8;font-size:8px;letter-spacing:.02em;border-bottom:1px solid #e8edf4}.analytics-table .analytics-group-head th+th{border-left:1px solid #e8edf4}.analytics-table td{padding:10px;border-top:1px solid #e8edf4;color:#263a58;text-align:center}.analytics-table td:first-child{text-align:left}.analytics-table tbody tr:hover{background:#fbfdff}.analytics-table .metric-cell{background:#fbfcff;color:#356da9;font-weight:850}.analytics-route-bars{padding:16px;border:1px solid #e1e7f0;border-radius:11px;background:#fcfdff}.analytics-route-bar{display:grid;grid-template-columns:94px 1fr 34px;align-items:center;gap:9px;margin:12px 0;color:#53647b;font-size:10px;font-weight:750}.analytics-route-bar label{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.analytics-route-track{height:8px;overflow:hidden;border-radius:99px;background:#eef3f9}.analytics-route-fill{height:100%;border-radius:99px;background:#8fbaf0}.analytics-route-bar b{text-align:right;color:#435570;font-size:10px}
        .analytics-route-list{display:grid;gap:12px}.analytics-route-card{padding:14px 16px;border:1px solid #e0e7f1;border-radius:12px;background:#fff}.analytics-route-head{display:flex;align-items:center;justify-content:space-between;gap:14px;padding-bottom:11px;border-bottom:1px solid #edf1f6}.analytics-route-head b{color:#263a58;font-size:12px}.analytics-route-head span{color:#73839a;font-size:9px;font-weight:750}.analytics-route-head strong{margin-left:5px;color:#0d2548;font-size:20px}.analytics-route-head small{font-size:9px;margin-left:2px}.analytics-route-detail-label{margin:10px 0 7px;color:#8795a7;font-size:9px;font-weight:800}.analytics-route-stages{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.analytics-route-stage{position:relative;padding:9px 10px;border-radius:9px;background:#f8faff;color:#6b7c92;font-size:9px}.analytics-route-stage:not(:last-child):after{content:'›';position:absolute;right:-6px;top:50%;transform:translateY(-50%);color:#b9c9de}.analytics-route-stage b{display:block;margin-top:4px;color:#263a58;font-size:15px}.analytics-route-outcome{display:flex;align-items:center;justify-content:space-between;margin-top:10px;padding-top:9px;border-top:1px dashed #e5ebf3;color:#6b7c92;font-size:9px}.analytics-route-outcome strong{color:#356da9;font-size:15px}
        .report-head{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin:2px 0 14px}.report-head h1{margin:0;color:#071a36;font-size:34px}.report-head p{margin:7px 0 0;color:#66768d;font-size:13px}.report-period{padding:9px 14px;border:1px solid #d8e2ef;border-radius:9px;background:#fff;color:#415571;font-size:12px;font-weight:750}
        [data-testid="stTabs"] [data-baseweb="tab-list"]{justify-content:flex-end;gap:8px;border:0;margin-bottom:12px}[data-testid="stTabs"] [data-baseweb="tab"]{height:40px;padding:0 18px;border:1px solid #d7e0ed;border-radius:9px;background:#fff;color:#61728a;font-weight:800}[data-testid="stTabs"] [aria-selected="true"]{background:#1268f3!important;color:#fff!important;border-color:#1268f3!important}[data-testid="stTabs"] [data-baseweb="tab-highlight"]{display:none}
        .report-summary{display:grid;grid-template-columns:repeat(6,1fr);margin-bottom:14px;padding:14px 8px;border:1px solid #dbe3ef;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)}.report-summary-item{display:flex;align-items:center;justify-content:center;gap:10px;min-height:62px;border-right:1px solid #e7ecf3}.report-summary-item:last-child{border:0}.report-summary-item span{color:#61728a;font-size:11px;font-weight:800}.report-summary-item strong{display:block;margin-top:4px;color:#0d2548;font-size:25px}.report-summary-item small{font-size:10px;margin-left:2px}
        .report-card{padding:17px 19px;border:1px solid #dbe3ef;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)}.report-card h2{margin:0 0 14px;color:#132b4c;font-size:16px}.report-card-desc{margin:-6px 0 10px;color:#66758c;font-size:12px;line-height:1.6;font-weight:650}.report-flow{display:grid;grid-template-columns:repeat(6,minmax(0,1fr) 38px) minmax(0,1fr);align-items:center;gap:0}.report-flow-step{position:relative;display:grid;place-items:center;min-height:84px;border:1.5px solid var(--c);border-radius:11px;color:var(--c);font-size:11px;font-weight:800}.report-flow-step strong{display:block;margin-top:5px;color:#0d2548;font-size:23px}.report-flow-step small{font-size:10px;margin-left:2px}.report-flow-connector{display:flex;min-width:0;flex-direction:column;align-items:center;justify-content:center;color:#71849d;font-style:normal;font-weight:850;line-height:1}.report-flow-connector span{font-size:10px;white-space:nowrap}.report-flow-connector i{margin-top:5px;font-size:22px;font-style:normal;font-weight:700}
        .report-bottom{display:grid;grid-template-columns:1.08fr .92fr;gap:14px;margin-top:14px}.report-bars{display:grid;gap:10px}.report-bar{display:grid;grid-template-columns:105px 1fr 42px 58px;align-items:center;gap:9px;color:#52647d;font-size:10px}.report-track{height:8px;border-radius:99px;background:#edf2f8;overflow:hidden}.report-fill{height:100%;border-radius:99px;background:var(--c)}.report-bar b{color:#0d2548;text-align:right}.report-bar small{color:#74859b;text-align:right}.report-insight{display:grid;grid-template-columns:1fr 1fr 1fr;align-items:center;min-height:150px;border:1px solid #ded7fb;border-radius:11px;background:#fdfcff}.report-insight>div{padding:15px;text-align:center;border-right:1px solid #e4e8f0}.report-insight>div:last-child{border:0}.report-insight strong{display:block;margin-top:5px;color:#0d2548;font-size:25px}.report-insight .accent strong{color:#7651e6;font-size:38px}
        .report-rank-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.report-rank-card{padding:15px;border:1px solid #dbe3ef;border-radius:13px;background:#fff}.report-rank-card h3{margin:0 0 10px;font-size:14px}.report-winner{margin-bottom:12px;padding:9px;border:1px solid var(--c);border-radius:8px;color:var(--c);font-size:11px;font-weight:800}.report-axis-title{display:flex;align-items:center;justify-content:space-between;margin:14px 0 8px}.report-axis-title h2{margin:0;font-size:16px}.report-table-wrap{overflow:hidden;border:1px solid #dde5ef;border-radius:10px}.report-table{width:100%;border-collapse:collapse;font-size:9px}.report-table th,.report-table td{padding:7px;border:1px solid #e3e8f0;text-align:center}.report-table th{background:#f8faff;color:#52647d}.report-table td:first-child{font-weight:800;text-align:left;background:#fff}.report-cell b{display:block;font-size:14px}.report-cell small{font-size:8px}.report-ref{display:inline-block;margin-left:3px;padding:1px 4px;border:1px solid #cbd6e5;border-radius:4px;color:#6d7d92;font-size:7px}
        /* レポートの縦横比を維持し、余白を情報の視認性へ振り替える。 */
        .report-head{margin-bottom:6px}.report-head h1{font-size:44px;font-weight:950;letter-spacing:-.03em}.report-head p{margin-top:3px;font-size:18px;font-weight:700}.report-period{padding:6px 10px;font-size:17px;font-weight:950}
        [data-testid="stTabs"] [data-baseweb="tab-list"]{margin-bottom:5px}[data-testid="stTabs"] [data-baseweb="tab"]{height:38px;padding:0 13px;font-size:18px;font-weight:950}
        .report-summary{margin-bottom:7px;padding:4px 3px}.report-summary-item{min-height:50px}.report-summary-item span{font-size:17px;font-weight:950}.report-summary-item strong{margin-top:0;font-size:38px;font-weight:950}.report-summary-item small{font-size:14px;font-weight:900}
        .report-card{padding:7px 10px}.report-card h2{margin-bottom:6px;font-size:24px;font-weight:950}.report-flow-step{min-height:70px;padding:2px;font-size:16px;font-weight:950}.report-flow-step strong{margin-top:1px;font-size:35px;font-weight:950}.report-flow-step small{font-size:14px;font-weight:900}.report-flow-connector span{font-size:12px;font-weight:950}.report-flow-connector i{margin-top:4px;font-size:25px;font-weight:900}
        .report-bottom{gap:7px;margin-top:7px}.report-bars{gap:5px}.report-bar{grid-template-columns:140px 1fr 58px 152px;gap:6px;font-size:17px;font-weight:900}.report-track{height:11px}.report-bar b{font-size:17px;font-weight:950}.report-bar small{font-size:14px;font-weight:850}.report-insight{min-height:126px}.report-insight>div{padding:5px;font-size:18px;font-weight:900}.report-insight strong{font-size:40px;font-weight:950}.report-insight .accent strong{font-size:54px}
        .report-rank-grid{gap:10px}.report-rank-card{min-height:210px;padding:10px 12px;box-sizing:border-box}.report-rank-card h3{margin-bottom:7px;font-size:18px;line-height:1.2;font-weight:950}.report-winner{margin-bottom:7px;padding:6px 9px;font-size:15px;line-height:1.2;font-weight:950}.report-rank-card .report-bars{gap:6px}.report-rank-card .report-bar{grid-template-columns:minmax(112px,1.25fr) minmax(62px,.7fr) 48px 78px;font-size:14px;line-height:1.18}.report-rank-card .report-bar b{font-size:14px}.report-rank-card .report-bar small{font-size:11px}.report-axis-title{margin:-17px 0 2px}.report-axis-title h2{font-size:21px;line-height:1.15;font-weight:950}.report-table{font-size:13px}.report-table th,.report-table td{height:38px;padding:2px 5px;box-sizing:border-box}.report-table th{height:31px;font-size:13px;font-weight:950}.report-table td:first-child{font-size:13px;font-weight:950}.report-cell b{font-size:18px;line-height:1;font-weight:950}.report-cell small{font-size:10px;line-height:1;font-weight:850}.report-ref{font-size:9px;font-weight:950}
        [data-testid="stTabs"] [data-testid="stTabs"] [role="tabpanel"] [data-testid="stVerticalBlock"]{gap:.45rem!important}
        /* UIイメージに合わせた3階層のタブ表現。 */
        [data-testid="stTabs"] [data-baseweb="tab-list"]{box-shadow:none!important}
        [data-testid="stTabs"] [data-baseweb="tab"]{display:flex;align-items:center;justify-content:center;min-width:0;border:1px solid #d6e0ef!important;border-radius:10px!important;background:#fff!important;color:#304566!important;box-shadow:0 2px 7px rgba(31,65,115,.035);font-family:inherit!important;font-size:16px!important;font-weight:850!important;letter-spacing:0!important}
        [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"]{border-color:#1268f3!important;background:linear-gradient(180deg,#2478f7,#1268f3)!important;color:#fff!important;box-shadow:0 5px 12px rgba(18,104,243,.18)}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(6)){display:grid!important;grid-template-columns:178px repeat(6,minmax(0,1fr));align-items:center;gap:10px!important;margin:0 0 12px!important;padding:12px 14px!important;border:1px solid #dbe3ef!important;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)!important}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(6))::before{content:'分析する選考フェーズ';color:#0d2548;font-size:17px;font-weight:950}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(6)) [data-baseweb="tab"]{width:100%;height:42px!important;padding:0 8px!important}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(3)):not(:has([role="tab"]:nth-of-type(4))){display:grid!important;grid-template-columns:178px repeat(3,118px) 1fr;align-items:center;gap:0!important;margin:10px 0 7px!important;padding:10px 14px!important;border:1px solid #dbe3ef!important;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)!important}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(3)):not(:has([role="tab"]:nth-of-type(4)))::before{content:'分析軸を切り替え';color:#0d2548;font-size:17px;font-weight:950}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(3)):not(:has([role="tab"]:nth-of-type(4))) [data-baseweb="tab"]{height:38px!important;padding:0 10px!important;border-radius:0!important;box-shadow:none!important}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(3)):not(:has([role="tab"]:nth-of-type(4))) [data-baseweb="tab"]:first-of-type{border-radius:9px 0 0 9px!important}
        [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(3)):not(:has([role="tab"]:nth-of-type(4))) [data-baseweb="tab"]:nth-of-type(3){border-radius:0 9px 9px 0!important}
        [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(2)):not(:has([role="tab"]:nth-of-type(3))){display:grid!important;grid-template-columns:178px repeat(2,118px) 1fr;align-items:center;gap:0!important;margin:10px 0 7px!important;padding:10px 14px!important;border:1px solid #dbe3ef!important;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)!important}
        [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(2)):not(:has([role="tab"]:nth-of-type(3)))::before{content:'分析軸を切り替え';color:#0d2548;font-size:17px;font-weight:950}
        [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(2)):not(:has([role="tab"]:nth-of-type(3))) [data-baseweb="tab"]{height:38px!important;padding:0 10px!important;border-radius:0!important;box-shadow:none!important}
        [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(2)):not(:has([role="tab"]:nth-of-type(3))) [data-baseweb="tab"]:first-of-type{border-radius:9px 0 0 9px!important}
        [data-testid="stTabs"] [data-testid="stTabs"] [data-baseweb="tab-list"]:has([role="tab"]:nth-of-type(2)):not(:has([role="tab"]:nth-of-type(3))) [data-baseweb="tab"]:nth-of-type(2){border-radius:0 9px 9px 0!important}
        /* Streamlit React Aria版の実DOMへ適用するタブデザイン。 */
        [data-testid="stTabs"] [role="tablist"]{display:flex;justify-content:flex-start;align-items:center;gap:10px;margin:0 0 10px;padding:0;border:0;background:transparent;box-shadow:none}
        [data-testid="stTabs"] [data-testid="stTab"]{display:flex;align-items:center;justify-content:center;height:44px;padding:0 18px;border:1px solid #d6e0ef!important;border-radius:10px!important;background:#fff!important;color:#304566!important;box-shadow:0 2px 7px rgba(31,65,115,.035);font-family:inherit!important;font-size:16px!important;font-weight:850!important;white-space:nowrap}
        [data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"]{border-color:#1268f3!important;background:linear-gradient(180deg,#2478f7,#1268f3)!important;color:#fff!important;box-shadow:0 5px 12px rgba(18,104,243,.18)}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(6)){display:grid!important;grid-template-columns:178px repeat(6,minmax(0,1fr));gap:10px!important;margin:0 0 6px!important;padding:9px 14px!important;border:1px solid #dbe3ef!important;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)!important}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(6))::before{content:'分析する選考フェーズ';color:#0d2548;font-size:17px;font-weight:950}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(6)) > [data-testid="stTab"]{width:100%;height:40px;padding:0 8px}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(3)):not(:has(> [data-testid="stTab"]:nth-child(4))){display:grid!important;grid-template-columns:178px repeat(3,118px) 1fr;gap:0!important;margin:10px 0 7px!important;padding:10px 14px!important;border:1px solid #dbe3ef!important;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)!important}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(3)):not(:has(> [data-testid="stTab"]:nth-child(4)))::before{content:'分析軸を切り替え';color:#0d2548;font-size:17px;font-weight:950}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(3)):not(:has(> [data-testid="stTab"]:nth-child(4))) > [data-testid="stTab"]{height:38px;padding:0 10px;border-radius:0!important;box-shadow:none}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(3)):not(:has(> [data-testid="stTab"]:nth-child(4))) > [data-testid="stTab"]:first-of-type{border-radius:9px 0 0 9px!important}
        [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(3)):not(:has(> [data-testid="stTab"]:nth-child(4))) > [data-testid="stTab"]:nth-of-type(3){border-radius:0 9px 9px 0!important}
        [data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(2)):not(:has(> [data-testid="stTab"]:nth-child(3))){display:grid!important;grid-template-columns:178px repeat(2,118px) 1fr;gap:0!important;margin:10px 0 7px!important;padding:10px 14px!important;border:1px solid #dbe3ef!important;border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(31,65,115,.045)!important}
        [data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(2)):not(:has(> [data-testid="stTab"]:nth-child(3)))::before{content:'分析軸を切り替え';color:#0d2548;font-size:17px;font-weight:950}
        [data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(2)):not(:has(> [data-testid="stTab"]:nth-child(3))) > [data-testid="stTab"]{height:38px;padding:0 10px;border-radius:0!important;box-shadow:none}
        [data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(2)):not(:has(> [data-testid="stTab"]:nth-child(3))) > [data-testid="stTab"]:first-of-type{border-radius:9px 0 0 9px!important}
        [data-testid="stTabs"] [data-testid="stTabs"] [role="tablist"]:has(> [data-testid="stTab"]:nth-child(2)):not(:has(> [data-testid="stTab"]:nth-child(3))) > [data-testid="stTab"]:nth-of-type(2){border-radius:0 9px 9px 0!important}
        .report-period-label{margin:0 0 5px;color:#0d2548;font-size:15px;font-weight:950;text-align:left}
        [class*="st-key-report_period_popover"] button{min-height:44px!important;border:1px solid #d6e0ef!important;border-radius:10px!important;background:#fff!important;color:#304566!important;box-shadow:0 2px 7px rgba(31,65,115,.035)!important;font-size:15px!important;font-weight:850!important}
        [class*="st-key-report_period_popover"] button [data-testid="stIconMaterial"]{color:#1268f3!important;font-size:20px!important}
        @media(min-width:901px){
          .report-summary{min-height:96px;box-sizing:border-box}.report-summary-item{min-height:82px}
          .report-flow{min-height:128px}.report-flow-step{min-height:104px}
          .report-bottom .report-card{min-height:286px;box-sizing:border-box}
          .report-bottom .report-bars{min-height:220px;align-content:space-evenly}
          .report-bottom .report-insight{min-height:220px}
        }
        @media(max-width:900px){.report-summary{grid-template-columns:repeat(2,1fr)}.report-summary-item{border-bottom:1px solid #e7ecf3}.report-flow{grid-template-columns:1fr}.report-flow-connector{min-height:42px}.report-flow-connector i{font-size:0}.report-flow-connector i:after{content:'↓';font-size:24px}.report-bottom,.report-rank-grid{grid-template-columns:1fr}.report-table-wrap{overflow:auto}}
        @media(max-width:1050px){.analytics-donut-layout{grid-template-columns:150px 1fr}.analytics-donut{width:142px;height:142px}.analytics-donut:after{inset:31px}.analytics-flow{gap:16px}.analytics-flow-step:not(:last-child):after{right:-12px}.analytics-rate-grid{grid-template-columns:repeat(2,1fr)}}
        @media(max-width:800px){.analytics-overview{grid-template-columns:1fr}.analytics-summary{grid-template-columns:1fr}.analytics-phase-grid,.analytics-route-grid{grid-template-columns:1fr}.analytics-flow{grid-template-columns:1fr}.analytics-flow-step:not(:last-child):after{content:'⌄';right:auto;top:auto;bottom:-22px;left:50%}.analytics-rate-grid{grid-template-columns:1fr}.analytics-donut-layout{grid-template-columns:1fr}[class*="st-key-analytics_row_"]{display:block!important}[class*="st-key-analytics_row_"] [data-testid="stColumn"]{margin-bottom:14px}}
        @media(max-width:1100px){.prep-grid{grid-template-columns:repeat(2,1fr)}.prep-layout{grid-template-columns:1fr}.prep-side{position:static}.detail-grid{grid-template-columns:1fr}.detail-hero{grid-template-columns:1fr}.detail-hero>div{border-right:0;border-bottom:1px solid #e6ebf2}}
        @media(max-width:700px){.prep-chooser-grid{grid-template-columns:1fr}}
        @media(max-width:900px){.summary-grid,.funnel{grid-template-columns:repeat(2,1fr)}.app-meta{grid-template-columns:1fr}.bar-row{grid-template-columns:110px 1fr 50px}
          [class*="st-key-application_workspace"] [data-testid="stColumn"]:last-child { border-left:0; padding-left:0; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _tabs(active: str) -> None:
    st.markdown(
        '<div class="app-tabs">'
        f'<a class="{"active" if active == "management" else ""}" href="?page=application_list&amp;focus=all">応募管理</a>'
        f'<a class="{"active" if active == "dashboard" else ""}" href="?page=application_dashboard">選考通過率レポート</a>'
        '</div>', unsafe_allow_html=True,
    )


def _summary_icon(kind: str) -> str:
    """応募状況カード用の装飾アイコンを返す。"""

    icons = {
        "preparation": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<rect x="5" y="4" width="14" height="17" rx="2"/>'
            '<path d="M9 4.5v-.7A1.8 1.8 0 0 1 10.8 2h2.4A1.8 1.8 0 0 1 15 3.8v.7"/>'
            '<path d="m8 12 2 2 5-5"/><path d="M8 18h8"/></svg>'
        ),
        "active": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<circle cx="9" cy="8" r="3"/>'
            '<path d="M3.5 20v-1.5A4.5 4.5 0 0 1 8 14h2a4.5 4.5 0 0 1 4.5 4.5V20"/>'
            '<circle cx="17" cy="9" r="2.5"/><path d="M16 14h1a4 4 0 0 1 4 4v1"/>'
            '</svg>'
        ),
        "upcoming": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<rect x="3" y="5" width="18" height="16" rx="2"/>'
            '<path d="M7 3v4M17 3v4M3 10h18"/><path d="m8 15 2 2 5-5"/>'
            '</svg>'
        ),
        "alert": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M12 3 2.8 20h18.4L12 3Z"/><path d="M12 9v5M12 17.5h.01"/>'
            '</svg>'
        ),
        "offer": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M8 4h8v4a4 4 0 0 1-8 0V4Z"/>'
            '<path d="M8 6H4v1a4 4 0 0 0 4 4M16 6h4v1a4 4 0 0 1-4 4M12 12v5M8 21h8M9 17h6"/>'
            '</svg>'
        ),
    }
    return icons.get(kind, icons["preparation"])


def _summary_cards(items: list[tuple], page_name: str = "") -> None:
    selected_focus = str(
        st.query_params.get("focus", "")
    ).strip()
    valid_focuses = {
        "preparation",
        "active",
        "upcoming",
        "attention",
    }
    if selected_focus not in valid_focuses:
        selected_focus = ""
    html = '<div class="summary-grid application-summary-grid">'
    for item in items:
        label, value, kind = item[:3]
        unit = item[3] if len(item) >= 4 else "社"
        focus = item[4] if len(item) >= 5 else ""
        card_html = (
            f'<div class="summary-card {kind}">'
            f'<div class="summary-icon">{_summary_icon(kind)}</div>'
            f'<div class="summary-label">{escape(label)}</div>'
            f'<div class="summary-value">{value}<small>{escape(unit)}</small></div>'
            '</div>'
        )
        if page_name and focus:
            try:
                is_disabled = int(value) <= 0
            except (TypeError, ValueError):
                is_disabled = False

            if is_disabled:
                html += (
                    '<div class="summary-link disabled" aria-disabled="true">'
                    f'{card_html}</div>'
                )
            else:
                selected_class = " selected" if selected_focus == focus else ""
                target_focus = "all" if selected_focus == focus else focus
                target = f"?page={escape(page_name)}&amp;focus={escape(target_focus)}"
                if target_focus != "all":
                    target += "#application-notifications"
                html += (
                    f'<a class="summary-link{selected_class}" '
                    f'target="_self" href="{target}">'
                    f'{card_html}</a>'
                )
        else:
            html += card_html
    st.markdown(html + '</div>', unsafe_allow_html=True)


def _render_focus_context(selected_focus: str, count: int) -> None:
    focus_labels = {
        "preparation": ("応募準備", "社"),
        "active": ("選考中", "社"),
        "upcoming": ("近日予定", "件"),
        "attention": ("対応が必要", "件"),
    }
    if selected_focus not in focus_labels:
        return

    label, unit = focus_labels[selected_focus]
    with st.container(key="application_focus_context"):
        message_col, action_col = st.columns([5, 1])
        message_col.markdown(f"{label}の{count}{unit}を表示中")
        if action_col.button("絞り込みを解除", key="clear_application_focus", use_container_width=True):
            st.session_state["application_overview_focus"] = ""
            st.rerun()


def _clear_application_list_filters() -> None:
    """選考スケジュールの絞り込み・並び替えを初期状態へ戻す。"""

    defaults = {
        "app_query": "",
        "app_phase": "すべて",
        "app_route": "すべて",
        "app_response_status": "すべて",
        "app_sort_order": "対応が必要な順",
    }
    for key, value in defaults.items():
        st.session_state[key] = value
    st.session_state["application_overview_focus"] = ""
    st.session_state["application_task_focus"] = False
    _close_schedule_dialog_for_filter_change()


def _close_schedule_dialog_for_filter_change() -> None:
    """絞り込みによる再描画で、以前閉じた応募詳細を再表示しない。"""

    st.session_state.pop("schedule_dialog_application_id", None)


def _render_application_list_header_filters(
    phase_filters: list[str], routes: list[str], filters_active: bool,
) -> None:
    """選考表の前に、検索・絞り込みを一か所へまとめて表示する。"""

    with st.container(key="application_list_header_filters"):
        st.markdown(
            '<div class="schedule-toolbar-title">'
            '<div><strong>表示する応募を絞り込む</strong>'
            '<span>条件を組み合わせて、確認したい企業だけを表示できます。</span></div>'
            f'<span class="schedule-filter-state">{"絞り込み中" if filters_active else "すべて表示"}</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        company_col, phase_col, route_col, response_col, sort_col, clear_col = st.columns(
            [1.45, 1, 1, 1, 1.15, 0.7],
        )
        with company_col:
            st.text_input(
                "会社名",
                key="app_query",
                placeholder="会社名で検索",
                on_change=_close_schedule_dialog_for_filter_change,
            )
        with phase_col:
            st.selectbox(
                "現在フェーズ", ["すべて", *phase_filters], key="app_phase",
                on_change=_close_schedule_dialog_for_filter_change,
            )
        with route_col:
            st.selectbox(
                "応募経路", ["すべて", *routes], key="app_route",
                on_change=_close_schedule_dialog_for_filter_change,
            )
        with response_col:
            st.selectbox(
                "対応状態", ["すべて", "対応が必要", "近日予定", "通常"],
                key="app_response_status",
                on_change=_close_schedule_dialog_for_filter_change,
            )
        with sort_col:
            st.selectbox(
                "並び替え",
                ["対応が必要な順", "次回予定が近い順", "最終更新が新しい順",
                 "最終更新が古い順", "会社名順", "応募日が新しい順", "現在フェーズ順"],
                key="app_sort_order",
                on_change=_close_schedule_dialog_for_filter_change,
            )
        with clear_col:
            st.markdown('<div class="schedule-toolbar-spacer" aria-hidden="true"></div>', unsafe_allow_html=True)
            st.button(
                "条件をクリア" if filters_active else "条件なし",
                key="clear_application_list_filters",
                on_click=_clear_application_list_filters,
                use_container_width=True,
                disabled=not filters_active,
            )


def _is_ended_application(view: dict) -> bool:
    """Return True when an application has ended by withdrawal or rejection."""

    application = view["application"]
    ended_results = {"辞退", "不合格"}
    return bool(
        application.status != "active"
        or application.selection_result in ended_results
        or application.current_phase in ended_results
    )


def _render_ended_applications(views: list[dict]) -> None:
    """Render ended applications separately from the active selection schedule."""

    with st.container(key="ended_applications_section"):
        with st.expander(f"終了済み企業一覧（{len(views)}社）", expanded=False):
            if not views:
                st.caption("終了済みの企業はありません。")
                return
            rows = []
            for view in views:
                application, job = view["application"], view["job"]
                result = (
                    application.selection_result
                    if application.selection_result in {"辞退", "不合格"}
                    else application.current_phase or "終了"
                )
                rows.append(
                    '<div class="ended-application-row">'
                    f'<strong>{escape(job.company_name)}</strong>'
                    f'<span>{escape(job.job_title or "求人名未登録")}</span>'
                    f'<span class="ended-application-result">{escape(result)}</span>'
                    '</div>'
                )
            st.markdown(
                f'<div class="ended-application-list">{"".join(rows)}</div>',
                unsafe_allow_html=True,
            )


def _display_milestone_date(value: str) -> str:
    if not value:
        return "日付未定"
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    weekdays = "月火水木金土日"
    return f"{parsed.month}/{parsed.day}（{weekdays[parsed.weekday()]}）"


def _milestone_title(milestone: ApplicationMilestone) -> str:
    return milestone.title or milestone.detail_name or milestone.milestone_type


def _milestone_visual_category(milestone: ApplicationMilestone) -> str:
    """予定を、利用者が直感的に判別できる3つの行動主体へ分類する。"""

    searchable = " ".join(
        filter(
            None,
            (
                milestone.milestone_type,
                milestone.title,
                milestone.detail_name,
                milestone.memo,
            ),
        )
    )
    if milestone.milestone_type == "応募" or _milestone_title(milestone).strip() == "応募":
        return "personal"
    if any(keyword in searchable for keyword in ("エージェント", "紹介会社", "キャリアアドバイザー")):
        return "agent"
    if (
        milestone.milestone_type
        in {
            "応募", "書類提出", "適性検査", "カジュアル面談", "一次面接",
            "二次面接", "最終面接", "その他の面接・選考", "オファー面談",
            "条件面談", "回答期限",
        }
        or any(keyword in searchable for keyword in ("企業", "採用担当", "面接", "面談", "選考"))
    ):
        return "company"
    return "personal"


def _render_attention_panel(items: list[dict]) -> None:
    if not items:
        return

    rows = []
    for item in items[:5]:
        view, milestone = item["view"], item["milestone"]
        company_name = view["job"].company_name
        action_name = _milestone_title(milestone)
        deadline = _display_milestone_date(milestone.scheduled_date)
        rows.append(
            '<li><div class="attention-row">'
            '<span class="attention-status">要対応</span>'
            '<div class="attention-main">'
            f'<strong>{escape(company_name)}</strong>'
            f'<span class="attention-action">{escape(action_name)}</span>'
            '</div>'
            '<div class="attention-deadline">'
            '<span class="attention-deadline-label">期限</span>'
            f'<span class="attention-date">{escape(deadline)}</span>'
            '</div>'
            f'<a class="attention-button" target="_self" href="?page=application_list&amp;'
            f'application_id={view["application"].id}&amp;milestone_id={milestone.id}'
            f'#attention-action-{milestone.id}">対応する</a>'
            '</div></li>'
        )
    attention_icon = (
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="M12 3 22 20H2L12 3Z" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M12 9v5" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round"/>'
        '<circle cx="12" cy="17" r="1" fill="currentColor"/>'
        '</svg>'
    )
    st.markdown(
        '<section class="attention-panel">'
        '<div class="panel-heading attention">'
        f'<span class="panel-heading-icon attention-heading-icon">{attention_icon}</span>'
        '<span>対応が必要</span>'
        f'<span class="attention-count">{len(items)}件</span>'
        '</div>'
        '<p class="attention-description">'
        '期限が近い、または期限を過ぎた予定です。内容を確認して次の対応を進めてください。'
        '</p>'
        f'<ul class="attention-list">{"".join(rows)}</ul>'
        '</section>',
        unsafe_allow_html=True,
    )

def _render_upcoming_panel(items: list[dict]) -> None:
    calendar_icon = (
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<rect x="3.5" y="5.5" width="17" height="15" rx="2.5"/>'
        '<path d="M8 3.5v4M16 3.5v4M3.5 10h17"/>'
        '</svg>'
    )
    chevron_icon = (
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="m9 5 7 7-7 7"/>'
        '</svg>'
    )
    rows = []
    for item in items[:6]:
        view, milestone = item["view"], item["milestone"]
        company_name = view["job"].company_name
        rows.append(
            f'<a class="schedule-row" href="?page=application_list&amp;application_id={view["application"].id}">'
            f'<div class="schedule-date">{escape(_display_milestone_date(milestone.scheduled_date))}</div>'
            f'<div class="schedule-title">{escape(company_name)}：{escape(_milestone_title(milestone))}'
            f'<div class="schedule-meta">{escape(milestone.milestone_type)}</div></div>'
            f'<div class="schedule-arrow">{chevron_icon}</div>'
            '</a>'
        )
    content = (
        f'<div class="schedule-list">{"".join(rows)}</div>'
        if rows else
        '<div class="schedule-empty">直近1週間の予定はありません。</div>'
    )
    st.markdown(
        '<section class="panel schedule-panel">'
        f'<div class="panel-heading"><span class="panel-heading-icon">{calendar_icon}</span>'
        '<span>直近1週間の予定</span></div>'
        f'{content}</section>',
        unsafe_allow_html=True,
    )


@st.fragment
def _render_application_notifications(
    views: list[dict], summary: dict, selected_focus: str,
) -> None:
    notifications: list[dict] = []
    for item in summary["attention_items"]:
        view, milestone = item["view"], item["milestone"]
        notifications.append({
            "kind": "attention", "label": "対応が必要",
            "date": _display_milestone_date(milestone.scheduled_date),
            "sort": (0, item["date"]), "company": view["job"].company_name,
            "phase": view["application"].current_phase or view["application"].phase_category or "未設定",
            "task": _milestone_title(milestone),
            "application_id": view["application"].id, "milestone_id": milestone.id,
            "action": "対応する",
        })
    for item in summary["upcoming_items"]:
        view, milestone = item["view"], item["milestone"]
        notifications.append({
            "kind": "upcoming", "label": "近日予定",
            "date": _display_milestone_date(milestone.scheduled_date),
            "sort": (1, item["date"]), "company": view["job"].company_name,
            "phase": view["application"].current_phase or view["application"].phase_category or "未設定",
            "task": _milestone_title(milestone),
            "application_id": view["application"].id, "milestone_id": milestone.id,
            "action": "確認する",
        })
    for view in views:
        application = view["application"]
        if application.status != "active":
            continue
        if application.id in summary["preparation_application_ids"]:
            next_milestone = view.get("next_milestone")
            notifications.append({
                "kind": "preparation", "label": "応募準備", "date": "期限未設定",
                "sort": (2, date.max), "company": view["job"].company_name,
                "phase": application.current_phase or application.phase_category or "応募準備",
                "task": _milestone_title(next_milestone) if next_milestone else "応募情報を確認",
                "application_id": application.id,
                "milestone_id": next_milestone.id if next_milestone else 0,
                "action": "確認する",
            })
        elif application.id in summary["active_application_ids"]:
            phase = application.current_phase or application.phase_category or "選考中"
            next_milestone = view.get("next_milestone")
            notifications.append({
                "kind": "active", "label": "選考中", "date": "進行中",
                "sort": (3, date.max), "company": view["job"].company_name,
                "phase": phase,
                "task": _milestone_title(next_milestone) if next_milestone else "進行状況を確認",
                "application_id": application.id,
                "milestone_id": next_milestone.id if next_milestone else 0,
                "action": "確認する",
            })
    if selected_focus:
        notifications = [row for row in notifications if row["kind"] == selected_focus]
    notifications.sort(key=lambda row: row["sort"])
    icons = {
        "attention": '<path d="M12 3 22 20H2L12 3Z"/><path d="M12 9v5"/><circle cx="12" cy="17" r="1"/>',
        "upcoming": '<rect x="3.5" y="5.5" width="17" height="15" rx="2.5"/><path d="M8 3.5v4M16 3.5v4M3.5 10h17"/>',
        "preparation": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M8 10l2 2 5-5"/>',
        "active": '<circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M3 20v-2a5 5 0 0 1 10 0v2M13 20v-2a5 5 0 0 1 8-4"/>',
    }
    visible_notifications = notifications[:8]
    current_label = {
        "attention": "対応が必要", "upcoming": "近日予定",
        "preparation": "応募準備", "active": "選考中",
    }.get(selected_focus, "すべて")
    remaining_count = max(0, len(notifications) - len(visible_notifications))
    remaining_html = (
        f'<div class="notification-more">ほか{remaining_count}件のお知らせがあります。'
        '上の状況カードで絞り込んで確認できます。</div>'
        if remaining_count
        else ""
    )
    st.markdown(
        '<span id="application-notifications" class="application-anchor"></span>'
        '<section class="application-notifications"><div class="notification-heading">'
        '<div><strong>お知らせ</strong><span>次に確認する内容を、優先度の高い順に表示しています。</span></div>'
        f'<span class="notification-filter {escape(selected_focus)}">{escape(current_label)}を表示中</span></div></section>',
        unsafe_allow_html=True,
    )
    if not visible_notifications:
        st.markdown('<div class="notification-empty">該当するお知らせはありません。</div>', unsafe_allow_html=True)
        return

    for row in visible_notifications:
        item_key = f'notification_item_{row["kind"]}_{row["application_id"]}_{row["milestone_id"]}'
        with st.container(key=item_key):
            kind_col, date_col, main_col, action_col = st.columns([1.05, .78, 4.25, .82])
            kind_col.markdown(
                f'<span class="notification-kind"><svg viewBox="0 0 24 24" aria-hidden="true">'
                f'{icons[row["kind"]]}</svg><span>{escape(row["label"])}</span></span>',
                unsafe_allow_html=True,
            )
            date_col.markdown(f'<span class="notification-date">{escape(row["date"])}</span>', unsafe_allow_html=True)
            main_col.markdown(
                f'<div class="notification-main"><strong>{escape(row["company"])}</strong>'
                '<div class="notification-meta">'
                f'<div class="notification-field"><span class="notification-field-label">フェーズ</span>'
                f'<span class="notification-field-value">{escape(row["phase"])}</span></div>'
                f'<div class="notification-field"><span class="notification-field-label">次のタスク</span>'
                f'<span class="notification-field-value">{escape(row["task"])}</span></div></div></div>',
                unsafe_allow_html=True,
            )
            if action_col.button(
                row["action"],
                key=f'filter_schedule_from_{item_key}',
                use_container_width=True,
            ):
                # 状況カードの絞り込みとは分離し、このお知らせの対象企業だけを
                # 選考スケジュールへ表示する。
                st.session_state["notification_schedule_application_id"] = int(row["application_id"])
                st.session_state["notification_schedule_kind"] = str(row["kind"])
                st.rerun()

    if remaining_html:
        st.markdown(remaining_html, unsafe_allow_html=True)


def _application_status_controls(summary: dict, selected_focus: str) -> str:
    items = [
        ("応募準備", summary["preparation"], "社", "preparation", "入力内容を確認", ":material/assignment_turned_in:"),
        ("選考中", summary["active"], "社", "active", "進行状況を確認", ":material/groups:"),
        ("近日予定", summary["upcoming"], "件", "upcoming", "今後の予定を確認", ":material/calendar_month:"),
        ("対応が必要", summary["attention"], "件", "attention", "優先して確認", ":material/warning:"),
    ]
    css_rules = []
    category_styles = {
        "preparation": {
            "accent": "#1268f3", "border": "#c8dcff", "icon_bg": "#e8f1ff",
            "surface": "linear-gradient(135deg,#ffffff 0%,#f3f7ff 100%)",
            "selected": "linear-gradient(135deg,#edf5ff 0%,#f8fbff 100%)",
            "shadow": "rgba(18,104,243,.16)",
        },
        "active": {
            "accent": "#138c88", "border": "#bee4e1", "icon_bg": "#e4f6f3",
            "surface": "linear-gradient(135deg,#ffffff 0%,#f1faf8 100%)",
            "selected": "linear-gradient(135deg,#e9f8f6 0%,#f8fdfc 100%)",
            "shadow": "rgba(19,140,136,.15)",
        },
        "upcoming": {
            "accent": "#6655d9", "border": "#d7d0fa", "icon_bg": "#efedff",
            "surface": "linear-gradient(135deg,#ffffff 0%,#f7f5ff 100%)",
            "selected": "linear-gradient(135deg,#f0edff 0%,#fbfaff 100%)",
            "shadow": "rgba(102,85,217,.15)",
        },
        "attention": {
            "accent": "#e4474d", "border": "#ffc7ca", "icon_bg": "#ffe8e9",
            "surface": "linear-gradient(135deg,#ffffff 0%,#fff4f4 100%)",
            "selected": "linear-gradient(135deg,#fff0f1 0%,#fff8f8 100%)",
            "shadow": "rgba(228,71,77,.14)",
        },
    }
    for _, value, unit, focus, guide, _ in items:
        # Streamlit applies the widget key to the button's element container.
        # Target that generated class directly so each status keeps its own color.
        key_selector = (
            f'div[class*="st-key-application_status_button_{focus}"][class*="st-key-"] '
            '[data-testid="stButton"]'
        )
        style = category_styles[focus]
        css_rules.extend(
            [
                f'{key_selector} button::before {{ content:"{int(value or 0)}{unit}"; }}',
                f'{key_selector} button::after {{ content:"{guide}"; }}',
                f'{key_selector} button {{ border-color:{style["border"]} !important; '
                f'background:{style["surface"]} !important; }}',
                f'{key_selector} button span[data-testid="stIconMaterial"] '
                f'{{ background:{style["icon_bg"]}; color:{style["accent"]}; }}',
                f'{key_selector} button p {{ color:{style["accent"]} !important; '
                'font-size:15px !important; line-height:1.3 !important; '
                'font-weight:850 !important; letter-spacing:.01em; }}',
                f'{key_selector} button::before {{ color:{style["accent"]}; '
                f'background:{style["icon_bg"]}; }}',
                f'{key_selector} button:hover:not(:disabled) {{ border-color:{style["accent"]} !important; '
                f'box-shadow:0 8px 18px {style["shadow"]} !important; }}',
            ]
        )
        if selected_focus == focus:
            css_rules.append(
                f'{key_selector} button {{ border:2px solid {style["accent"]} !important; '
                f'background:{style["selected"]} !important; '
                f'box-shadow:0 7px 18px {style["shadow"]} !important; }}'
            )
    st.markdown(f'<style>{"".join(css_rules)}</style>', unsafe_allow_html=True)

    columns = st.columns(4, gap="small")
    for column, (label, value, _unit, focus, _guide, icon) in zip(columns, items):
        with column:
            with st.container(key=f"application_status_{focus}"):
                if st.button(
                    label,
                    key=f"application_status_button_{focus}",
                    icon=icon,
                    disabled=int(value or 0) <= 0,
                    use_container_width=True,
                ):
                    selected_focus = "" if selected_focus == focus else focus
                    st.session_state["application_overview_focus"] = selected_focus
                    _close_schedule_dialog_for_filter_change()
                    st.rerun()
    return selected_focus


def render_application_list_page(focus: str = "") -> None:
    render_job_navigation("application_list")
    _inject_css()
    sync_applications_from_decisions()
    requested_focus = str(st.query_params.get("focus", "") or focus).strip()
    if requested_focus == "milestones":
        st.session_state["application_task_focus"] = True
        st.query_params.pop("focus", None)
    # トップ画面・通知・旧応募詳細URLから来た場合も、独立ページへは遷移せず
    # この応募管理画面上で予定・結果登録モーダルを一度だけ開く。
    try:
        requested_application_id = int(st.query_params.get("application_id", "0") or 0)
    except (TypeError, ValueError):
        requested_application_id = 0
    if requested_application_id:
        st.session_state["schedule_dialog_application_id"] = requested_application_id
        st.query_params.pop("application_id", None)
        st.query_params.pop("milestone_id", None)
    st.markdown(
        '<header class="application-page-head"><h1>応募管理</h1>'
        '<p>応募企業の選考状況を管理し、次のアクションにつなげましょう。</p></header>',
        unsafe_allow_html=True,
    )
    all_views = load_application_views(True)
    summary = operational_summary(all_views)
    focus_id_map = {
        "preparation": summary["preparation_application_ids"],
        "active": summary["active_application_ids"],
        "upcoming": summary["upcoming_application_ids"],
        "attention": summary["attention_application_ids"],
    }
    focus_state_key = "application_overview_focus"
    if focus_state_key not in st.session_state:
        st.session_state[focus_state_key] = ""
    selected_focus = str(st.session_state[focus_state_key]).strip()
    if selected_focus not in focus_id_map:
        selected_focus = ""
        st.session_state[focus_state_key] = ""
    with st.container(key="application_overview"):
        st.markdown(
            '<div class="application-overview-heading">応募状況とお知らせ</div>',
            unsafe_allow_html=True,
        )
        selected_focus = _application_status_controls(summary, selected_focus)
        if selected_focus:
            _render_application_notifications(all_views, summary, selected_focus)

    notification_schedule_application_id = int(
        st.session_state.get("notification_schedule_application_id", 0) or 0
    )
    notification_schedule_kind = str(
        st.session_state.get("notification_schedule_kind", "") or ""
    )
    if notification_schedule_application_id:
        instruction = (
            "下記のスケジュールより、対象企業の「次の予定・期限」をクリックして、スケジュールの更新を行ってください。"
            if notification_schedule_kind == "attention"
            else "下記のスケジュールより、対象企業の「次の予定・期限」をクリックして、スケジュールを確認してください。"
        )
        with st.container(key="notification_schedule_filter_context"):
            context_col, clear_col = st.columns([5, 1])
            context_col.markdown(
                f'<div class="schedule-filter-context"><span>{escape(instruction)}</span></div>',
                unsafe_allow_html=True,
            )
            if clear_col.button(
                "絞り込みを解除",
                key="clear_notification_schedule_filter",
                use_container_width=True,
            ):
                st.session_state.pop("notification_schedule_application_id", None)
                st.session_state.pop("notification_schedule_kind", None)
                st.rerun()

    phase_filters = list(dict.fromkeys([*PHASE_CATEGORIES, *PHASE_OPTIONS]))
    routes = sorted({v["application"].actual_route or "未設定" for v in all_views})
    query = str(st.session_state.get("app_query", ""))
    phase_filter = str(st.session_state.get("app_phase", "すべて"))
    route_filter = str(st.session_state.get("app_route", "すべて"))
    response_filter = str(st.session_state.get("app_response_status", "すべて"))
    sort_order = str(st.session_state.get("app_sort_order", "対応が必要な順"))
    task_focus_active = bool(st.session_state.get("application_task_focus", False))
    ended_views = sorted(
        [view for view in all_views if _is_ended_application(view)],
        key=lambda view: view["job"].company_name,
    )

    views = []
    for view in all_views:
        app, job = view["application"], view["job"]
        if _is_ended_application(view):
            continue
        if notification_schedule_application_id:
            if app.id == notification_schedule_application_id:
                views.append(view)
            continue
        if task_focus_active and view.get("next_milestone") is None:
            continue
        if query and query.lower() not in job.company_name.lower(): continue
        if phase_filter != "すべて":
            if phase_filter in PHASE_CATEGORIES and app.phase_category != phase_filter: continue
            if phase_filter not in PHASE_CATEGORIES and app.current_phase != phase_filter: continue
        if route_filter != "すべて" and (app.actual_route or "未設定") != route_filter: continue
        response_status = _application_response_status(view)
        if response_filter != "すべて" and response_status != response_filter: continue
        views.append(view)
    views = _sort_application_views(views, sort_order)
    filters_active = bool(
        notification_schedule_application_id
        or task_focus_active
        or query
        or phase_filter != "すべて"
        or route_filter != "すべて"
        or response_filter != "すべて"
        or sort_order != "対応が必要な順"
    )
    with st.container(key="application_schedule_section"):
        if task_focus_active:
            with st.container(key="application_task_focus_context"):
                task_message, task_action = st.columns([5, 1])
                task_message.markdown(
                    f"**予定・タスクが登録されている応募企業を{len(views)}社表示中**  \n"
                    "各企業の「次の予定・期限」を確認し、完了・日程変更・結果登録が必要な場合は、"
                    "操作列の「予定・結果を更新」から対応してください。"
                )
                if task_action.button(
                    "絞り込みを解除",
                    key="clear_application_task_focus",
                    use_container_width=True,
                ):
                    st.session_state["application_task_focus"] = False
                    st.rerun()
        st.markdown(
            '<span id="application-company-list" class="application-anchor"></span>',
            unsafe_allow_html=True,
        )
        requested_wbs_view = str(st.query_params.get("wbs_view", "week"))
        initial_wbs_label = {
            "two_weeks": "2週間表示",
            "month": "1か月表示",
        }.get(requested_wbs_view, "週表示")
        with st.container(key="application_list_heading"):
            heading_col, switch_col = st.columns([1, 0.32])
            with heading_col:
                info_icon = (
                    '<svg viewBox="0 0 24 24" aria-hidden="true">'
                    '<circle cx="12" cy="12" r="9"/><path d="M12 10v6"/>'
                    '<path d="M12 7.25h.01"/>'
                    '</svg>'
                )
                schedule_icon = (
                    '<svg viewBox="0 0 24 24" aria-hidden="true">'
                    '<rect x="3.5" y="5.5" width="17" height="15" rx="2.5"/>'
                    '<path d="M7.5 3.5v4M16.5 3.5v4M3.5 10h17"/>'
                    '<path d="m8 15 2.1 2.1L16 12.5"/>'
                    '</svg>'
                )
                st.markdown(
                    '<div class="application-list-head"><div class="application-list-title-wrap">'
                    f'<span class="application-list-title-icon">{schedule_icon}</span>'
                    '<div class="application-list-title-copy">'
                    '<span class="application-list-eyebrow">選考管理</span>'
                    '<h2 class="application-list-title">選考スケジュール'
                    f'<span class="application-list-count">{len(views)}社</span>'
                    f'<span class="application-list-info">{info_icon}</span></h2>'
                    '<p class="application-list-caption">予定と選考の進み具合を、企業ごとに確認できます。</p>'
                    '</div></div></div>', unsafe_allow_html=True,
                )
            with switch_col:
                selected_wbs_label = st.radio(
                    "WBS表示期間", ["週表示", "2週間表示", "1か月表示"],
                    index=["週表示", "2週間表示", "1か月表示"].index(initial_wbs_label),
                    horizontal=True, label_visibility="collapsed", key="wbs_view_control",
                    on_change=_close_schedule_dialog_for_filter_change,
                )
        wbs_view = {
            "2週間表示": "two_weeks",
            "1か月表示": "month",
        }.get(selected_wbs_label, "week")
        if st.session_state.get("application_schedule_last_view") != wbs_view:
            st.session_state["application_schedule_last_view"] = wbs_view
            st.session_state["application_schedule_period_offset"] = 0
        _render_application_list_header_filters(phase_filters, routes, filters_active)
        if not views:
            st.markdown(
                '<div class="schedule-empty-state" role="status">'
                '<div class="schedule-empty-state-icon" aria-hidden="true">i</div>'
                '<div><strong>条件に一致する応募企業はありません</strong>'
                '<span>表示条件を変更するか、求人確認画面で応募判断を保存してください。</span></div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            _render_application_table(views, wbs_view)
        _render_ended_applications(ended_views)

def _oldest_overdue_milestone_date(views: list[dict], today: date) -> date | None:
    """Return the oldest overdue date among the applications currently displayed."""
    overdue_dates: list[date] = []
    for view in views:
        for milestone in view["milestones"]:
            if not milestone.scheduled_date or not is_milestone_overdue(milestone, today):
                continue
            try:
                overdue_dates.append(date.fromisoformat(milestone.scheduled_date))
            except ValueError:
                continue
    return min(overdue_dates, default=None)


def _wbs_period(
    view_mode: str,
    today: date,
    offset: int = 0,
    oldest_overdue_date: date | None = None,
) -> list[date]:
    if view_mode == "month":
        day_count = calendar.monthrange(today.year, today.month)[1]
    else:
        day_count = 14 if view_mode == "two_weeks" else 7
    default_start = today - timedelta(days=1)

    # 「今日」の期間では期限超過を見落とさないよう、最も古い期限超過日まで
    # 左端を自動で広げる。未来側は従来の表示範囲を維持する。
    if offset == 0 and oldest_overdue_date and oldest_overdue_date < default_start:
        period_start = oldest_overdue_date
        period_end = default_start + timedelta(days=day_count - 1)
        visible_day_count = (period_end - period_start).days + 1
    else:
        period_start = default_start + timedelta(days=offset * day_count)
        visible_day_count = day_count

    return [period_start + timedelta(days=day_offset) for day_offset in range(visible_day_count)]


def _application_response_status(view: dict) -> str:
    today = date.today()
    milestones = view["milestones"]
    if any(is_milestone_overdue(milestone, today) for milestone in milestones):
        return "対応が必要"
    if any(is_milestone_upcoming(milestone, today) for milestone in milestones):
        return "近日予定"
    return "通常"


def _next_date_sort_value(view: dict) -> str:
    next_milestone = view["next_milestone"]
    return next_milestone.scheduled_date if next_milestone and next_milestone.scheduled_date else "9999-12-31"


def _sort_application_views(views: list[dict], sort_order: str) -> list[dict]:
    if sort_order == "次回予定が近い順":
        key = lambda view: (_next_date_sort_value(view), view["job"].company_name)
        return sorted(views, key=key)
    if sort_order == "最終更新が新しい順":
        return sorted(views, key=lambda view: view["application"].updated_at or "", reverse=True)
    if sort_order == "最終更新が古い順":
        return sorted(views, key=lambda view: view["application"].updated_at or "")
    if sort_order == "会社名順":
        return sorted(views, key=lambda view: view["job"].company_name)
    if sort_order == "応募日が新しい順":
        return sorted(
            views,
            key=lambda view: (
                view["application"].application_date or "",
                view["application"].created_at or "",
            ),
            reverse=True,
        )
    if sort_order == "現在フェーズ順":
        return sorted(views, key=lambda view: (view["application"].current_phase, view["job"].company_name))
    priority = {"対応が必要": 0, "近日予定": 1, "通常": 2}
    return sorted(
        views,
        key=lambda view: (
            priority[_application_response_status(view)],
            _next_date_sort_value(view),
            view["job"].company_name,
        ),
    )


@st.fragment
def _render_application_table(views: list[dict], view_mode: str) -> None:
    with st.container(key="schedule_modal_triggers"):
        for view in views:
            application_id = int(view["application"].id)
            if st.button(
                f"予定登録::{application_id}",
                key=f"schedule_modal_trigger_{application_id}",
            ):
                # モーダル内の完了・登録操作で再描画されても、明示的に閉じるまでは
                # 同じ応募詳細を開いた状態に保つ。
                st.session_state["schedule_dialog_application_id"] = application_id

    today = date.today()
    oldest_overdue_date = _oldest_overdue_milestone_date(views, today)
    offset_key = "application_schedule_period_offset"
    offset = int(st.session_state.get(offset_key, 0) or 0)
    with st.container(key="application_schedule_period_control"):
        label_col, hint_col, previous_col, today_col, next_col = st.columns([3.3, 2.2, 0.55, 0.7, 0.55])
        if previous_col.button("←", key=f"schedule_previous_{view_mode}", help="前の期間へ"):
            offset -= 1
            st.session_state[offset_key] = offset
        if today_col.button("今日", key=f"schedule_today_{view_mode}", help="現在の期間へ戻る"):
            offset = 0
            st.session_state[offset_key] = 0
        if next_col.button("→", key=f"schedule_next_{view_mode}", help="次の期間へ"):
            offset += 1
            st.session_state[offset_key] = offset
        period = _wbs_period(view_mode, today, offset, oldest_overdue_date)
        label_col.markdown(
            f'<div class="schedule-period-label">{period[0].year}年{period[0].month}月{period[0].day}日'
            f'〜{period[-1].year}年{period[-1].month}月{period[-1].day}日</div>',
            unsafe_allow_html=True,
        )
        hint_col.markdown(
            '<div class="schedule-scroll-hint">横にスクロールして期間全体を確認できます</div>',
            unsafe_allow_html=True,
        )
    weekdays = "月火水木金土日"
    date_headers = "".join(
        '<th class="wbs-day '
        f'{"weekend" if day.weekday() >= 5 else ""} '
        f'{"today-column" if day == today else ""}">'
        '<span class="wbs-date-head '
        f'{"today" if day == today else ""}">{day.month}/{day.day} {weekdays[day.weekday()]}</span></th>'
        for day in period
    )
    rows = []
    for view in views:
        app, job = view["application"], view["job"]
        response_status = _application_response_status(view)
        response_class = {
            "対応が必要": "attention",
            "近日予定": "upcoming",
        }.get(response_status, "normal")
        next_m = view["next_milestone"]
        next_text = escape(_milestone_title(next_m)) if next_m else "次の予定を登録"

        events_by_date: dict[date, list[dict[str, str]]] = {}
        rendered_events: set[tuple[date, str, str]] = set()
        for milestone in view["milestones"]:
            if not milestone.scheduled_date:
                continue
            try:
                scheduled = date.fromisoformat(milestone.scheduled_date)
            except ValueError:
                continue
            if milestone.status in {"postponed", "cancelled"}:
                css_class = "inactive"
            elif is_milestone_overdue(milestone, today):
                css_class = "overdue"
            else:
                css_class = ""
            visual_category = _milestone_visual_category(milestone)
            title = escape(_milestone_title(milestone))
            if milestone.status == "completed" and milestone.completed_at:
                try:
                    completed_date = datetime.fromisoformat(milestone.completed_at).date()
                except ValueError:
                    completed_date = scheduled
                event_key = (completed_date, title, "completed")
                if event_key not in rendered_events:
                    events_by_date.setdefault(completed_date, []).append({
                        "title": title, "category": visual_category, "state": "done", "label": "実績",
                    })
                    rendered_events.add(event_key)
            else:
                event_key = (scheduled, title, milestone.status)
                if event_key not in rendered_events:
                    events_by_date.setdefault(scheduled, []).append({
                        "title": title, "category": visual_category, "state": css_class, "label": "予定",
                    })
                    rendered_events.add(event_key)

        timeline_cells = []
        for day in period:
            day_events = events_by_date.get(day, [])
            rendered = []
            for event in day_events[:3]:
                state_class = event["state"]
                if not state_class and 0 <= (day - today).days <= 2:
                    state_class = "urgent"
                event_class = f'{event["category"]} {state_class}'.strip()
                accessible = escape(f'{day.month}/{day.day} {event["title"]}（{event["label"]}）')
                if event["state"] == "done":
                    marker = (
                        f'<img class="timeline-state-icon" src="{TIMELINE_COMPLETE_ICON}" '
                        'alt="完了">'
                    )
                elif event["state"] == "overdue":
                    marker = (
                        f'<img class="timeline-state-icon" src="{TIMELINE_WARNING_ICON}" '
                        'alt="期限超過・要対応">'
                    )
                else:
                    marker = f'<span class="timeline-dot {event["category"]}" aria-hidden="true"></span>'
                rendered.append(
                    f'<span class="wbs-event {event_class}" title="{accessible}">'
                    f'{marker}<span class="timeline-event-label">{event["title"]}</span></span>'
                )
            if len(day_events) > 3:
                rendered.append(f'<span class="wbs-more">ほか{len(day_events) - 3}件</span>')
            events_html = "".join(rendered)
            cell_content = events_html or '<span class="wbs-empty-day"></span>'
            timeline_cells.append(
                f'<td class="wbs-day {"weekend" if day.weekday() >= 5 else ""} '
                f'{"today-column" if day == today else ""}">'
                f'<div class="wbs-events">{cell_content}</div></td>'
            )

        rows.append(
            '<tr>'
            '<td class="company-cell"><div class="schedule-company-actions">'
            f'<a class="table-company" title="{escape(job.company_name)}" '
            f'href="?page=job_detail&amp;job_id={app.job_id}">{escape(job.company_name)}</a></div></td>'
            f'<td class="next-cell"><span class="table-next">{next_text}</span></td>'
            f'<td class="route-cell">{escape(app.actual_route or "未設定")}</td>'
            f'<td class="phase-cell"><span class="table-phase">{escape(app.current_phase)}</span></td>'
            f'<td class="status-cell"><span class="table-status {response_class}">'
            f'{escape("対応不要" if response_status == "通常" else response_status)}</span></td>'
            '<td class="prep-cell"><div class="schedule-row-actions">'
            f'<button type="button" class="schedule-row-action primary" '
            f'data-schedule-application="{app.id}" '
            f'aria-label="{escape(job.company_name)}の予定と選考結果を更新">予定・結果を更新</button>'
            f'<a class="schedule-row-action" target="_self" '
            f'href="?page=selection_preparation&amp;application_id={app.id}">選考準備</a>'
            '</div></td>'
            f'{"".join(timeline_cells)}'
            '</tr>'
        )

    st.html(
        '<div class="application-table-wrap" role="region" aria-label="選考スケジュール">'
        '<div class="schedule-list-topline"><div class="wbs-legend">'
        '<span><i class="legend-dot personal"></i>自分の準備</span>'
        '<span><i class="legend-dot agent"></i>エージェント連絡</span>'
        '<span><i class="legend-dot company"></i>企業・選考</span>'
        f'<span><img class="legend-state-icon" src="{TIMELINE_COMPLETE_ICON}" alt="">完了（実績）</span>'
        f'<span><img class="legend-state-icon" src="{TIMELINE_WARNING_ICON}" alt="">期限超過・要対応</span>'
        '</div></div>'
        f'<table class="application-table {view_mode}" style="--timeline-total-width:{len(period) * (128 if view_mode == "week" else 64 if view_mode == "two_weeks" else 32)}px">'
        '<colgroup>'
        '<col class="company-col"><col class="next-col"><col class="route-col">'
        '<col class="phase-col"><col class="status-col"><col class="prep-col">'
        f'<col class="timeline-col" span="{len(period)}">'
        '</colgroup><thead>'
        '<tr class="schedule-group-head"><th class="management-group" colspan="6">操作・管理</th>'
        f'<th class="timeline-group" colspan="{len(period)}">確認用タイムライン</th></tr>'
        '<tr class="schedule-column-head"><th class="company-cell">会社名</th>'
        '<th class="next-cell">次の予定・期限</th><th class="route-cell">応募経路</th>'
        '<th class="phase-cell">現在フェーズ</th><th class="status-cell">対応状態</th>'
        f'<th class="prep-cell">操作</th>{date_headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '</div>'
        '<script>'
        'document.querySelectorAll("[data-schedule-application]").forEach(function(cell){'
        'cell.addEventListener("click", function(){'
        'const label="予定登録::"+cell.dataset.scheduleApplication;'
        'const trigger=Array.from(document.querySelectorAll("button")).find(function(button){'
        'return button.textContent.trim()===label;});'
        'if(trigger){trigger.click();}'
        '});'
        'cell.addEventListener("keydown", function(event){'
        'if(event.key==="Enter"||event.key===" "){event.preventDefault();cell.click();}'
        '});'
        '});'
        '</script>',
        unsafe_allow_javascript=True,
    )
    # 起動要求は一度だけ消費する。IDを保持したままにすると、絞り込みや
    # 表示切替など無関係な再描画でも応募詳細が勝手に再表示される。
    selected_application_id = int(
        st.session_state.pop("schedule_dialog_application_id", 0) or 0
    )
    if selected_application_id:
        _render_application_detail_dialog(selected_application_id)


def _render_application_card(view: dict) -> None:
    app, job = view["application"], view["job"]
    next_m = view["next_milestone"]
    meta_next = "未登録"
    if next_m:
        meta_next = f'{next_m.scheduled_date or "日付未定"} {next_m.title or next_m.milestone_type}'
    steps = []
    today = date.today()
    for milestone in view["milestones"][:6]:
        if milestone.status == "completed":
            css_class = "done"
        elif milestone.status in {"postponed", "cancelled"}:
            css_class = "inactive"
        elif is_milestone_overdue(milestone, today):
            css_class = "overdue"
        elif is_milestone_upcoming(milestone, today):
            css_class = "upcoming"
        else:
            css_class = ""
        label = milestone.title or milestone.detail_name or milestone.milestone_type
        status = milestone_status_label(milestone.status)
        steps.append(
            f'<div class="wbs-step {css_class}">{escape(label)}<br>'
            f'{escape(milestone.scheduled_date or "未定")} · {escape(status)}</div>'
        )
    if not steps:
        steps = ['<div class="wbs-step">予定を登録</div>']
    st.markdown(
        f'''<article class="application-card"><div class="app-head"><div>
        <a class="company" href="?page=job_detail&job_id={app.job_id}">{escape(job.company_name)}</a>
        <div class="job-title">{escape(job.job_title or "求人名未登録")}</div></div>
        <a class="badge" href="?page=application_detail&application_id={app.id}">応募詳細を開く →</a></div>
        <div class="app-meta"><div class="meta-box"><div class="meta-label">現在フェーズ</div><div class="meta-value">{escape(app.current_phase)}</div></div>
        <div class="meta-box"><div class="meta-label">応募経路</div><div class="meta-value">{escape(app.actual_route or "未設定")}</div></div>
        <div class="meta-box"><div class="meta-label">次の予定・期限</div><div class="meta-value">{escape(meta_next)}</div></div></div>
        <div class="wbs">{''.join(steps)}</div></article>''', unsafe_allow_html=True,
    )


ANALYTICS_COLORS = ("#1F6FEB", "#1CB7C9", "#F59A00", "#E7B416", "#7651E6", "#EF6B7B", "#19A66A", "#AAB5C4")
ANALYTICS_PHASE_COLORS = {
    "応募準備": "#1F6FEB", "応募": "#1CB7C9", "書類選考": "#F59A00",
    "適性検査": "#E7B416", "面接": "#7651E6", "オファー・条件確認": "#EF6B7B",
    "内定": "#19A66A", "保留": "#D783B5", "終了": "#AAB5C4",
}


def _analytics_icon(kind: str) -> str:
    paths = {
        "total": '<circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M3 20v-2a5 5 0 0 1 10 0v2M13 20v-2a5 5 0 0 1 8-4"/>',
        "applied": '<path d="m4 12 16-8-6 16-3-6-7-2Z"/><path d="m11 14 4-5"/>',
        "interview": '<circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2.5 20a5.5 5.5 0 0 1 11 0M13 20a4 4 0 0 1 8 0"/>',
        "offer": '<path d="M8 4h8v4a4 4 0 0 1-8 0V4Z"/><path d="M8 6H5v1a4 4 0 0 0 4 4M16 6h3v1a4 4 0 0 1-4 4M12 12v5M8 20h8M10 17h4"/>',
    }
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{paths[kind]}</svg>'


def _analytics_donut(title: str, counts, total: int) -> str:
    rows = list(counts.most_common())
    if not rows:
        return '<div class="analytics-chart-card"><div class="analytics-card-title"><i></i>' + escape(title) + '</div><div class="notification-empty">集計対象の応募はありません。</div></div>'
    circumference = 364.42
    cursor = 0.0
    segments, legend = [], []
    for index, (name, count) in enumerate(rows):
        color = ANALYTICS_PHASE_COLORS.get(str(name), ANALYTICS_COLORS[index % len(ANALYTICS_COLORS)])
        percent = count / total * 100 if total else 0
        length = circumference * percent / 100
        visible_length = max(0, length - 2.4)
        segments.append(
            f'<circle class="analytics-donut-segment" cx="90" cy="90" r="58" stroke="{color}" '
            f'stroke-dasharray="{visible_length:.2f} {circumference - visible_length:.2f}" '
            f'stroke-dashoffset="{-cursor:.2f}" transform="rotate(-90 90 90)">'
            f'<title>{escape(str(name))} {count}社・{round(percent)}%</title></circle>'
        )
        cursor += length
        legend.append(
            f'<div class="analytics-legend-row"><i style="background:{color}"></i>'
            f'<b title="{escape(str(name))}">{escape(str(name))}</b><span>{count}社</span>'
            f'<em>{round(percent)}%</em></div>'
        )
    return (
        '<div class="analytics-chart-card"><div class="analytics-card-title"><i></i>' + escape(title) + '</div>'
        '<div class="analytics-donut-layout"><div class="analytics-donut">'
        '<svg viewBox="0 0 180 180" aria-label="現在フェーズの構成"><circle class="analytics-donut-track" cx="90" cy="90" r="58"/>'
        f'{"".join(segments)}</svg><div class="analytics-donut-center">全体<strong>{total}<small>社</small></strong></div></div>'
        f'<div class="analytics-legend">{"".join(legend)}</div></div></div>'
    )


def _analytics_detail_color(name: str, index: int) -> str:
    if "不合格" in name or "辞退" in name:
        return "#EF6B7B"
    for phase_name, color in ANALYTICS_PHASE_COLORS.items():
        if phase_name in name or (phase_name == "面接" and "面談" in name):
            return color
    return ANALYTICS_COLORS[index % len(ANALYTICS_COLORS)]


def _analytics_detail_panel(counts, total: int) -> str:
    rows = []
    for index, (name, count) in enumerate(counts.most_common()):
        color = _analytics_detail_color(str(name), index)
        percent = round(count / total * 100) if total else 0
        rows.append(
            f'<div class="analytics-detail-row"><i style="background:{color}"></i>'
            f'<b title="{escape(str(name))}">{escape(str(name))}</b>'
            f'<span>{count}<small>社・{percent}%</small></span></div>'
        )
    body = ''.join(rows) if rows else '<div class="notification-empty">集計対象の応募はありません。</div>'
    return (
        '<div class="analytics-chart-card analytics-detail-card"><div class="analytics-card-title"><i></i>詳細フェーズ内訳</div>'
        '<p class="analytics-chart-note">右側は、左の大分類を「現在どの予定・結果の状態か」まで細かくした内訳です。</p>'
        f'<div class="analytics-detail-list">{body}</div></div>'
    )


def _analytics_rate(value) -> str:
    return "―" if value is None else f"{value}%"


REPORT_COLORS = {
    "書類選考": "#1f6feb", "適性検査": "#18a979", "一次面接": "#f59a00",
    "二次面接": "#7651e6", "最終面接": "#ef5f78", "内定": "#19a66a",
}


def _report_bars(rows: dict, stage: str, color: str, limit: int = 4) -> str:
    ordered = sorted(
        ((name, values[stage]) for name, values in rows.items() if values[stage]["reached"]),
        key=lambda item: (item[1]["rate"] or -1, item[1]["reached"]), reverse=True,
    )[:limit]
    if not ordered:
        return '<div class="notification-empty">集計対象のデータはありません。</div>'
    return ''.join(
        f'<div class="report-bar" style="--c:{color}"><span title="{escape(name)}">{escape(name)}</span>'
        f'<div class="report-track"><div class="report-fill" style="width:{row["rate"] or 0}%"></div></div>'
        f'<b>{row["rate"]}%</b><small>{row["passed"]} / {row["reached"]}'
        f'{" 参考" if row["is_reference"] else ""}</small></div>'
        for name, row in ordered
    )


def _report_ranking_card(title: str, rows: dict, stage: str, color: str, winner_label: str) -> str:
    valid = sorted(
        ((name, values[stage]) for name, values in rows.items() if values[stage]["reached"]),
        key=lambda item: (item[1]["rate"] or -1, item[1]["reached"]), reverse=True,
    )
    winner = valid[0] if valid else ("データなし", {"rate": 0})
    return (
        f'<section class="report-rank-card" style="--c:{color}"><h3>{escape(title)}　{escape(stage)}通過率</h3>'
        f'<div class="report-winner">{escape(winner_label)}　 {escape(winner[0])} {winner[1]["rate"] or 0}%</div>'
        f'<div class="report-bars">{_report_bars(rows, stage, color, 3)}</div></section>'
    )


def _report_heatmap(rows: dict, stages: tuple[str, ...], axis_name: str) -> str:
    ordered = sorted(rows.items(), key=lambda item: item[1][stages[0]]["reached"], reverse=True)[:6]
    header = ''.join(f'<th>{escape(stage.replace("選考", ""))}</th>' for stage in stages)
    body = []
    for name, values in ordered:
        cells = []
        for stage in stages:
            row = values[stage]
            if not row["reached"]:
                cells.append('<td class="report-cell">―<small>対象なし</small></td>')
                continue
            rate = row["rate"] or 0
            color = REPORT_COLORS[stage]
            cells.append(
                f'<td class="report-cell" style="background:{color}12;color:{color}"><b>{rate}%</b>'
                f'<small>{row["passed"]} / {row["reached"]}</small>'
                f'{"<i class=\"report-ref\">参考値</i>" if row["is_reference"] else ""}</td>'
            )
        body.append(f'<tr><td>{escape(name)}</td>{"".join(cells)}</tr>')
    return (
        f'<div class="report-axis-title"><h2>{escape(axis_name)} × 選考フェーズ</h2></div>'
        f'<div class="report-table-wrap"><table class="report-table"><thead><tr><th>{escape(axis_name)}</th>{header}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
    )


def render_application_dashboard_page() -> None:
    render_job_navigation("application_dashboard")
    _inject_css()
    sync_applications_from_decisions()
    today = date.today()
    period_enabled = bool(st.session_state.get("report_period_enabled", False))
    selected_period = st.session_state.get("report_period_range", (today - timedelta(days=30), today))
    if period_enabled and isinstance(selected_period, (tuple, list)) and len(selected_period) == 2:
        period_label = f'{selected_period[0].strftime("%Y/%m/%d")} 〜 {selected_period[1].strftime("%Y/%m/%d")}'
    else:
        period_label = "全期間"

    header_left, header_right = st.columns([0.78, 0.22], vertical_alignment="bottom")
    with header_left:
        st.markdown(
            '<header class="report-head"><div><h1>選考通過率レポート</h1>'
            '<p>選考全体の通過状況と各フェーズの通過率を確認できます。</p></div></header>',
            unsafe_allow_html=True,
        )
    with header_right:
        st.markdown('<div class="report-period-label">集計期間</div>', unsafe_allow_html=True)
        with st.popover(
            period_label,
            icon=":material/calendar_month:",
            use_container_width=True,
            key="report_period_popover",
        ):
            period_enabled = st.checkbox("期間を指定する", key="report_period_enabled")
            if period_enabled:
                selected_period = st.date_input(
                    "応募日の範囲",
                    value=selected_period,
                    max_value=today,
                    format="YYYY/MM/DD",
                    key="report_period_range",
                )
                st.caption("応募日が未登録の場合は、応募管理への登録日を使用します。")

    start_date = end_date = None
    if period_enabled and isinstance(selected_period, (tuple, list)) and len(selected_period) == 2:
        start_date, end_date = selected_period
    data = selection_pass_report(start_date=start_date, end_date=end_date)
    summary = data["summary"]
    overall_tab, analysis_tab = st.tabs(["1　全体サマリー", "2　経路・業種・職種別分析"])
    with overall_tab:
        items = [("応募企業", "total"), ("応募", "applied"), ("選考中", "active"),
                 ("面接進出", "interview"), ("内定", "offers"), ("選考終了", "closed")]
        strip = ''.join(f'<div class="report-summary-item"><div><span>{label}</span><strong>{summary[key]}<small>社</small></strong></div></div>' for label, key in items)
        flow = (
            f'<div class="report-flow-step" style="--c:#4b8df8">応募'
            f'<strong>{summary["applied"]}<small>社</small></strong></div>'
        ) + ''.join(
            f'<div class="report-flow-connector"><span>'
            f'{data["overall"][stage]["rate"] if data["overall"][stage]["rate"] is not None else "―"}%'
            f'</span><i>→</i></div>'
            f'<div class="report-flow-step" style="--c:{REPORT_COLORS[stage]}">'
            f'{"内定" if stage == "内定" else stage.replace("選考", "") + "通過"}'
            f'<strong>{data["overall"][stage]["passed"]}<small>社</small></strong></div>'
            for stage in data["stages"]
        )
        stage_bars = ''.join(
            f'<div class="report-bar" style="--c:{REPORT_COLORS[stage]}"><span>{stage}</span><div class="report-track">'
            f'<div class="report-fill" style="width:{data["overall"][stage]["rate"] or 0}%"></div></div>'
            f'<b>{data["overall"][stage]["rate"] if data["overall"][stage]["rate"] is not None else "―"}%</b>'
            f'<small>{data["overall"][stage]["passed"]} / {data["overall"][stage]["reached"]}'
            f'　結果待ち {data["overall"][stage]["pending"]}</small></div>'
            for stage in data["stages"][:-1]
        )
        candidates = [(s, data["overall"][s]) for s in data["stages"][:-1] if data["overall"][s]["reached"]]
        focus_stage, focus = min(candidates, key=lambda x: x[1]["rate"]) if candidates else ("未設定", {"rate": None, "passed": 0, "reached": 0, "pending": 0})
        st.markdown(
            f'<div class="report-summary">{strip}</div><section class="report-card"><h2>選考全体の流れ</h2><div class="report-flow">{flow}</div></section>'
            f'<div class="report-bottom"><section class="report-card"><h2>フェーズ別通過率</h2><div class="report-bars">{stage_bars}</div></section>'
            f'<section class="report-card"><h2>通過率を確認したいフェーズ</h2><p class="report-card-desc">選考結果を確認したいフェーズの状況です。結果待ちがある場合は、結果確定後に通過率へ反映されます。</p><div class="report-insight"><div class="accent">{focus_stage}<strong>{focus["rate"] if focus["rate"] is not None else "―"}%</strong></div>'
            f'<div>通過<strong>{focus["passed"]}件</strong><small>対象 {focus["reached"]}件</small></div><div>結果待ち<strong>{focus["pending"]}件</strong></div></div></section></div>',
            unsafe_allow_html=True,
        )
    with analysis_tab:
        phase_tabs = st.tabs(list(data["stages"]))
        for stage, phase_tab in zip(data["stages"], phase_tabs):
            with phase_tab:
                if stage == "適性検査":
                    st.markdown(
                        '<div class="report-rank-grid" style="grid-template-columns:repeat(2,minmax(0,1fr))">'
                        f'{_report_ranking_card("業種別", data["industries"], stage, "#f28a16", "最も高い業種")}'
                        f'{_report_ranking_card("職種別", data["occupations"], stage, "#7651e6", "最も高い職種")}</div>',
                        unsafe_allow_html=True,
                    )
                    industry_axis, occupation_axis = st.tabs(["業種", "職種"])
                    with industry_axis: st.markdown(_report_heatmap(data["industries"], data["stages"], "業種"), unsafe_allow_html=True)
                    with occupation_axis: st.markdown(_report_heatmap(data["occupations"], data["stages"], "職種"), unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="report-rank-grid">'
                        f'{_report_ranking_card("応募経路別", data["routes"], stage, "#159b69", "最も高い経路")}'
                        f'{_report_ranking_card("業種別", data["industries"], stage, "#f28a16", "最も高い業種")}'
                        f'{_report_ranking_card("職種別", data["occupations"], stage, "#7651e6", "最も高い職種")}</div>',
                        unsafe_allow_html=True,
                    )
                    route_axis, industry_axis, occupation_axis = st.tabs(["応募経路", "業種", "職種"])
                    with route_axis: st.markdown(_report_heatmap(data["routes"], data["stages"], "応募経路"), unsafe_allow_html=True)
                    with industry_axis: st.markdown(_report_heatmap(data["industries"], data["stages"], "業種"), unsafe_allow_html=True)
                    with occupation_axis: st.markdown(_report_heatmap(data["occupations"], data["stages"], "職種"), unsafe_allow_html=True)


def _analytics_route_section(routes: dict) -> None:
    if not routes:
        st.markdown('<section class="analytics-section"><div class="analytics-section-head"><span class="analytics-index">4</span>応募経路別実績</div><div class="notification-empty">応募経路別に集計できるデータはありません。</div></section>', unsafe_allow_html=True)
        return
    ordered = sorted(routes.items(), key=lambda item: item[1]["applications"], reverse=True)
    table_rows, bars = [], []
    for route, row in ordered:
        rate = round(row["document_pass"] / row["applications"] * 100) if row["applications"] else None
        rate_text = "―" if rate is None else f"{rate}%"
        table_rows.append(
            f'<tr><td><b>{escape(route)}</b></td><td>{row["applications"]}</td><td>{row["document_known"]}</td>'
            f'<td>{row["document_pass"]}</td><td>{row["interview"]}</td><td>{row["offers"]}</td>'
            f'<td class="metric-cell">{rate_text}</td></tr>'
        )
        bars.append(
            f'<div class="analytics-route-bar"><label title="{escape(route)}">{escape(route)}</label>'
            f'<div class="analytics-route-track"><div class="analytics-route-fill" style="width:{0 if rate is None else rate}%"></div></div>'
            f'<b>{rate_text}</b></div>'
        )
    st.markdown(
        '<section class="analytics-section"><div class="analytics-section-head"><span class="analytics-index">4</span>応募経路別実績</div>'
        '<div class="analytics-route-grid"><div class="analytics-table-wrap"><table class="analytics-table"><thead>'
        '<tr class="analytics-group-head"><th rowspan="2">応募経路</th><th colspan="1">全体</th>'
        '<th colspan="4">選考の内訳・到達状況</th><th rowspan="2">成果指標</th></tr>'
        '<tr><th>応募数</th><th>結果判明</th><th>書類通過</th><th>面接進出</th><th>内定</th></tr>'
        f'</thead><tbody>{"".join(table_rows)}</tbody></table></div>'
        '<div class="analytics-route-bars"><div class="analytics-card-title"><i></i>書類通過率（応募数ベース）</div>'
        f'{"".join(bars)}</div></div></section>',
        unsafe_allow_html=True,
    )


def _bar_panel(counts, total: int) -> None:
    if not counts:
        st.info("集計対象の応募はありません。")
        return
    html = '<div class="panel">'
    for name, count in counts.most_common():
        percent = round(count / total * 100) if total else 0
        color = PHASE_COLORS.get(name, BLUE)
        html += f'<div class="bar-row"><strong>{escape(str(name))}</strong><div class="bar-track"><div class="bar-fill" style="width:{percent}%;background:{color}"></div></div><span>{count}社</span></div>'
    st.markdown(html + '</div>', unsafe_allow_html=True)


def _rate_cards(data: dict) -> None:
    labels = [("書類通過率", data["document_pass_rate"]), ("面接進出率", data["interview_rate"]), ("内定率（応募ベース）", data["offer_rate"])]
    html = '<div class="summary-grid" style="grid-template-columns:repeat(3,1fr)">'
    for label, rate in labels:
        value = "算出不可" if rate is None else f"{rate}%"
        html += f'<div class="summary-card"><div class="label">{escape(label)}</div><div class="value">{value}</div></div>'
    st.markdown(html + '</div>', unsafe_allow_html=True)


def _route_table(routes: dict) -> None:
    if not routes:
        st.info("応募経路別に集計できるデータはありません。")
        return
    html = '<div class="panel"><table class="route-table"><thead><tr><th>応募経路</th><th>応募数</th><th>書類通過</th><th>面接進出</th><th>内定</th><th>書類通過率</th></tr></thead><tbody>'
    for route, row in sorted(routes.items(), key=lambda item: item[1]["applications"], reverse=True):
        rate = round(row["document_pass"] / row["document_known"] * 100) if row["document_known"] else None
        html += f'<tr><td>{escape(route)}</td><td>{row["applications"]}</td><td>{row["document_pass"]}</td><td>{row["interview"]}</td><td>{row["offers"]}</td><td>{"―" if rate is None else str(rate)+"%"}</td></tr>'
    st.markdown(html + '</tbody></table></div>', unsafe_allow_html=True)


# UIイメージに合わせた応募詳細。通常ページと応募管理上のモーダルで同じ内容を利用する。
def _rerun_application_detail(*, embedded: bool) -> None:
    """モーダル内の更新はモーダルだけ、通常ページでは画面全体を再描画する。"""

    if embedded:
        st.rerun(scope="fragment")
    st.rerun()


def render_application_detail_page(
    application_id_override: int | None = None,
    *,
    embedded: bool = False,
) -> None:
    if not embedded:
        render_job_navigation("application_list")
    _inject_css()
    application_id = (
        int(application_id_override)
        if application_id_override is not None
        else int(st.query_params.get("application_id", "0") or 0)
    )
    # 旧URLや既存リンクから開かれた場合も独立ページは表示せず、
    # 応募管理画面上の予定・結果登録モーダルへ引き継ぐ。
    if not embedded:
        st.session_state["schedule_dialog_application_id"] = application_id
        st.query_params.clear()
        st.query_params["page"] = "application_list"
        st.rerun()
    detail = load_application_detail(application_id)
    if not detail:
        st.error("応募情報が見つかりません。")
        return
    app, job = detail["application"], detail["job"]
    phase_confirmation_key = f"show_phase_confirmation_{app.id}"
    pending = [m for m in detail["milestones"] if m.status == "pending"]
    overdue = [m for m in pending if is_milestone_overdue(m, date.today())]
    if not embedded:
        st.markdown('<div class="application-page-head"><h1>応募詳細</h1></div>', unsafe_allow_html=True)
    top_left, top_right = st.columns([1, 1])
    with top_right:
        _, edit_col = st.columns([.65, 1.55])
        with edit_col.popover("応募経路・応募日を変更", use_container_width=True):
            st.markdown("#### 応募経路・応募日を変更")
            st.caption(
                "応募経路・応募日・管理メモを変更できます。\n\n"
                "選考状況は下の「次の状態を登録」から更新してください。"
            )
            try:
                current_application_date = (
                    date.fromisoformat(app.application_date) if app.application_date else None
                )
            except ValueError:
                current_application_date = None
            with st.form(f"application_entry_edit_{app.id}"):
                edited_route = st.text_input("応募経路", value=app.actual_route)
                edited_date = st.date_input(
                    "応募日", value=current_application_date, format="YYYY/MM/DD"
                )
                edited_notes = st.text_area(
                    "管理メモ", value=app.notes, height=120,
                    placeholder="応募手続きやエージェントとの確認事項を記録します。",
                )
                if st.form_submit_button("変更を保存", type="primary", use_container_width=True):
                    if not edited_route.strip():
                        st.error("応募経路を入力してください。")
                    else:
                        app.actual_route = edited_route.strip()
                        app.application_date = edited_date.isoformat() if edited_date else None
                        app.notes = edited_notes.strip()
                        try:
                            update_application_data(app)
                        except Exception:
                            render_save_failure(
                                "応募経路・応募日・管理メモ",
                                recovery="入力内容は画面に残っています。時間をおいて、もう一度「変更を保存」を押してください。",
                            )
                        else:
                            st.toast("応募経路・応募日・管理メモを更新しました。")
                            _rerun_application_detail(embedded=embedded)
    st.markdown(f'''<section class="detail-hero">
      <div><div class="company-row"><div><div class="detail-company">{escape(job.company_name)}</div>
      <div class="detail-role">{escape(job.job_title or "求人名未登録")}</div></div></div></div>
      <div><div class="detail-label">応募経路</div><div class="detail-value">{escape(app.actual_route or "未設定")}</div></div>
      <div><div class="detail-label">応募日</div><div class="detail-value">{escape(app.application_date or "未登録")}</div></div>
      <div><div class="detail-label">管理メモ</div><div class="detail-value">{escape(app.notes or "未登録")}</div></div>
    </section>''', unsafe_allow_html=True)

    if overdue:
        st.markdown(
            f'<div class="detail-attention"><span class="detail-attention-mark">!</span><div><b>期限を過ぎた予定が{len(overdue)}件あります。</b><br>'
            '下の「選考の進行」で、完了・延期・中止のいずれかを登録してください。</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="detail-section-title">選考予定・結果を登録する</div>', unsafe_allow_html=True)
    st.markdown('<p class="detail-section-copy">選考終了までを一つの流れとして、予定の追加・変更と結果の登録を行います。</p>', unsafe_allow_html=True)

    with st.container(border=True):
        upcoming_milestones = [m for m in detail["milestones"] if m.status == "pending"]
        st.markdown('<div class="detail-subtitle">次にすべきこと</div>', unsafe_allow_html=True)
        st.markdown('<p class="detail-subcopy">次に予定されている内容を、ここで確認・更新できます。</p>', unsafe_allow_html=True)
        if not upcoming_milestones:
            if "結果待ち" in (app.current_phase or ""):
                st.markdown('<div class="detail-empty">現在は選考結果を待っている状態です。結果が届いたら、下から登録してください。</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="detail-attention"><span class="detail-attention-mark">!</span><div><b>次の予定が登録されていません。</b><br>選考を継続する場合は、下の入力欄から次の予定を登録してください。</div></div>', unsafe_allow_html=True)
        ordered_milestones = upcoming_milestones
        for milestone in ordered_milestones:
            st.markdown(
                f'<span id="milestone-action-{milestone.id}" class="application-anchor"></span>',
                unsafe_allow_html=True,
            )
            card_kind = (
                "overdue" if is_milestone_overdue(milestone, date.today()) else "pending"
            )
            with st.container(key=f"detail_milestone_{card_kind}_{milestone.id}"):
                info, action = st.columns([4, 1])
                time_text = ""
                if milestone.start_time:
                    time_text = f" {milestone.start_time}"
                    if milestone.end_time:
                        time_text += f"〜{milestone.end_time}"
                info.markdown(
                    f'<div class="milestone-name">{escape(milestone.title or milestone.milestone_type)}'
                    f'<span class="milestone-status">{escape(milestone_status_label(milestone.status))}</span></div>'
                    f'<div class="milestone-meta">{escape(milestone.scheduled_date or "日付未定")}{escape(time_text)}'
                    f'　・　{escape(milestone.milestone_type)}</div>',
                    unsafe_allow_html=True,
                )
                if action.button("完了にする", key=f"unified_complete_{milestone.id}", use_container_width=True):
                    complete_milestone(milestone)
                    st.session_state[phase_confirmation_key] = True
                    _rerun_application_detail(embedded=embedded)
                with st.expander("予定を編集"):
                    try:
                        current_schedule_date = date.fromisoformat(milestone.scheduled_date)
                    except (TypeError, ValueError):
                        current_schedule_date = date.today()
                    try:
                        current_start_time = datetime.strptime(milestone.start_time, "%H:%M").time() if milestone.start_time else None
                    except ValueError:
                        current_start_time = None
                    try:
                        current_end_time = datetime.strptime(milestone.end_time, "%H:%M").time() if milestone.end_time else None
                    except ValueError:
                        current_end_time = None
                    with st.form(f"unified_schedule_edit_form_{milestone.id}"):
                        st.markdown("**予定日時を修正**")
                        st.caption("入力内容の訂正や、確定した日時への更新に使用します。履歴上の延期にはなりません。")
                        edit_date_col, edit_start_col, edit_end_col = st.columns(3)
                        edited_date = edit_date_col.date_input("実施日・期限", value=current_schedule_date, key=f"unified_edit_date_{milestone.id}")
                        edited_start = edit_start_col.time_input("開始時刻（任意）", value=current_start_time, key=f"unified_edit_start_{milestone.id}")
                        edited_end = edit_end_col.time_input("終了時刻（任意）", value=current_end_time, key=f"unified_edit_end_{milestone.id}")
                        if st.form_submit_button("日時の修正を保存", type="primary", use_container_width=True):
                            try:
                                update_milestone_schedule(milestone, edited_date.isoformat(), edited_start.strftime("%H:%M") if edited_start else "", edited_end.strftime("%H:%M") if edited_end else "")
                            except ApplicationManagementError as exc:
                                st.error(str(exc))
                            else:
                                st.toast("予定日時を修正しました。")
                                _rerun_application_detail(embedded=embedded)
                    st.markdown("---")
                    st.markdown("**別の日程へ延期する**")
                    st.caption("実際に延期が発生した場合に使用します。元の予定は延期履歴として残ります。")
                    new_date = st.date_input("変更後の日付", value=date.today(), key=f"unified_postpone_date_{milestone.id}")
                    reason = st.text_input("理由（任意）", key=f"unified_milestone_reason_{milestone.id}")
                    p1, p2 = st.columns(2)
                    if p1.button("日程を変更", key=f"unified_postpone_{milestone.id}"):
                        postpone_milestone(milestone, new_date.isoformat(), reason)
                        st.session_state[phase_confirmation_key] = True
                        _rerun_application_detail(embedded=embedded)
                    if p2.button("中止", key=f"unified_cancel_{milestone.id}"):
                        cancel_milestone(milestone, reason)
                        st.session_state[phase_confirmation_key] = True
                        _rerun_application_detail(embedded=embedded)
                    st.markdown("---")
                    st.caption("誤って登録した予定だけを削除してください。削除した予定は元に戻せません。")
                    confirm = st.checkbox("誤登録のため完全に削除する", key=f"unified_delete_confirm_{milestone.id}")
                    if st.button("物理削除", key=f"unified_delete_{milestone.id}", disabled=not confirm):
                        delete_milestone_data(milestone)
                        _rerun_application_detail(embedded=embedded)

        historical_milestones = [
            milestone for milestone in detail["milestones"]
            if milestone.status in {"completed", "postponed", "cancelled"}
        ]
        if historical_milestones:
            with st.expander(f"完了・延期・中止済みの予定（{len(historical_milestones)}件）"):
                st.caption(
                    "実際に発生した完了・延期・中止は履歴として残してください。"
                    "誤って登録した予定に限り、状態にかかわらず物理削除できます。"
                )
                for milestone in historical_milestones:
                    row_info, row_action = st.columns([4, 1])
                    row_info.markdown(
                        f"**{escape(milestone.title or milestone.milestone_type)}**　"
                        f"{escape(milestone_status_label(milestone.status))}  \n"
                        f"{escape(milestone.scheduled_date or '日付未定')}　・　"
                        f"{escape(milestone.milestone_type)}"
                    )
                    with row_action:
                        confirm_history_delete = st.checkbox(
                            "誤登録",
                            key=f"history_delete_confirm_{milestone.id}",
                        )
                        if st.button(
                            "物理削除",
                            key=f"history_delete_{milestone.id}",
                            disabled=not confirm_history_delete,
                            use_container_width=True,
                        ):
                            delete_milestone_data(milestone)
                            _rerun_application_detail(embedded=embedded)

    with st.expander("＋ 選考結果を登録する", expanded=False):
        st.caption("結果と次回選考を登録すると、次の予定と現在フェーズへ反映されます。")
        r1, r2, r3 = st.columns(3)
        stage_index = SELECTION_STAGES.index(app.selection_stage) if app.selection_stage in SELECTION_STAGES else 0
        stage = r1.selectbox("対象選考", SELECTION_STAGES, index=stage_index)
        result_index = RESULT_OPTIONS.index(app.selection_result) if app.selection_result in RESULT_OPTIONS else 0
        result = r2.selectbox("結果", RESULT_OPTIONS, index=result_index)
        next_stage = r3.selectbox("次回選考（通過時）", ("未定",) + SELECTION_STAGES)
        next_date_value = ""
        next_start_value = next_end_value = None
        if result == "通過" and next_stage != "未定":
            date_decided = st.checkbox("次回選考の日程も決まっている", key=f"next_date_decided_{app.id}")
            if date_decided:
                nd1, nd2, nd3 = st.columns(3)
                next_date_value = nd1.date_input("次回選考日", value=date.today(), key=f"next_selection_date_{app.id}").isoformat()
                next_start_value = nd2.time_input("開始時刻", value=None, key=f"next_selection_start_{app.id}")
                next_end_value = nd3.time_input("終了時刻（任意）", value=None, key=f"next_selection_end_{app.id}")
        st.caption(f"画面上では「{stage}{result}」として扱います。現在フェーズと次回選考の予定は登録内容から自動更新されます。")
        if st.button("結果を登録", type="primary", use_container_width=True):
            register_selection_result(
                app.id, stage, result,
                "" if next_stage == "未定" else next_stage,
                next_date_value,
                next_start_value.strftime("%H:%M") if next_start_value else "",
                next_end_value.strftime("%H:%M") if next_end_value else "",
            )
            st.session_state[phase_confirmation_key] = True
            _rerun_application_detail(embedded=embedded)

    with st.expander("＋ 次の予定を登録する", expanded=not upcoming_milestones):
        a, b = st.columns([1, 2])
        kind = a.selectbox("予定の種類", MILESTONE_TYPES, key=f"unified_milestone_kind_{app.id}")
        title = b.text_input("予定名", placeholder="例：一次面接", key=f"unified_milestone_title_{app.id}")
        d1, d2, d3 = st.columns(3)
        scheduled_date = d1.date_input("実施日・期限", value=date.today(), key=f"unified_milestone_date_{app.id}")
        start_at = d2.time_input("開始時刻（任意）", value=None, key=f"unified_milestone_start_{app.id}")
        end_at = d3.time_input("終了時刻（任意）", value=None, key=f"unified_milestone_end_{app.id}")
        if st.button("予定を登録", type="primary", key=f"unified_milestone_add_{app.id}"):
            add_milestone_data(ApplicationMilestone(application_id=app.id, milestone_type=kind, title=title.strip() or kind, scheduled_date=scheduled_date.isoformat(), start_time=start_at.strftime("%H:%M") if start_at else "", end_time=end_at.strftime("%H:%M") if end_at else ""))
            st.session_state[phase_confirmation_key] = True
            _rerun_application_detail(embedded=embedded)

    if not st.session_state.get(phase_confirmation_key, False):
        if st.button(
            "選考の現在地を確認・修正",
            key=f"reveal_phase_confirmation_{app.id}",
            use_container_width=False,
        ):
            st.session_state[phase_confirmation_key] = True
            _rerun_application_detail(embedded=embedded)
    else:
        st.markdown('<div class="detail-section-title">選考の現在地</div>', unsafe_allow_html=True)
        st.markdown('<p class="detail-section-copy">予定・結果の登録内容から自動更新された現在地です。</p>', unsafe_allow_html=True)
        with st.container(border=True):
            phase_col, correction_col = st.columns([3.5, 1.5])
            phase_col.markdown(
                f'<span class="phase-pill">{escape(app.current_phase)}</span>',
                unsafe_allow_html=True,
            )
            with correction_col.expander("実際と異なる場合は修正"):
                phase = st.selectbox(
                    "修正後の現在地", PHASE_OPTIONS,
                    index=PHASE_OPTIONS.index(app.current_phase) if app.current_phase in PHASE_OPTIONS else 0,
                )
                if st.button("現在地を修正", use_container_width=True):
                    app.current_phase = phase
                    update_application_data(app)
                    _rerun_application_detail(embedded=embedded)


@st.dialog(
    "選考予定・結果を登録",
    width="large",
    on_dismiss=_close_schedule_dialog_for_filter_change,
)
def _render_application_detail_dialog(application_id: int) -> None:
    """応募管理画面を離れず、予定・結果の登録と現在地確認を行う。"""
    st.markdown(
        """
        <style>
        div[role="dialog"] { max-width:min(1460px, 94vw) !important; }
        div[role="dialog"] > div { max-height:92vh; }
        div[role="dialog"] [data-testid="stDialogBody"] { padding-top:0; }
        div[role="dialog"] [data-testid="stVerticalBlock"] { gap:.48rem; }
        div[role="dialog"] [data-testid="stForm"] { padding:.65rem .8rem; }
        div[role="dialog"] [data-testid="stExpander"] details summary { min-height:38px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _, close_col = st.columns([5.5, 1])
    if close_col.button(
        "閉じる", key=f"close_application_dialog_{application_id}",
        use_container_width=True,
    ):
        st.session_state.pop("schedule_dialog_application_id", None)
        st.rerun()
    render_application_detail_page(
        application_id,
        embedded=True,
    )


def render_selection_preparation_page() -> None:
    render_job_navigation("selection_preparation")
    _inject_css()
    application_id = int(st.query_params.get("application_id", "0") or 0)
    if application_id <= 0:
        # The shared navigation opens this chooser first because preparation is
        # stored per application and cannot be edited without selecting one.
        st.markdown(
            '<h1 class="prep-page-title">選考準備</h1>'
            '<p class="prep-chooser-lead">準備する応募企業を選択してください。企業ごとの準備内容と、現在の選考に合わせたテーマを確認できます。</p>',
            unsafe_allow_html=True,
        )
        views = load_application_views(include_closed=False)
        if views:
            cards = "".join(
                f'<a class="prep-chooser-card" href="?page=selection_preparation&amp;application_id={view["application"].id}" target="_self">'
                f'<div><b>{escape(view["job"].company_name)}</b>'
                f'<span>{escape(view["application"].current_phase or "応募準備")}　／　{escape(view["application"].actual_route or "応募経路未設定")}</span></div>'
                '<i>›</i></a>'
                for view in views
            )
            st.markdown(f'<div class="prep-chooser-grid">{cards}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="prep-chooser-empty">選考準備を作成できる応募企業がありません。<br>求人確認画面から応募判断を登録してください。</div>',
                unsafe_allow_html=True,
            )
        return
    detail = load_application_detail(application_id)
    if not detail:
        st.error("応募情報が見つかりません。")
        return
    app, job = detail["application"], detail["job"]
    selection_type = app.current_phase.replace("調整中", "").replace("予定", "").replace("結果待ち", "") or "選考"
    items = load_preparation_items(app.id, selection_type)
    global_templates = load_global_preparation_templates()
    scope_labels = {"selection": "選考別準備", "company": "企業別準備", "common": "共通準備"}
    requested_scope = str(st.query_params.get("prep_tab", "selection"))
    if requested_scope not in scope_labels:
        requested_scope = "selection"
    tab_state_key = f"selection_preparation_scope_{app.id}"
    if tab_state_key not in st.session_state:
        st.session_state[tab_state_key] = scope_labels[requested_scope]
    selected_scope_label = st.session_state[tab_state_key]
    active_tab = next(
        (key for key, label in scope_labels.items() if label == selected_scope_label),
        "selection",
    )
    if active_tab == "common":
        visible = global_templates
    elif active_tab == "selection":
        visible = [item for item in items if item.scope == "selection" and item.selection_type == selection_type]
    else:
        visible = [item for item in items if item.scope == "company"]
    visible = sorted(visible, key=lambda item: (item.sort_order, item.id))
    completed = sum(item.is_completed for item in visible)
    rate = round(completed / len(visible) * 100) if visible else 0
    next_date = next((m.scheduled_date for m in detail["milestones"] if m.status == "pending"), "日程未定")

    st.markdown(
        '<a class="prep-action" href="?page=application_list">← 応募管理へ戻る</a>',
        unsafe_allow_html=True,
    )
    st.markdown(f'''<div class="prep-head"><div>
      <h1 class="prep-page-title">選考準備 <span class="phase-pill">{escape(selection_type)}</span></h1>
      <div class="prep-company">{escape(job.company_name)}　/　{escape(job.job_title or "求人名未登録")}</div></div>
      <div class="prep-meta"><div class="progress-track"><div class="progress-fill" style="width:{rate}%"></div></div>
      <b>{rate}%</b><span>{completed} / {len(visible)} 完了</span></div></div>
      ''', unsafe_allow_html=True)
    if st.button(
        "＋ テーマを追加",
        key=f"show_custom_theme_form_{app.id}_{active_tab}",
        use_container_width=False,
    ):
        st.session_state[f"custom_theme_form_open_{app.id}_{active_tab}"] = True
    st.segmented_control(
        "準備の種類",
        options=list(scope_labels.values()),
        key=tab_state_key,
        label_visibility="collapsed",
        width="stretch",
    )

    if active_tab == "company":
        if st.button("共通原稿をこの企業へコピー（既存内容は上書きしない）"):
            copied = copy_global_preparations_to_application(app.id)
            st.toast(f"{copied}件を企業別準備へコピーしました。")
            st.rerun()
    elif active_tab == "selection":
        if st.button("企業別準備をこの選考へコピー（既存内容は上書きしない）"):
            copied = copy_application_preparations_to_selection(app.id, selection_type)
            st.toast(f"{copied}件を{selection_type}へコピーしました。")
            st.rerun()

    main_column, side_column = st.columns([3.35, 1], gap="large")
    with main_column:
        st.markdown(
            f'<div class="prep-section-head"><h2>標準テーマ（{len(visible)}項目）</h2>'
            '<span class="prep-sort">並び替え：おすすめ順　▦ ☰</span></div>',
            unsafe_allow_html=True,
        )
        card_columns = st.columns(2, gap="medium")
        for index, item in enumerate(visible):
            with card_columns[index % 2]:
                state = "完了" if item.is_completed else ("入力済み" if item.content else "未着手")
                updated = item.updated_at[:16].replace("T", " ") if item.updated_at else "未更新"
                with st.expander(
                    f"{item.title}　｜　{state}",
                    expanded=False,
                    key=f"prep_theme_{active_tab}_{item.id}",
                    type="compact",
                ):
                    st.markdown(
                        f'<p class="prep-theme-description">{escape(item.description)}</p>',
                        unsafe_allow_html=True,
                    )
                    content_key = f"prep_content_{active_tab}_{item.id}"
                    pending_content_key = f"prep_pending_content_{active_tab}_{item.id}"
                    if pending_content_key in st.session_state:
                        st.session_state[content_key] = st.session_state.pop(pending_content_key)
                    content = st.text_area(
                        "整理した内容",
                        value=item.content,
                        key=content_key,
                        height=230,
                        placeholder="考えたことや確認したい内容を、自分の言葉で直接入力します。",
                    )
                    done = st.checkbox(
                        "準備完了",
                        value=item.is_completed,
                        key=f"prep_done_{active_tab}_{item.id}",
                    )
                    st.markdown(
                        f'<div class="prep-theme-updated">最終更新：{escape(updated)}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "保存",
                        key=f"prep_save_{active_tab}_{item.id}",
                        type="primary",
                        use_container_width=True,
                    ):
                        item.content, item.is_completed = content, done
                        if active_tab == "common":
                            save_global_preparation_template(item)
                        else:
                            save_preparation_item(item)
                        st.toast("準備内容を保存しました。")
                        st.rerun()
                    if item.is_custom:
                        delete_confirmed = st.checkbox(
                            "この追加テーマを削除する",
                            key=f"prep_delete_confirm_{active_tab}_{item.id}",
                        )
                        if st.button(
                            "追加テーマを削除",
                            key=f"prep_delete_{active_tab}_{item.id}",
                            disabled=not delete_confirmed,
                            use_container_width=True,
                        ):
                            try:
                                delete_custom_preparation(item)
                            except ApplicationManagementError as exc:
                                st.error(str(exc))
                            else:
                                st.toast("追加テーマを削除しました。")
                                st.rerun()
    with side_column:
        with st.container(border=False, key=f"prep_sidebar_{app.id}_{active_tab}"):
            st.markdown(f'''<div class="prep-side-overview"><h3>この選考の概要</h3><dl>
              <dt>選考ステップ</dt><dd>{escape(selection_type)}</dd><dt>選考目標</dt><dd>{escape(next_date)}</dd>
              <dt>面接形式</dt><dd>未登録</dd><dt>応募経路</dt><dd>{escape(app.actual_route or "未設定")}</dd>
              </dl></div><div class="prep-ai-heading"><h3>AI支援</h3>
              <p>選択したテーマに関連する材料をAIが提示します。内容を確認してから準備メモへ追加できます。</p></div>''', unsafe_allow_html=True)
            if visible:
                selected_item = st.selectbox(
                    "材料を取得するテーマ",
                    options=visible,
                    format_func=lambda row: row.title,
                    key=f"prep_ai_theme_{app.id}_{active_tab}",
                )
                # Version the session key whenever the AI output contract changes so an
                # old generated result is not mistaken for a result from the current rules.
                result_key = f"prep_ai_result_v7_{app.id}_{active_tab}_{selected_item.id}"
                if st.button(
                    "AIから材料を取得する",
                    key=f"prep_ai_generate_{app.id}_{active_tab}",
                    use_container_width=True,
                ):
                    try:
                        with st.spinner("登録情報をもとに材料を整理しています…"):
                            material = generate_preparation_material(
                                job_id=app.job_id,
                                company_name=job.company_name,
                                job_title=job.job_title or "求人名未登録",
                                selection_type=selection_type,
                                theme_key=selected_item.theme_key,
                                theme_title=selected_item.title,
                                theme_description=selected_item.description,
                                existing_content=selected_item.content,
                            )
                        st.session_state[result_key] = format_preparation_material(
                            material,
                            selected_item.theme_key,
                        )
                    except SelectionPreparationAIError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("AI材料の取得処理でエラーが発生しました。画面を再読み込みして、もう一度お試しください。")
                if result_key in st.session_state:
                    generated_text = st.text_area(
                        "AIが提示した材料",
                        value=st.session_state[result_key],
                        height=260,
                        key=f"prep_ai_text_v7_{app.id}_{active_tab}_{selected_item.id}",
                    )
                    st.caption("AIの内容には誤りが含まれる場合があります。事実と異なる箇所を修正してから追加してください。")
                    if st.button(
                        "このテーマの準備メモに追加",
                        type="primary",
                        key=f"prep_ai_apply_v7_{app.id}_{active_tab}_{selected_item.id}",
                        use_container_width=True,
                    ):
                        selected_item.content = "\n\n".join(
                            row for row in (selected_item.content.strip(), generated_text.strip()) if row
                        )
                        if active_tab == "common":
                            save_global_preparation_template(selected_item)
                        else:
                            save_preparation_item(selected_item)
                        st.session_state[
                            f"prep_pending_content_{active_tab}_{selected_item.id}"
                        ] = selected_item.content
                        st.session_state.pop(result_key, None)
                        st.toast("AIの材料を準備メモへ追加しました。")
                        st.rerun()
            else:
                st.info("材料を取得するテーマがありません。先にテーマを追加してください。")
    custom_form_key = f"custom_theme_form_open_{app.id}_{active_tab}"
    if st.session_state.get(custom_form_key, False):
        with st.container(border=True, key=f"custom_theme_form_{app.id}_{active_tab}"):
            st.markdown("### 自由テーマを追加")
            st.caption(f"「{scope_labels[active_tab]}」に新しい準備テーマを追加します。")
            custom_title = st.text_input(
                "テーマ名",
                key=f"custom_theme_title_{app.id}_{active_tab}",
                placeholder="例：面接で確認したいこと",
            )
            add_col, cancel_col = st.columns(2)
            if add_col.button(
                "このテーマを追加",
                key=f"add_custom_theme_{app.id}_{active_tab}",
                type="primary",
                disabled=not custom_title.strip(),
                use_container_width=True,
            ):
                add_custom_preparation(
                    app.id,
                    selection_type,
                    custom_title,
                    scope=active_tab,
                )
                st.session_state[custom_form_key] = False
                st.toast("準備テーマを追加しました。")
                st.rerun()
            if cancel_col.button(
                "キャンセル",
                key=f"cancel_custom_theme_{app.id}_{active_tab}",
                use_container_width=True,
            ):
                st.session_state[custom_form_key] = False
                st.rerun()
