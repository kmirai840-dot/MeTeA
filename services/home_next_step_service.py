"""保存状態からホームの次の一歩を決める。AIやデータ更新は行わない。"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from html import escape
from constants.work_values import WORK_STYLE_QUESTIONS
from database.repositories.home_progress_repository import get_home_progress
from services.current_user_service import get_current_user_id

STEPS = (
    ('basic_info', '基本情報'), ('hope_conditions', '希望条件'),
    ('work_values', '価値観'), ('job_hunting_axis', '就活の軸'),
    ('career', '職務経歴・スキル'),
)

@dataclass(frozen=True)
class NextStep:
    reason: str
    message: str
    detail: str
    label: str
    href: str


def choose_next_step(progress: dict, views: list[dict], today: date | None = None) -> NextStep:
    today = today or datetime.now(ZoneInfo("Asia/Tokyo")).date()
    active = [v for v in views if v['application'].status == 'active']
    due = []
    for view in active:
        for milestone in view['milestones']:
            if milestone.status != 'pending' or not milestone.scheduled_date:
                continue
            try:
                scheduled = date.fromisoformat(milestone.scheduled_date)
            except ValueError:
                continue
            if scheduled <= today + timedelta(days=7):
                due.append((scheduled, view['application'].id, milestone.id or 0, view, milestone))
    if due:
        scheduled, _, _, view, milestone = min(due, key=lambda x: x[:3])
        timing = '予定日を過ぎた未完了の対応があります。' if scheduled < today else ('今日の予定があります。' if scheduled == today else '7日以内の予定があります。')
        title = milestone.title or milestone.detail_name or milestone.milestone_type
        return NextStep('deadline', timing, f"{view['job'].company_name}：{title}（{scheduled.month}/{scheduled.day}）を確認しましょう。", '予定・対応を確認する', f"?page=application_list&application_id={view['application'].id}")

    counts = progress['counts']
    complete = {key: counts.get(key, 0) > 0 for key, _ in STEPS}
    complete['hope_conditions'] = complete['hope_conditions'] and all(counts.get('hope_' + kind, 0) for kind in ('occupation', 'location', 'employment_type'))
    complete['work_values'] = all(counts.get('rank_' + kind, 0) >= 3 for kind in ('important_value', 'rewarding_scene', 'strength_environment')) and all(counts.get('style_' + q['question_type'], 0) for q in WORK_STYLE_QUESTIONS)
    labels = dict(STEPS)
    for key in progress.get('drafts', []):
        if key in labels:
            return NextStep('draft', f"{labels[key]}の一時保存があります。", '保存した続きから入力内容を確認しましょう。', f'{labels[key]}の入力を再開する', f'?page={key}')
    # 応募を開始している人は、自己理解の不足より実際の対応を優先する。
    if active:
        view = min(active, key=lambda v: (v['application'].phase_category != '応募準備', v['application'].id))
        app = view['application']
        waiting = '結果待ち' in app.current_phase
        return NextStep('application', '応募・選考が進行中です。', f"{view['job'].company_name}の{app.current_phase}を確認し、" + ('結果が届いたら記録しましょう。' if waiting else '次の対応や予定を整理しましょう。'), '応募状況を確認する', f'?page=application_list&application_id={app.id}')
    if counts.get('application_intents', 0):
        return NextStep('application_intent', '応募したい求人が記録されています。', '応募条件や応募経路を確認して、応募準備を進めましょう。', '応募予定の求人を確認する', '?page=job_list')
    for key, label in STEPS:
        if not complete[key]:
            return NextStep('profile', f'{label}の登録内容を整えましょう。', '保存状況に合わせて、続きのステップをご案内しています。', f'{label}を確認・入力する', f'?page={key}')
    if not counts.get('jobs', 0):
        return NextStep('register_job', '自分の情報が登録されています。', '気になる求人を登録して、希望条件との相性を確認しましょう。', '求人を登録する', '?page=job_registration')
    if counts.get('undecided_jobs', 0):
        return NextStep('compare', '応募判断が未確定の求人があります。', '登録した求人を確認して、応募するかどうか整理しましょう。', '求人を確認・比較する', '?page=job_list')
    if counts.get('applications', 0):
        return NextStep('review', 'これまでの応募・選考を振り返りましょう。', '活動の結果を確認し、次の求人選びに役立てましょう。', '活動を振り返る', '?page=application_dashboard')
    return NextStep('more_jobs', '登録した求人の応募判断が記録されています。', '次に気になる求人を登録して、選択肢を広げてみましょう。', '求人を追加する', '?page=job_registration')


def load_next_step(views: list[dict]) -> NextStep:
    return choose_next_step(get_home_progress(get_current_user_id()), views)


def render_next_step_html(step: NextStep) -> str:
    return (f'<p>{escape(step.message)}</p><p>{escape(step.detail)}</p>'
            f'<a class="metea-primary-button" href="{escape(step.href, quote=True)}">'
            f'{escape(step.label)} <span>→</span></a>')
