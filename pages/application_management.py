"""応募管理・就職活動ダッシュボード画面（カード内編集対応）。"""

import calendar
import base64
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

import streamlit as st

from models import ApplicationActivity, ApplicationMilestone
from pages.job_layout import render_job_navigation
from services.application_management_service import (
    MILESTONE_TYPES,
    PHASE_OPTIONS,
    RESULT_OPTIONS,
    SELECTION_STAGES,
    ApplicationManagementError,
    add_manual_activity,
    add_custom_preparation,
    add_milestone_data,
    cancel_milestone,
    complete_milestone,
    delete_milestone_data,
    is_milestone_overdue,
    is_milestone_upcoming,
    milestone_status_label,
    postpone_milestone,
    update_milestone_schedule,
    dashboard_summary,
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
        .prep-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin:2px 0 20px;padding-bottom:20px;border-bottom:1px solid #dfe6f0}
        .prep-company{margin-top:12px;color:#1f3454;font-size:14px;font-weight:750}.prep-meta{display:flex;gap:13px;align-items:center;padding-top:14px;white-space:nowrap}
        .progress-track{width:220px;height:10px;background:#e7edf7;border-radius:99px;overflow:hidden}.progress-fill{height:100%;background:#1268f3;border-radius:99px}
        .prep-actions{display:flex;justify-content:flex-end;gap:10px;margin:-4px 0 16px}.prep-action{padding:8px 14px;border:1px solid #a9c7fb;border-radius:8px;background:#fff;color:#1268f3!important;text-decoration:none!important;font-size:13px;font-weight:800}
        .prep-tabs{display:flex;gap:38px;border-bottom:1px solid #dce4ef;margin-bottom:24px}.prep-tab{padding:12px 2px;color:#53647b!important;text-decoration:none!important;font-size:14px;font-weight:800;border-bottom:3px solid transparent}
        .prep-tab.active{color:#1268f3!important;border-bottom-color:#1268f3}.prep-layout{display:grid;grid-template-columns:minmax(0,1fr) 285px;gap:24px;align-items:start}
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
        .prep-side{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:18px;height:max-content;position:sticky;top:20px}.prep-side h3{font-size:16px;margin:0 0 16px}.prep-side dl{display:grid;grid-template-columns:78px 1fr;gap:12px 8px;font-size:12px}.prep-side dt{color:#738299}.prep-side dd{margin:0;font-weight:700}.prep-side-section{margin-top:18px;padding-top:18px;border-top:1px solid #e4e9f1}.prep-side-button{display:block;margin-top:12px;padding:9px;text-align:center;border:1px solid #a9c7fb;border-radius:8px;color:#1268f3!important;text-decoration:none!important;font-size:12px;font-weight:800}
        @media(max-width:1100px){.prep-grid{grid-template-columns:repeat(2,1fr)}.prep-layout{grid-template-columns:1fr}.prep-side{position:static}.detail-grid{grid-template-columns:1fr}.detail-hero{grid-template-columns:1fr}.detail-hero>div{border-right:0;border-bottom:1px solid #e6ebf2}}
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
        f'<a class="{"active" if active == "dashboard" else ""}" href="?page=application_dashboard">就職活動ダッシュボード</a>'
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
    anchor_by_focus = {
        "preparation": "application-company-list",
        "active": "application-company-list",
        "upcoming": "application-upcoming",
        "attention": "application-attention",
    }
    html = '<div class="summary-grid application-summary-grid">'
    for item in items:
        label, value, kind = item[:3]
        unit = item[3] if len(item) >= 4 else "社"
        focus = item[4] if len(item) >= 5 else ""
        application_ids = item[5] if len(item) >= 6 else set()
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
    _close_schedule_dialog_for_filter_change()


def _close_schedule_dialog_for_filter_change() -> None:
    """絞り込みによる再描画で、以前閉じた応募詳細を再表示しない。"""

    st.session_state.pop("schedule_dialog_application_id", None)
    st.session_state.pop("schedule_dialog_target_milestone_id", None)


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
                 "最終更新が古い順", "会社名順", "現在フェーズ順"],
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
    # トップ画面・通知・旧応募詳細URLから来た場合も、独立ページへは遷移せず
    # この応募管理画面上で予定・結果登録モーダルを一度だけ開く。
    try:
        requested_application_id = int(st.query_params.get("application_id", "0") or 0)
    except (TypeError, ValueError):
        requested_application_id = 0
    if requested_application_id:
        st.session_state["schedule_dialog_application_id"] = requested_application_id
        try:
            requested_milestone_id = int(st.query_params.get("milestone_id", "0") or 0)
        except (TypeError, ValueError):
            requested_milestone_id = 0
        if requested_milestone_id:
            st.session_state["schedule_dialog_target_milestone_id"] = requested_milestone_id
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
        or query
        or phase_filter != "すべて"
        or route_filter != "すべて"
        or response_filter != "すべて"
        or sort_order != "対応が必要な順"
    )
    with st.container(key="application_schedule_section"):
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
        selected_milestone_id = int(
            st.session_state.pop("schedule_dialog_target_milestone_id", 0) or 0
        )
        _render_application_detail_dialog(selected_application_id, selected_milestone_id)


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


def render_application_dashboard_page() -> None:
    render_job_navigation("application_dashboard")
    _inject_css()
    sync_applications_from_decisions()
    _tabs("dashboard")
    st.title("就職活動ダッシュボード")
    st.markdown('<p class="page-lead">応募状況と選考実績を振り返り、今後のアクションに活かします。</p>', unsafe_allow_html=True)
    data = dashboard_summary()
    _summary_cards([("管理対象", data["total"], ""), ("応募", data["applied"], ""), ("面接進出", data["interview"], ""), ("内定", data["offers"], "offer")])
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("現在フェーズ（集計）")
        _bar_panel(data["categories"], data["total"])
    with right:
        st.subheader("詳細フェーズ内訳")
        _bar_panel(data["detailed"], data["total"])
    st.subheader("選考実績（全体の流れ）")
    st.markdown(
        '<div class="funnel">' + ''.join([
            f'<div class="funnel-card">応募<strong>{data["applied"]}社</strong></div>',
            f'<div class="funnel-card">書類通過<strong>{data["document_pass"]}社</strong></div>',
            f'<div class="funnel-card">面接進出<strong>{data["interview"]}社</strong></div>',
            f'<div class="funnel-card">内定<strong>{data["offers"]}社</strong></div>',
        ]) + '</div>', unsafe_allow_html=True,
    )
    _rate_cards(data)
    st.subheader("応募経路別実績")
    _route_table(data["routes"])


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


def render_application_detail_page() -> None:
    render_job_navigation("application_list")
    _inject_css()
    application_id = int(st.query_params.get("application_id", "0") or 0)
    detail = load_application_detail(application_id)
    if not detail:
        st.error("応募情報が見つかりません。")
        st.page_link("app.py", label="応募管理へ戻る", query_params={"page": "application_list"})
        return
    app, job = detail["application"], detail["job"]
    st.markdown('<a href="?page=application_list">← 応募管理へ戻る</a>', unsafe_allow_html=True)
    st.title(job.company_name)
    st.caption(job.job_title or "求人名未登録")
    st.subheader("選考状況")
    c1, c2, c3 = st.columns(3)
    route = c1.text_input("実際の応募経路", value=app.actual_route)
    phase = c2.selectbox("現在フェーズ", PHASE_OPTIONS, index=PHASE_OPTIONS.index(app.current_phase) if app.current_phase in PHASE_OPTIONS else 0)
    result = c3.selectbox("選考結果", RESULT_OPTIONS, index=RESULT_OPTIONS.index(app.selection_result) if app.selection_result in RESULT_OPTIONS else 0)
    application_date = st.date_input("応募日", value=date.fromisoformat(app.application_date) if app.application_date else None)
    notes = st.text_area("メモ", value=app.notes)
    if st.button("選考状況を保存", type="primary", use_container_width=True):
        app.actual_route, app.current_phase, app.selection_result = route.strip(), phase, result
        app.application_date = application_date.isoformat() if application_date else None
        app.notes = notes
        update_application_data(app)
        st.toast("選考状況を保存しました。")
        st.rerun()
    st.subheader("予定・期限")
    with st.expander("予定を追加", expanded=not detail["milestones"]):
        kind = st.selectbox("種類", MILESTONE_TYPES)
        title = st.text_input("予定名", placeholder="例：一次面接")
        d = st.date_input("日付", value=date.today(), key="milestone_date")
        schedule_kind = st.radio("日付の意味", ["予定", "期限"], horizontal=True)
        memo = st.text_area("補足", key="milestone_memo")
        if st.button("予定を登録", type="primary"):
            try:
                add_milestone_data(ApplicationMilestone(
                    application_id=app.id,
                    milestone_type=kind,
                    title=title.strip(),
                    schedule_kind="deadline" if schedule_kind == "期限" else "event",
                    scheduled_date=d.isoformat(),
                    memo=memo.strip(),
                ))
            except ApplicationManagementError as exc:
                st.error(str(exc))
            else:
                st.toast("予定を登録しました。")
                st.rerun()
    if not detail["milestones"]:
        st.info("予定はまだ登録されていません。")
    for milestone in detail["milestones"]:
        with st.container(border=True):
            header, status_column = st.columns([4, 1])
            header.markdown(
                f"**{milestone.title or milestone.milestone_type}**  "
                f"  {milestone.scheduled_date or '日付未定'}"
            )
            status_column.markdown(f"**{milestone_status_label(milestone.status)}**")
            if milestone.memo:
                st.caption(milestone.memo)
            if milestone.status == "pending":
                complete_column, postpone_column, cancel_column = st.columns(3)
                if complete_column.button("完了にする", key=f"complete_{milestone.id}", use_container_width=True):
                    try:
                        complete_milestone(milestone)
                    except ApplicationManagementError as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
                with postpone_column.expander("延期する"):
                    original = date.today()
                    if milestone.scheduled_date:
                        try:
                            original = date.fromisoformat(milestone.scheduled_date)
                        except ValueError:
                            pass
                    new_date = st.date_input(
                        "新しい日付",
                        value=original + timedelta(days=1),
                        key=f"postpone_date_{milestone.id}",
                    )
                    reason = st.text_input("延期理由（任意）", key=f"postpone_reason_{milestone.id}")
                    if st.button("新しい予定を作る", key=f"postpone_{milestone.id}"):
                        try:
                            postpone_milestone(milestone, new_date.isoformat(), reason)
                        except ApplicationManagementError as exc:
                            st.error(str(exc))
                        else:
                            st.toast("元の予定を延期として残し、新しい予定を作成しました。")
                            st.rerun()
                with cancel_column.expander("中止する"):
                    cancel_reason = st.text_input("中止理由（任意）", key=f"cancel_reason_{milestone.id}")
                    confirm_cancel = st.checkbox("この予定を中止します", key=f"cancel_confirm_{milestone.id}")
                    if st.button("予定を中止", key=f"cancel_{milestone.id}", disabled=not confirm_cancel):
                        try:
                            cancel_milestone(milestone, cancel_reason)
                        except ApplicationManagementError as exc:
                            st.error(str(exc))
                        else:
                            st.toast("予定を中止しました。履歴は保持されます。")
                            st.rerun()
            with st.expander("誤って登録した予定を削除"):
                st.caption(
                    "この予定を予定一覧から削除します。"
                    "選考予定そのものがなくなった場合は、削除ではなく「中止する」を使用してください。"
                )
                confirm_delete = st.checkbox(
                    "この予定を削除することを確認しました",
                    key=f"delete_confirm_{milestone.id}",
                )
                if st.button(
                    "予定を削除",
                    key=f"delete_{milestone.id}",
                    disabled=not confirm_delete,
                ):
                    try:
                        delete_milestone_data(milestone)
                    except ApplicationManagementError as exc:
                        st.error(str(exc))
                    else:
                        st.toast("誤って登録した予定を削除しました。")
                        st.rerun()
    st.subheader("活動履歴")
    with st.expander("活動を手動で追加"):
        activity_title = st.text_input("活動内容", key="activity_title")
        activity_detail = st.text_area("詳細", key="activity_detail")
        if st.button("活動を追加") and activity_title:
            add_manual_activity(app.id, activity_title, activity_detail, datetime.now().isoformat(timespec="minutes")); st.rerun()
    for activity in detail["activities"]:
        st.markdown(f'**{escape(activity.title)}**　{escape(activity.occurred_at)}  \n{escape(activity.detail)}')


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
    target_milestone_override: int = 0,
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
    next_m = min(pending, key=lambda m: m.scheduled_date or "9999-12-31", default=None)
    overdue = [m for m in pending if is_milestone_overdue(m, date.today())]
    try:
        target_milestone_id = (
            int(target_milestone_override)
            if embedded
            else int(st.query_params.get("milestone_id", "0") or 0)
        )
    except (TypeError, ValueError):
        target_milestone_id = 0
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
                        except Exception as exc:
                            st.error(f"応募情報を更新できませんでした：{exc}")
                        else:
                            st.toast("応募経路・応募日・管理メモを更新しました。")
                            _rerun_application_detail(embedded=embedded)
    next_text = "予定未登録"
    if next_m:
        next_text = f"{next_m.title or next_m.milestone_type}　{_display_milestone_date(next_m.scheduled_date)} {next_m.start_time}"
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
def _render_application_detail_dialog(application_id: int, target_milestone_id: int = 0) -> None:
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
        st.session_state.pop("schedule_dialog_target_milestone_id", None)
        st.rerun()
    render_application_detail_page(
        application_id,
        embedded=True,
        target_milestone_override=target_milestone_id,
    )


def render_selection_preparation_page() -> None:
    render_job_navigation("application_list")
    _inject_css()
    application_id = int(st.query_params.get("application_id", "0") or 0)
    detail = load_application_detail(application_id)
    if not detail:
        st.error("応募情報が見つかりません。")
        return
    app, job = detail["application"], detail["job"]
    selection_type = app.current_phase.replace("調整中", "").replace("予定", "").replace("結果待ち", "") or "選考"
    items = load_preparation_items(app.id, selection_type)
    global_templates = load_global_preparation_templates()
    active_tab = str(st.query_params.get("prep_tab", "selection"))
    if active_tab not in {"selection", "company", "common"}:
        active_tab = "selection"
    scope_labels = {"selection": "選考別準備", "company": "企業別準備", "common": "共通準備"}
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
      <div class="prep-actions"><a class="prep-action" href="#free-theme">＋ テーマを追加</a></div>
      <nav class="prep-tabs">''' + ''.join(
        f'<a class="prep-tab {"active" if key == active_tab else ""}" href="?page=selection_preparation&amp;application_id={app.id}&amp;prep_tab={key}">{label}</a>'
        for key, label in scope_labels.items()
      ) + '</nav>', unsafe_allow_html=True)

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

    icon_map = {
        "self_intro": "♙", "career_reason": "↔", "motivation": "▦", "career_plan": "▥",
        "achievement": "♛", "strengths": "●", "conditions": "▣", "questions": "?",
    }
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
                with st.container(border=False, key=f"prep_card_{item.id}"):
                    state = "完了" if item.is_completed else ("入力済み" if item.content else "未着手")
                    state_css = "" if item.is_completed else "todo"
                    updated = item.updated_at[:16].replace("T", " ") if item.updated_at else "未更新"
                    with st.container(key=f"prep_edit_{item.id}"):
                        with st.popover("編集"):
                            st.markdown(f'<div class="prep-editor"><div class="prep-editor-title">{escape(item.title)}を編集</div></div>', unsafe_allow_html=True)
                            content = st.text_area(
                                "整理した内容",
                                value=item.content,
                                key=f"prep_content_{item.id}",
                                height=180,
                                placeholder="考えたことや確認したい内容を、自分の言葉で整理します。",
                            )
                            done = st.checkbox(
                                "準備完了",
                                value=item.is_completed,
                                key=f"prep_done_{item.id}",
                            )
                            if st.button(
                                "保存",
                                key=f"prep_save_{item.id}",
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
                    note_html = (
                        f'<div class="prep-note">{escape(item.content)}</div>'
                        if item.content.strip()
                        else '<div class="prep-note empty">まだ整理した内容はありません<br>右上の編集から追加できます</div>'
                    )
                    st.markdown(f'''<div class="prep-card-body"><div class="prep-card-top">
                      <span class="prep-icon">{icon_map.get(item.theme_key, "✦")}</span><span class="prep-state {state_css}">{escape(state)}</span></div>
                      <h3>{escape(item.title)}</h3><p>{escape(item.description)}</p>{note_html}</div>''', unsafe_allow_html=True)
                    st.markdown(f'<div class="prep-updated">最終更新：{escape(updated)}</div>', unsafe_allow_html=True)
    with side_column:
        st.markdown(f'''<aside class="prep-side"><h3>この選考の概要</h3><dl><dt>選考ステップ</dt><dd>{escape(selection_type)}</dd>
          <dt>選考目標</dt><dd>{escape(next_date)}</dd><dt>面接形式</dt><dd>未登録</dd><dt>応募経路</dt><dd>{escape(app.actual_route or "未設定")}</dd></dl>
          <div class="prep-side-section"><h3>AI支援</h3><p style="font-size:12px;color:#66768d;line-height:1.65">選択したテーマに関連する材料をAIが提示します。</p>
          <span class="prep-side-button">AIから材料を取得する</span></div>
          <div class="prep-side-section"><h3>直近面接の振り返り</h3><p style="font-size:12px;color:#66768d">過去の質問や改善点を次の準備に活用します。</p></div></aside>''', unsafe_allow_html=True)

    st.markdown('<div id="free-theme"></div>', unsafe_allow_html=True)
    with st.expander("＋ テーマを追加する（自由テーマ）"):
        custom_title = st.text_input("テーマ名")
        if st.button("テーマを追加", disabled=not custom_title.strip()):
            add_custom_preparation(app.id, selection_type, custom_title)
            st.rerun()
