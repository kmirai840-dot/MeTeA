"""Responsive schedule presentation using the already-loaded company snapshot."""
from datetime import date
from html import escape

SCHEDULE_RESPONSIVE_CSS = """
.application-table .wbs-event:not(.done):not(.inactive) .timeline-event-label {font-size:12px;font-weight:750;line-height:1.4;}
.application-table .wbs-event.done {background:transparent;font-size:10px;font-weight:400;}
.application-table .wbs-event.done .timeline-event-label {font-size:10px;font-weight:400;color:#68788c;line-height:1.4;}
.application-table .wbs-event.done .timeline-state-icon {width:13px;height:13px;flex-basis:13px;opacity:.7;}
.application-table.two_weeks .wbs-event:not(.done):not(.inactive) .timeline-event-label {font-size:10px;}
.application-table.two_weeks .wbs-event.done .timeline-event-label {font-size:9px;}
.application-table.month .timeline-event-label {display:none;}
.schedule-mobile {display:none;}
@media(max-width:767px) {
  .application-table-wrap, .st-key-application_schedule_period_control, .st-key-wbs_view_control {display:none!important;}
  .schedule-mobile {display:grid;gap:14px;width:100%;min-width:0;box-sizing:border-box;}
  .schedule-mobile *, .schedule-mobile *::before {box-sizing:border-box;}
  .schedule-mobile-company {min-width:0;padding:16px;background:#fff;border:1px solid #d9e3f0;border-radius:12px;}
  .schedule-mobile-company h3 {font-size:16px!important;line-height:1.5;margin:0 0 6px;overflow-wrap:anywhere;}
  .schedule-mobile-company a {color:#0d2548;text-decoration:none;}
  .schedule-mobile-meta {font-size:12px;color:#52647d;line-height:1.6;overflow-wrap:anywhere;}
  .schedule-mobile-events {list-style:none;margin:10px 0;padding:0;}
  .schedule-mobile-event {padding:12px 0;border-top:1px solid #e7edf5;overflow-wrap:anywhere;}
  .schedule-mobile-event strong {display:block;font-size:14px;line-height:1.6;color:#0d2548;}
  .schedule-mobile-date {display:block;font-size:14px;line-height:1.6;font-weight:700;color:#1268f3;}
  .schedule-mobile-state {display:block;font-size:12px;line-height:1.6;color:#52647d;}
  .schedule-mobile-event.overdue {border-left:3px solid #d7353b;padding-left:10px;background:#fff7f7;}
  .schedule-mobile-event.overdue .schedule-mobile-date {color:#b4232b;}
  .schedule-mobile-event.completed strong, .schedule-mobile-event.completed .schedule-mobile-date,
  .schedule-mobile-event.cancelled strong, .schedule-mobile-event.postponed strong {color:#68788c;font-size:12px;font-weight:400;}
  .schedule-mobile-actions {display:grid;grid-template-columns:1fr 1fr;gap:8px;}
  .schedule-mobile-actions .schedule-row-action {min-height:44px;white-space:normal;font-size:13px;padding:10px 6px;}
}
"""


def mobile_schedule_html(views, today=None):
    today = today or date.today()
    companies = []
    for view in views:
        app, job = view['application'], view['job']
        events = []
        def sort_key(m):
            return (m.status != 'pending', str(m.scheduled_date or '9999-12-31'), m.id or 0)
        for m in sorted(view['milestones'], key=sort_key):
            day = None
            try:
                day = date.fromisoformat(str(m.scheduled_date)) if m.scheduled_date else None
            except ValueError:
                pass
            deadline = f'{day.year}/{day.month}/{day.day}（{"月火水木金土日"[day.weekday()]}）' if day else '日程未定'
            state = {'completed':'完了', 'cancelled':'取消', 'postponed':'延期'}.get(m.status, '未完了')
            css = m.status
            if m.status == 'pending' and day:
                days = (day-today).days
                if days < 0:
                    state, css = f'期限超過・{abs(days)}日経過', 'overdue'
                else:
                    state = '未完了・本日期限' if days == 0 else f'未完了・あと{days}日'
            title = m.title or m.detail_name or m.milestone_type or '予定'
            events.append(f'<li class="schedule-mobile-event {escape(css)}"><span class="schedule-mobile-date">{escape(deadline)}</span><strong>{escape(title)}</strong><span class="schedule-mobile-state">{escape(state)}</span></li>')
        content = '<ul class="schedule-mobile-events">'+''.join(events)+'</ul>' if events else '<p class="schedule-mobile-meta">予定は未登録です。</p>'
        companies.append(
            f'<article class="schedule-mobile-company"><h3><a target="_self" href="?page=job_detail&amp;job_id={app.job_id}">{escape(job.company_name)}</a></h3>'
            f'<div class="schedule-mobile-meta">{escape(app.current_phase or "応募準備")}｜応募経路：{escape(app.actual_route or "未設定")}</div>'
            f'{content}<div class="schedule-mobile-actions">'
            f'<button type="button" class="schedule-row-action primary" data-schedule-application="{app.id}" aria-label="{escape(job.company_name)}の予定と選考結果を更新">予定・結果を更新</button>'
            f'<a class="schedule-row-action" target="_self" href="?page=selection_preparation&amp;application_id={app.id}">選考準備</a></div></article>')
    return '<section class="schedule-mobile" aria-label="会社別の予定一覧">'+''.join(companies)+'</section>'
