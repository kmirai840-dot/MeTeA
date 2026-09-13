"""Responsive schedule presentation using the already-loaded company snapshot."""
from datetime import date, datetime
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


CALENDAR_CSS = """
@media(max-width:767px){
.schedule-mobile {gap:12px;}
.mobile-calendar-toolbar {display:flex;align-items:center;justify-content:space-between;gap:4px;}
.mobile-calendar-toolbar button {min-width:40px;min-height:44px;border:1px solid #d9e3f0;border-radius:8px;background:#fff;color:#1268f3;font-size:14px;}
.mobile-calendar-month {font-size:17px;font-weight:750;color:#0d2548;}
.mobile-calendar-grid {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));width:100%;border-top:1px solid #d9e3f0;border-left:1px solid #d9e3f0;background:white;}
.mobile-calendar-weekday {text-align:center;font-size:12px;padding:7px 0;color:#52647d;background:#f4f8ff;border-right:1px solid #d9e3f0;}
.mobile-calendar-day {min-width:0;min-height:86px;padding:3px 1px;border:0;border-right:1px solid #d9e3f0;border-bottom:1px solid #d9e3f0;background:#fff;text-align:left;overflow:hidden;color:#0d2548;}
.mobile-calendar-day[aria-pressed=true] {background:#e8f1ff;box-shadow:inset 0 0 0 2px #1268f3;}
.mobile-calendar-day.outside {background:#f6f8fb;color:#8693a5;}
.mobile-calendar-number {display:block;text-align:center;font-size:12px;line-height:20px;}
.mobile-calendar-day.today .mobile-calendar-number {color:#1268f3;font-weight:800;text-decoration:underline;}
.mobile-calendar-chip {display:block;background:#e8f1ff;color:#0753a5;border-radius:3px;margin-top:2px;font-size:9px;line-height:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.mobile-calendar-chip span {display:block;overflow:hidden;text-overflow:ellipsis;}
.mobile-calendar-chip.completed,.mobile-calendar-chip.cancelled,.mobile-calendar-chip.postponed {background:#f1f3f6;color:#68788c;}
.mobile-calendar-chip.overdue {background:#fff0f0;color:#b4232b;}
.mobile-calendar-more {font-size:9px;color:#52647d;}
.schedule-mobile h3.mobile-calendar-selected {margin:6px 0;font-size:16px;}
.mobile-calendar-event {width:100%;text-align:left;border:1px solid #d9e3f0;border-radius:10px;background:#fff;padding:12px;color:#0d2548;cursor:pointer;}
.mobile-calendar-event strong,.mobile-calendar-event span {display:block;overflow-wrap:anywhere;line-height:1.6;}
.mobile-calendar-event strong {font-size:14px;}
.mobile-calendar-event .mobile-calendar-company {font-size:12px;color:#52647d;}
.mobile-calendar-event.completed {color:#68788c;background:#f8f9fb;}
.mobile-calendar-event.overdue {border-left:3px solid #d7353b;}
.mobile-calendar-events,.mobile-calendar-undated {display:grid;gap:8px;}
.mobile-calendar-event[hidden],.mobile-calendar-empty[hidden] {display:none!important;}
.mobile-calendar-help,.mobile-calendar-empty {font-size:12px;color:#52647d;line-height:1.6;margin:0;}
}
"""
SCHEDULE_RESPONSIVE_CSS += CALENDAR_CSS

from pathlib import Path
from streamlit.components.v2 import component

_calendar = component('metea_schedule_calendar', js=Path(__file__).with_name('schedule_calendar.js').read_text(encoding='utf-8'))

def install_mobile_calendar():
    _calendar(key='metea_schedule_calendar', height=0)


def mobile_schedule_html(views, today=None):
    today = today or date.today()
    events = []
    for view in views:
        app, job = view['application'], view['job']
        for m in view['milestones']:
            day = None
            try:
                day = date.fromisoformat(str(m.scheduled_date)) if m.scheduled_date else None
            except ValueError:
                pass
            date_label = ''
            if m.status == 'completed':
                date_label = '予定日：'
                if m.completed_at:
                    try:
                        day = datetime.fromisoformat(str(m.completed_at)).date()
                        date_label = '完了日：'
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
            company_short = job.company_name.replace('株式会社','').replace('有限会社','')[:6]
            time = (' '+m.start_time+(('〜'+m.end_time) if m.end_time else '')) if m.start_time else ''
            card = (f'<button type="button" class="mobile-calendar-event {escape(css)}" data-event-day="{day.isoformat() if day else ""}" '
                    f'data-state="{escape(css)}" data-company-short="{escape(company_short)}" data-event-title="{escape(title)}" '
                    f'data-calendar-application="{app.id}" aria-label="{escape(job.company_name+"："+title+"を更新")}">'
                    f'<span class="mobile-calendar-company">{escape(job.company_name)}</span><strong>{escape(title)}</strong>'
                    f'<span class="schedule-mobile-date">{escape(date_label+deadline+time)}</span><span class="schedule-mobile-state">{escape(state)}</span></button>')
            events.append((m.status!='pending', str(day or date.max), m.start_time or '', card, day))
    events.sort(key=lambda e:e[:3])
    dated=''.join(e[3] for e in events if e[4])
    undated=''.join(e[3] for e in events if not e[4]) or '<p class="mobile-calendar-help">日程未定の予定はありません。</p>'
    return (f'<section id="metea-mobile-calendar" class="schedule-mobile" aria-label="月間カレンダーと予定一覧" data-today="{today.isoformat()}">'
            '<div class="mobile-calendar-toolbar"><button type="button" data-month-step="-1" aria-label="前の月">‹</button>'
            '<span class="mobile-calendar-month" aria-live="polite"></span><button type="button" data-calendar-today>今日</button>'
            '<button type="button" data-month-step="1" aria-label="次の月">›</button></div>'
            '<div class="mobile-calendar-grid" aria-label="月間カレンダー"></div>'
            '<p class="mobile-calendar-help">日付を選ぶと下に予定を表示します。予定を押すと更新できます。</p>'
            '<h3 class="mobile-calendar-selected" aria-live="polite"></h3><p class="mobile-calendar-empty">この日の予定はありません。</p>'
            f'<div class="mobile-calendar-events">{dated}</div><h3 class="mobile-calendar-selected-undated">日程未定</h3>'
            f'<div class="mobile-calendar-undated">{undated}</div></section>')
