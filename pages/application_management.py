"""応募管理・就職活動ダッシュボード画面（カード内編集対応）。"""

import calendar
from datetime import date, datetime, timedelta
from html import escape

import streamlit as st

from models import ApplicationActivity, ApplicationMilestone
from pages.job_layout import render_job_navigation
from services.application_management_service import (
    MILESTONE_TYPES,
    PHASE_OPTIONS,
    RESULT_OPTIONS,
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
    dashboard_summary,
    load_application_detail,
    load_application_views,
    load_preparation_items,
    operational_summary,
    sync_applications_from_decisions,
    update_application_data,
    save_preparation_item,
)


BLUE = "#1268f3"
PHASE_CATEGORIES = ("応募準備", "書類選考", "適性検査", "面接", "オファー・条件確認", "内定", "保留", "終了")
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
        .block-container { max-width:1280px; padding-top:2rem !important; padding-bottom:3rem !important; }
        .application-page-head { margin:8px 0 18px; padding-bottom:2px; }
        .application-page-head h1 { margin:0; color:#0b2242; font-size:34px; line-height:1.25;
          letter-spacing:.015em; font-weight:850; }
        .application-page-head p { margin:9px 0 0; color:#66768d; font-size:15px; line-height:1.7; }
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
        .application-summary-grid { gap:16px; margin:22px 0 26px; }
        .application-summary-grid .summary-card { min-height:148px; padding:22px 20px 20px; }
        .application-summary-grid .summary-icon { width:44px; height:44px; margin-bottom:12px;
          border-radius:13px; }
        .application-summary-grid .summary-icon svg { width:23px; height:23px; fill:none;
          stroke:currentColor; stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }
        .application-summary-grid .summary-label { font-size:15px; }
        .application-summary-grid .summary-value { margin-top:8px; font-size:36px; }
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
.application-focus-context a {
    color:#1268f3!important; font-weight:700; text-decoration:none!important;
}
.application-focus-context a:hover { text-decoration:underline!important; }
.application-anchor { display:block; height:0; scroll-margin-top:24px; }
        .panel { padding:20px; margin:14px 0; }
        .panel h3 { margin:0 0 14px; font-size:18px; }
        .attention-panel {
          margin:20px 0 24px; padding:20px 22px; background:#fff8f8;
          border:1px solid #ffc7ca; border-radius:14px;
          box-shadow:0 6px 18px rgba(31,65,115,.04);
        }
        .panel-heading { display:flex; align-items:center; gap:10px; margin-bottom:12px;
          color:#0d2548; font-size:18px; font-weight:800; }
        .panel-heading.attention { color:#d7353b; margin-bottom:4px; }
        .panel-heading-icon { width:29px; height:29px; display:grid; place-items:center;
          border-radius:9px; background:#eaf2ff; color:#1268f3; font-size:13px; font-weight:900; }
        .panel-heading.attention .panel-heading-icon { background:#ffe5e6; color:#d7353b; }
        .attention-heading-icon svg { display:block; width:17px; height:17px; }
        .attention-count {
          display:inline-flex; align-items:center; justify-content:center; min-width:24px;
          height:24px; padding:0 8px; margin-left:2px; border-radius:999px;
          background:#ffe5e6; color:#d7353b; font-size:12px; font-weight:800;
        }
        .attention-description {
          margin:0 0 14px 39px; color:#6f7f94; font-size:13px; line-height:1.55;
        }
        .attention-list { margin:0; padding:0; list-style:none; }
        .attention-row {
          display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:16px;
          align-items:center; padding:14px 16px; margin-top:10px; background:#fff;
          border:1px solid #ffd8da; border-radius:11px;
        }
        .attention-status {
          display:inline-flex; align-items:center; justify-content:center; min-width:58px;
          height:28px; padding:0 10px; border-radius:999px; background:#fff0f0;
          color:#d7353b; font-size:12px; font-weight:800;
        }
        .attention-main { color:#40526b; font-size:14px; line-height:1.6; }
        .attention-main strong {
          display:block; margin-bottom:2px; color:#0d2548; font-size:15px;
        }
        .attention-action { color:#40526b; }
        .attention-deadline {
          min-width:128px; padding-left:16px; border-left:1px solid #ffe0e1;
          text-align:right; white-space:nowrap;
        }
        .attention-deadline-label {
          display:block; margin-bottom:2px; color:#8a97a8; font-size:11px; font-weight:700;
        }
        .attention-date { color:#d7353b; font-size:13px; font-weight:800; }
        @media (max-width:900px) {
          .attention-row { grid-template-columns:auto minmax(0,1fr); }
          .attention-deadline {
            grid-column:2; padding-left:0; border-left:0; text-align:left;
          }
        }
        [class*="st-key-application_workspace"] { background:#fff; border:1px solid #dbe3ef;
          border-radius:14px; padding:18px 20px 12px; margin:8px 0 24px;
          box-shadow:0 4px 14px rgba(31,65,115,.035); }
        [class*="st-key-application_workspace"] [data-testid="stHorizontalBlock"] { gap:18px; }
        [class*="st-key-application_workspace"] [data-testid="stColumn"]:last-child {
          border-left:1px solid #e4eaf2; padding-left:18px; }
        [class*="st-key-application_workspace"] h3 { margin:0 0 8px; color:#0d2548;
          font-size:16px; font-weight:800; }
        [class*="st-key-application_workspace"] [data-testid="stWidgetLabel"] p {
          color:#53647b; font-size:12px; font-weight:700; }
        [class*="st-key-application_workspace"] [data-baseweb="input"],
        [class*="st-key-application_workspace"] [data-baseweb="select"] > div {
          min-height:38px; background:#f8faff; border-color:#dbe3ef; }
        .schedule-panel { padding:0; margin:0; border:0; border-radius:0; box-shadow:none; }
        .schedule-panel .panel-heading { margin-bottom:14px; }
        .schedule-list { display:grid; gap:9px; }
        .schedule-row { display:grid; grid-template-columns:105px minmax(0,1fr) 20px;
          align-items:center; gap:12px; padding:12px 14px; border:1px solid #e4eaf3;
          border-radius:10px; background:#f8faff; }
        .schedule-date { color:#263a58; font-weight:800; }
        .schedule-title { min-width:0; color:#0d2548; font-size:14px; font-weight:750;
          line-height:1.45; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .schedule-meta { color:#7a899d; font-size:12px; font-weight:500; }
        .schedule-arrow { color:#1268f3; font-size:18px; font-weight:800; text-align:right; }
        .schedule-empty { padding:18px; border:1px dashed #cdd8e8; border-radius:10px;
          color:#718096; background:#f8faff; text-align:center; }
        .application-list-head { display:flex; align-items:center; justify-content:space-between;
          gap:16px; margin:4px 0 10px; }
        .application-list-title { display:flex; align-items:center; gap:9px; margin:0;
          color:#0d2548; font-size:20px; font-weight:850; }
        .application-list-info { display:inline-grid; place-items:center; width:20px; height:20px;
          border:2px solid #1268f3; border-radius:50%; color:#1268f3; font-size:11px; font-weight:900; }
        [class*="st-key-application_list_heading"] [data-testid="stHorizontalBlock"] {
          align-items:center; margin:4px 0 10px; }
        [class*="st-key-application_list_heading"] [data-testid="stColumn"]:last-child {
          display:flex; justify-content:flex-end; }
        [class*="st-key-wbs_view_control"] [role="radiogroup"] { display:flex; gap:4px;
          width:max-content; padding:3px; border-radius:9px; background:#eef2f8; }
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"] { min-width:68px; margin:0; padding:7px 13px;
          justify-content:center; border-radius:7px; color:#52647d; font-size:12px; font-weight:800; }
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"][data-selected="true"] {
          background:#1268f3; color:#fff; box-shadow:0 2px 6px rgba(18,104,243,.18); }
        [class*="st-key-wbs_view_control"] [data-testid="stRadioOption"] > div > div > div:first-child {
          display:none; }
        [class*="st-key-wbs_view_control"] [data-testid="stMarkdownContainer"] p { font-size:12px; }
        .application-table-wrap { overflow-x:auto; margin-bottom:28px; background:#fff;
          border:1px solid #dbe3ef; border-radius:12px; box-shadow:0 4px 14px rgba(31,65,115,.035); }
        .application-table { width:max-content; min-width:100%; border-collapse:separate;
          border-spacing:0; table-layout:fixed; }
        .application-table th { padding:12px 10px; background:#f8faff; border-bottom:1px solid #dbe3ef;
          border-right:1px solid #e6ebf2; color:#465a75; font-size:11px; line-height:1.35;
          text-align:left; font-weight:800; }
        .application-table th:last-child { border-right:0; }
        .application-table td { padding:14px 10px; border-bottom:1px solid #e6ebf2;
          border-right:1px solid #edf1f6; color:#263a58; font-size:12px; line-height:1.5;
          vertical-align:middle; }
        .application-table tr:last-child td { border-bottom:0; }
        .application-table td:last-child { border-right:0; }
        .application-table .company-cell { width:150px; }
        .application-table .phase-cell { width:118px; }
        .application-table .route-cell { width:105px; }
        .application-table .next-cell { width:145px; }
        .application-table .status-cell { width:82px; }
        .application-table .wbs-day { width:72px; padding:9px 4px; text-align:center; }
        .application-table.month .wbs-day { width:54px; }
        .wbs-date-head { display:block; color:#40526b; font-size:10px; white-space:nowrap; }
        .wbs-date-head.today { color:#1268f3; font-weight:900; }
        .wbs-event { display:block; position:relative; min-height:42px; padding-top:18px;
          color:#52647d; font-size:9px; line-height:1.25; overflow-wrap:anywhere; }
        .wbs-event::before { content:''; position:absolute; top:4px; left:50%; width:8px; height:8px;
          transform:translateX(-50%); border:3px solid #1268f3; border-radius:50%; background:#fff; }
        .wbs-event.done::before { border-color:#18a36f; background:#18a36f; }
        .wbs-event.overdue { color:#d7353b; font-weight:700; }
        .wbs-event.overdue::before { border-color:#e5484d; }
        .wbs-event.inactive::before { border-color:#b9c5d6; background:#eef2f7; }
        .wbs-event small { display:block; margin-top:2px; color:#8090a5; font-size:8px; font-weight:700; }
        .wbs-event.done small { color:#16885f; }
        .wbs-empty-day { display:block; min-height:42px; }
        .wbs-legend { display:flex; align-items:center; gap:18px; padding:10px 14px;
          border-top:1px solid #e6ebf2; color:#66768d; font-size:10px; }
        .wbs-legend span { display:inline-flex; align-items:center; gap:6px; }
        .legend-dot { width:9px; height:9px; border:3px solid #1268f3; border-radius:50%; background:#fff; }
        .legend-dot.done { border-color:#18a36f; background:#18a36f; }
        .legend-dot.overdue { border-color:#e5484d; }
        .table-company { display:block; color:#0d2548!important; font-size:14px; font-weight:850;
          text-decoration:none!important; }
        .table-job { display:block; margin-top:2px; color:#708097; font-size:10px; }
        .table-phase { display:inline-block; padding:5px 8px; border-radius:7px;
          background:#eaf2ff; color:#1268f3; font-weight:800; }
        .table-next { font-weight:750; }
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
        .detail-hero {display:grid;grid-template-columns:1.15fr .8fr 1fr;gap:0;background:#fff;
          border:1px solid #dbe3ef;border-radius:14px;margin:14px 0 22px;overflow:hidden}
        .detail-hero>div{padding:24px;border-right:1px solid #e6ebf2}.detail-hero>div:last-child{border:0}
        .company-row{display:flex;gap:14px;align-items:center}.company-logo{width:58px;height:58px;border-radius:50%;
          background:linear-gradient(145deg,#eaf2ff,#f7f9ff);display:grid;place-items:center;color:#1268f3;font-size:28px;font-weight:900}
        .detail-company{font-size:21px;font-weight:850}.detail-role{margin-top:7px;color:#52647d}.detail-label{font-size:12px;color:#75849a;font-weight:750}
        .detail-value{margin-top:9px;font-weight:800}.phase-pill{display:inline-flex;padding:7px 13px;border:1px solid #98bcff;
          border-radius:8px;background:#f1f6ff;color:#1268f3;font-weight:800}.hero-timeline{display:flex;margin-top:20px}
        .hero-step{flex:1;text-align:center;font-size:11px;color:#66768d;position:relative}.hero-step:before{content:'';display:block;
          width:11px;height:11px;border-radius:50%;border:3px solid #b9c7dc;background:#fff;margin:0 auto 7px;position:relative;z-index:2}
        .hero-step:not(:last-child):after{content:'';position:absolute;height:2px;background:#dbe3ef;top:6px;left:55%;right:-45%}
        .hero-step.done:before,.hero-step.current:before{border-color:#1268f3}.hero-step.done:before{background:#1268f3}
        .hero-step.current{color:#1268f3;font-weight:800}
        .section-number{display:inline-grid;place-items:center;width:25px;height:25px;border:2px solid #1268f3;border-radius:50%;
          color:#1268f3;font-size:12px;margin-right:8px}.action-panel{border-color:#ffd3d5;background:#fffafa}.action-row{display:flex;
          justify-content:space-between;align-items:center;padding:15px;border:1px solid #ffd7d9;border-radius:10px;background:#fff}
        .detail-grid{display:grid;grid-template-columns:1fr 1.45fr 1fr;gap:14px}.status-card{background:#fff;border:1px solid #dbe3ef;
          border-radius:12px;padding:18px}.status-card h4{margin:0 0 14px}.detail-timeline{border-left:2px solid #dce5f2;margin-left:10px;padding-left:24px}
        .activity-row{position:relative;padding:10px 0;border-bottom:1px solid #edf1f6}.activity-row:before{content:'';position:absolute;
          width:9px;height:9px;border-radius:50%;background:#9db2d1;left:-30px;top:16px}.activity-date{color:#708097;font-size:12px}
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
                anchor = anchor_by_focus.get(focus, "")
                anchor_suffix = f"#{anchor}" if anchor else ""
                html += (
                    f'<a class="summary-link{selected_class}" '
                    f'href="?page={escape(page_name)}&amp;focus={escape(focus)}{anchor_suffix}">'
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
    st.markdown(
        '<div class="application-focus-context">'
        f'<strong>{escape(label)}の{count}{escape(unit)}を表示中</strong>'
        '<a href="?page=application_list&amp;focus=all">絞り込みを解除</a>'
        '</div>',
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
            '<li class="attention-row">'
            '<span class="attention-status">要対応</span>'
            '<div class="attention-main">'
            f'<strong>{escape(company_name)}</strong>'
            f'<span class="attention-action">{escape(action_name)}</span>'
            '</div>'
            '<div class="attention-deadline">'
            '<span class="attention-deadline-label">期限</span>'
            f'<span class="attention-date">{escape(deadline)}</span>'
            '</div>'
            '</li>'
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
    rows = []
    for item in items[:6]:
        view, milestone = item["view"], item["milestone"]
        company_name = view["job"].company_name
        rows.append(
            '<div class="schedule-row">'
            f'<div class="schedule-date">{escape(_display_milestone_date(milestone.scheduled_date))}</div>'
            f'<div class="schedule-title">{escape(company_name)}：{escape(_milestone_title(milestone))}'
            f'<div class="schedule-meta">{escape(milestone.milestone_type)}</div></div>'
            '<div class="schedule-arrow">›</div>'
            '</div>'
        )
    content = (
        f'<div class="schedule-list">{"".join(rows)}</div>'
        if rows else
        '<div class="schedule-empty">直近1週間の予定はありません。</div>'
    )
    st.markdown(
        '<section class="panel schedule-panel">'
        '<div class="panel-heading"><span class="panel-heading-icon">予</span>'
        '<span>直近1週間の予定</span></div>'
        f'{content}</section>',
        unsafe_allow_html=True,
    )


def render_application_list_page(focus: str = "") -> None:
    render_job_navigation("application_list")
    _inject_css()
    sync_applications_from_decisions()
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
    query_focus = str(
        st.query_params.get("focus", "")
    ).strip()
    selected_focus = (
        query_focus
        if query_focus in focus_id_map
        else ""
    )
    _summary_cards([
        ("応募準備", summary["preparation"], "preparation", "社", "preparation"),
        ("選考中", summary["active"], "active", "社", "active"),
        ("近日予定", summary["upcoming"], "upcoming", "件", "upcoming"),
        ("対応が必要", summary["attention"], "alert", "件", "attention"),
    ], page_name="application_list")
    st.markdown(
        '<span id="application-attention" class="application-anchor"></span>',
        unsafe_allow_html=True,
    )
    if selected_focus == "attention":
        _render_focus_context(
            selected_focus,
            summary["attention"],
        )
    _render_attention_panel(summary["attention_items"])

    st.markdown(
        '<span id="application-upcoming" class="application-anchor"></span>',
        unsafe_allow_html=True,
    )
    if selected_focus == "upcoming":
        _render_focus_context(
            selected_focus,
            summary["upcoming"],
        )
    with st.container(key="application_workspace"):
        left, right = st.columns([1.4, 1])
        with left:
            _render_upcoming_panel(summary["upcoming_items"])
        with right:
            st.subheader("表示条件")
            query = st.text_input("会社名・求人名で検索", key="app_query")
            phase_filters = list(dict.fromkeys([*PHASE_CATEGORIES, *PHASE_OPTIONS]))
            phase_filter = st.selectbox("現在フェーズ", ["すべて", *phase_filters], key="app_phase")
            routes = sorted({v["application"].actual_route or "未設定" for v in all_views})
            route_filter = st.selectbox("応募経路", ["すべて", *routes], key="app_route")
            response_filter = st.selectbox(
                "対応状態", ["すべて", "対応が必要", "近日予定", "通常"], key="app_response_status",
            )
            sort_order = st.selectbox(
                "並び替え",
                ["対応が必要な順", "次回予定が近い順", "最終更新が新しい順",
                 "最終更新が古い順", "会社名順", "現在フェーズ順"],
                key="app_sort_order",
            )
            include_closed = st.checkbox("終了した応募も表示", value=False)

    views = []
    for view in all_views:
        app, job = view["application"], view["job"]
        if not include_closed and app.status != "active": continue
        if selected_focus and app.id not in focus_id_map[selected_focus]: continue
        if query and query.lower() not in f"{job.company_name} {job.job_title}".lower(): continue
        if phase_filter != "すべて":
            if phase_filter in PHASE_CATEGORIES and app.phase_category != phase_filter: continue
            if phase_filter not in PHASE_CATEGORIES and app.current_phase != phase_filter: continue
        if route_filter != "すべて" and (app.actual_route or "未設定") != route_filter: continue
        response_status = _application_response_status(view)
        if response_filter != "すべて" and response_status != response_filter: continue
        views.append(view)
    views = _sort_application_views(views, sort_order)
    st.markdown(
        '<span id="application-company-list" class="application-anchor"></span>',
        unsafe_allow_html=True,
    )
    if selected_focus in {"preparation", "active"}:
        _render_focus_context(
            selected_focus,
            len(views),
        )
    requested_wbs_view = str(st.query_params.get("wbs_view", "week"))
    initial_wbs_label = "月表示" if requested_wbs_view == "month" else "週表示"
    with st.container(key="application_list_heading"):
        heading_col, switch_col = st.columns([1, 0.32])
        with heading_col:
            st.markdown(
                '<div class="application-list-head"><h2 class="application-list-title">'
                f'応募企業一覧（{len(views)}社）<span class="application-list-info">i</span>'
                '</h2></div>', unsafe_allow_html=True,
            )
        with switch_col:
            selected_wbs_label = st.radio(
                "WBS表示期間", ["週表示", "月表示"],
                index=0 if initial_wbs_label == "週表示" else 1,
                horizontal=True, label_visibility="collapsed", key="wbs_view_control",
            )
    wbs_view = "month" if selected_wbs_label == "月表示" else "week"
    if not views:
        st.info("条件に一致する応募企業はありません。求人確認画面で「応募する」を保存すると、ここへ自動追加されます。")
    else:
        _render_application_table(views, wbs_view)


def _wbs_period(view_mode: str, today: date) -> list[date]:
    if view_mode == "month":
        last_day = calendar.monthrange(today.year, today.month)[1]
        return [date(today.year, today.month, day) for day in range(1, last_day + 1)]
    monday = today - timedelta(days=today.weekday())
    return [monday + timedelta(days=offset) for offset in range(7)]


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


def _render_application_table(views: list[dict], view_mode: str) -> None:
    today = date.today()
    period = _wbs_period(view_mode, today)
    weekdays = "月火水木金土日"
    date_headers = "".join(
        '<th class="wbs-day"><span class="wbs-date-head '
        f'{"today" if day == today else ""}">{day.month}/{day.day} {weekdays[day.weekday()]}</span></th>'
        for day in period
    )
    rows = []
    for view in views:
        app, job = view["application"], view["job"]
        next_m = view["next_milestone"]
        if next_m:
            next_text = f'{_display_milestone_date(next_m.scheduled_date)}<br>{escape(_milestone_title(next_m))}'
        else:
            next_text = "未登録"

        events_by_date: dict[date, list[str]] = {}
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
            title = escape(_milestone_title(milestone))
            planned_html = f'<span class="wbs-event {css_class}">{title}<small>予定</small></span>'
            events_by_date.setdefault(scheduled, []).append(planned_html)
            if milestone.status == "completed" and milestone.completed_at:
                try:
                    completed_date = datetime.fromisoformat(milestone.completed_at).date()
                except ValueError:
                    completed_date = scheduled
                actual_html = f'<span class="wbs-event done">{title}<small>実績</small></span>'
                events_by_date.setdefault(completed_date, []).append(actual_html)
        timeline_cells = "".join(
            f'<td class="wbs-day">{"".join(events_by_date.get(day, [])) or "<span class=\"wbs-empty-day\"></span>"}</td>'
            for day in period
        )

        rows.append(
            '<tr>'
            '<td class="company-cell">'
            f'<a class="table-company" href="?page=job_detail&amp;job_id={app.job_id}">{escape(job.company_name)}</a>'
            f'<span class="table-job">{escape(job.job_title or "求人名未登録")}</span></td>'
            f'<td class="phase-cell"><span class="table-phase">{escape(app.current_phase)}</span></td>'
            f'<td class="route-cell">{escape(app.actual_route or "未設定")}</td>'
            f'<td class="next-cell"><span class="table-next">{next_text}</span>'
            f'<a class="table-detail-link" href="?page=application_detail&amp;application_id={app.id}">応募詳細を開く →</a></td>'
            f'<td class="status-cell">{escape(_application_response_status(view))}</td>'
            f'{timeline_cells}'
            '</tr>'
        )

    st.markdown(
        f'<div class="application-table-wrap"><table class="application-table {view_mode}">'
        '<thead><tr><th class="company-cell">会社名／求人名</th>'
        '<th class="phase-cell">現在フェーズ</th><th class="route-cell">応募経路</th>'
        '<th class="next-cell">次の予定・期限</th><th class="status-cell">対応状態</th>'
        f'{date_headers}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        '<div class="wbs-legend"><span><i class="legend-dot done"></i>完了（実績）</span>'
        '<span><i class="legend-dot"></i>予定</span><span><i class="legend-dot overdue"></i>期限超過・要対応</span></div></div>',
        unsafe_allow_html=True,
    )


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
        st.success("選考状況を保存しました。")
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
                st.success("予定を登録しました。")
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
                            st.success("元の予定を延期として残し、新しい予定を作成しました。")
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
                            st.success("予定を中止しました。履歴は保持されます。")
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
                        st.success("誤って登録した予定を削除しました。")
                        st.rerun()
    st.subheader("活動履歴")
    with st.expander("活動を手動で追加"):
        activity_title = st.text_input("活動内容", key="activity_title")
        activity_detail = st.text_area("詳細", key="activity_detail")
        if st.button("活動を追加") and activity_title:
            add_manual_activity(app.id, activity_title, activity_detail, datetime.now().isoformat(timespec="minutes")); st.rerun()
    for activity in detail["activities"]:
        st.markdown(f'**{escape(activity.title)}**　{escape(activity.occurred_at)}  \n{escape(activity.detail)}')


# UIイメージに合わせた応募詳細。上の実装は既存操作を参照できるよう残し、公開関数をこちらで更新する。
def render_application_detail_page() -> None:
    render_job_navigation("application_list")
    _inject_css()
    application_id = int(st.query_params.get("application_id", "0") or 0)
    detail = load_application_detail(application_id)
    if not detail:
        st.error("応募情報が見つかりません。")
        return
    app, job = detail["application"], detail["job"]
    pending = [m for m in detail["milestones"] if m.status == "pending"]
    next_m = min(pending, key=lambda m: m.scheduled_date or "9999-12-31", default=None)
    overdue = [m for m in pending if is_milestone_overdue(m, date.today())]
    st.markdown('<div class="application-page-head"><h1>応募詳細</h1></div>', unsafe_allow_html=True)
    top_left, top_right = st.columns([1, 1])
    top_left.markdown('<a href="?page=application_list">← 一覧に戻る</a>', unsafe_allow_html=True)
    with top_right:
        _, edit_col, prep_col = st.columns([1, .55, .9])
        edit_col.button("編集", use_container_width=True, key="show_detail_edit")
        prep_col.page_link("app.py", label="＋ 選考準備", query_params={"page":"selection_preparation","application_id":app.id}, use_container_width=True)
    next_text = "予定未登録"
    if next_m:
        next_text = f"{next_m.title or next_m.milestone_type}　{_display_milestone_date(next_m.scheduled_date)} {next_m.start_time}"
    st.markdown(f'''<section class="detail-hero">
      <div><div class="company-row"><div class="company-logo">M</div><div><div class="detail-company">{escape(job.company_name)}</div>
      <div class="detail-role">{escape(job.job_title or "求人名未登録")}</div><div class="detail-role">応募経路：{escape(app.actual_route or "未設定")}</div></div></div></div>
      <div><div class="detail-label">現在フェーズ</div><div class="detail-value"><span class="phase-pill">{escape(app.current_phase)}</span></div>
      <div class="detail-label" style="margin-top:22px">応募日</div><div class="detail-value">{escape(app.application_date or "未登録")}</div></div>
      <div><div class="detail-label">次の予定</div><div class="detail-value">{escape(next_text)}</div>
      <div class="hero-timeline"><div class="hero-step done">応募</div><div class="hero-step done">書類選考</div><div class="hero-step current">面接</div><div class="hero-step">最終面接</div><div class="hero-step">内定</div></div></div>
    </section>''', unsafe_allow_html=True)

    if overdue:
        rows = ''.join(f'<div class="action-row"><div><b>⚠ {escape(m.title or m.milestone_type)}の更新が必要です</b><br><small>期限：{escape(m.scheduled_date or "未定")}</small></div><span class="phase-pill">対応する</span></div>' for m in overdue[:3])
        st.markdown(f'<section class="panel action-panel"><h3><span class="section-number">1</span>対応が必要（{len(overdue)}件）</h3>{rows}</section>', unsafe_allow_html=True)

    st.markdown('<h3><span class="section-number">2</span>選考状況を更新</h3>', unsafe_allow_html=True)
    with st.container(border=True):
        left, middle, right = st.columns([1, 1.25, 1])
        with left:
            st.markdown("**現在フェーズ**")
            st.markdown(f'<span class="phase-pill">{escape(app.current_phase)}</span>', unsafe_allow_html=True)
            st.caption(f"次の予定：{next_text}")
        with middle:
            st.markdown("**選考の進捗を更新**")
            phase = st.selectbox("新しいフェーズ", PHASE_OPTIONS, index=PHASE_OPTIONS.index(app.current_phase) if app.current_phase in PHASE_OPTIONS else 0, label_visibility="collapsed")
            if st.button("選考状況を保存", type="primary", use_container_width=True):
                app.current_phase = phase
                update_application_data(app)
                st.rerun()
        with right:
            st.markdown("**結果が判明した場合**")
            result = st.selectbox("選考結果", RESULT_OPTIONS, index=RESULT_OPTIONS.index(app.selection_result) if app.selection_result in RESULT_OPTIONS else 0, label_visibility="collapsed")
            if st.button("選考結果を登録", use_container_width=True):
                app.selection_result = result
                update_application_data(app)
                st.rerun()

    st.markdown('<h3><span class="section-number">3</span>予定・マイルストーン</h3>', unsafe_allow_html=True)
    with st.expander("＋ 予定を追加", expanded=not detail["milestones"]):
        a, b, c = st.columns(3)
        kind = a.selectbox("種類", MILESTONE_TYPES)
        title = b.text_input("予定名", placeholder="例：一次面接")
        d = c.date_input("日付", value=date.today())
        if st.button("予定を登録", type="primary"):
            add_milestone_data(ApplicationMilestone(application_id=app.id, milestone_type=kind, title=title.strip(), scheduled_date=d.isoformat()))
            st.rerun()
    for milestone in detail["milestones"]:
        with st.container(border=True):
            info, action = st.columns([4, 1])
            info.markdown(f"**{milestone.title or milestone.milestone_type}**　{milestone.scheduled_date or '日付未定'}")
            info.caption(f"{milestone.milestone_type}・{milestone_status_label(milestone.status)}")
            if milestone.status == "pending" and action.button("完了にする", key=f"new_complete_{milestone.id}", use_container_width=True):
                complete_milestone(milestone); st.rerun()

    st.markdown('<h3><span class="section-number">4</span>最近の活動履歴</h3>', unsafe_allow_html=True)
    with st.expander("＋ 活動を追加"):
        activity_title = st.text_input("活動内容", key="new_activity_title")
        activity_detail = st.text_area("詳細", key="new_activity_detail")
        if st.button("活動を追加", key="new_activity_add") and activity_title:
            add_manual_activity(app.id, activity_title, activity_detail, datetime.now().isoformat(timespec="minutes")); st.rerun()
    rows = ''.join(f'<div class="activity-row"><span class="activity-date">{escape(a.occurred_at)}</span><br><b>{escape(a.title)}</b>　{escape(a.detail)}</div>' for a in detail["activities"][:8])
    st.markdown(f'<div class="panel"><div class="detail-timeline">{rows or "活動履歴はまだありません。"}</div></div>', unsafe_allow_html=True)


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
    completed = sum(item.is_completed for item in items)
    rate = round(completed / len(items) * 100) if items else 0
    active_tab = str(st.query_params.get("prep_tab", "selection"))
    if active_tab not in {"selection", "company", "common"}:
        active_tab = "selection"
    scope_labels = {"selection": "選考別準備", "company": "企業別準備", "common": "共通準備"}
    visible = items if active_tab == "selection" else [item for item in items if item.scope == active_tab]
    visible = sorted(visible, key=lambda item: (item.sort_order, item.id))
    next_date = next((m.scheduled_date for m in detail["milestones"] if m.status == "pending"), "日程未定")

    st.markdown(
        f'<a class="prep-action" href="?page=application_detail&amp;application_id={app.id}">← 応募詳細に戻る</a>',
        unsafe_allow_html=True,
    )
    st.markdown(f'''<div class="prep-head"><div>
      <h1 class="prep-page-title">選考準備 <span class="phase-pill">{escape(selection_type)}</span></h1>
      <div class="prep-company">{escape(job.company_name)}　/　{escape(job.job_title or "求人名未登録")}</div></div>
      <div class="prep-meta"><div class="progress-track"><div class="progress-fill" style="width:{rate}%"></div></div>
      <b>{rate}%</b><span>{completed} / {len(items)} 完了</span></div></div>
      <div class="prep-actions"><a class="prep-action" href="#free-theme">＋ テーマを追加</a>
      <a class="prep-action" href="?page=selection_preparation&amp;application_id={app.id}&amp;prep_tab=common">▣ 共通準備からコピー</a></div>
      <nav class="prep-tabs">''' + ''.join(
        f'<a class="prep-tab {"active" if key == active_tab else ""}" href="?page=selection_preparation&amp;application_id={app.id}&amp;prep_tab={key}">{label}</a>'
        for key, label in scope_labels.items()
      ) + '</nav>', unsafe_allow_html=True)

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
