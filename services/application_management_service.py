"""応募管理と就職活動ダッシュボードの業務ロジック。"""

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta

from database.repositories.application_repository import (
    add_phase_history, get_activities, get_application, get_application_by_job_route,
    get_applications, get_milestones, get_preparations, save_activity, save_application, save_milestone,
    save_preparation,
    soft_delete_milestone,
)
from models import ApplicationActivity, ApplicationMilestone, ApplicationPreparation, ApplicationRecord
from services.current_user_service import get_current_user_id
from services.job_evaluation_service import load_job_application_decisions
from services.job_service import load_job, load_jobs, load_job_sources


ACTIVE_DECISIONS = {"応募する", "他経路から応募する"}
PHASE_OPTIONS = (
    "応募準備", "応募依頼済／応募予定", "応募済", "書類選考中",
    "適性検査調整中", "適性検査予定", "適性検査結果待ち",
    "カジュアル面談調整中", "カジュアル面談予定", "カジュアル面談結果待ち",
    "一次面接調整中", "一次面接予定", "一次面接結果待ち",
    "二次面接調整中", "二次面接予定", "二次面接結果待ち",
    "最終面接調整中", "最終面接予定", "最終面接結果待ち",
    "次回選考調整中", "オファー面談調整中", "オファー面談予定",
    "条件確認中", "内定", "保留", "不合格", "辞退", "見送り", "選考終了",
)
RESULT_OPTIONS = ("", "未確定", "通過", "不合格", "辞退", "内定", "保留")
MILESTONE_TYPES = (
    "応募", "書類提出", "適性検査", "カジュアル面談", "一次面接", "二次面接",
    "最終面接", "その他の面接・選考", "オファー面談", "条件面談", "回答期限", "その他",
)

PREPARATION_THEMES = (
    ("selection", "self_intro", "自己紹介・職務経歴", "これまでの経歴や担当業務、実績を簡潔に説明します。"),
    ("selection", "career_reason", "転職理由・キャリアの一貫性", "転職を考えた理由と今後の方向性を整理します。"),
    ("company", "motivation", "志望動機・企業との接続", "求人・企業と自分の経験がつながる点を具体化します。"),
    ("common", "career_plan", "転職軸・キャリアプラン", "転職活動の軸と将来的に実現したいことを整理します。"),
    ("selection", "achievement", "実績・強みを示すエピソード", "成果を出した経験をSTARで整理します。"),
    ("common", "strengths", "強み・弱み・人物面", "長所・短所、価値観やモチベーションを整理します。"),
    ("company", "conditions", "条件・選考状況", "希望条件や選考状況、入社可能時期を整理します。"),
    ("company", "questions", "逆質問・確認事項", "企業理解を深める質問や確認事項を準備します。"),
)
TERMINAL_CATEGORIES = {"内定", "終了"}
MILESTONE_STATUS_PENDING = "pending"
MILESTONE_STATUS_COMPLETED = "completed"
MILESTONE_STATUS_POSTPONED = "postponed"
MILESTONE_STATUS_CANCELLED = "cancelled"
MILESTONE_STATUS_LABELS = {
    MILESTONE_STATUS_PENDING: "未完了",
    MILESTONE_STATUS_COMPLETED: "完了",
    MILESTONE_STATUS_POSTPONED: "延期",
    MILESTONE_STATUS_CANCELLED: "中止",
}


class ApplicationManagementError(ValueError):
    """応募管理の操作を完了できない場合のエラー。"""


def milestone_status_label(status: str) -> str:
    return MILESTONE_STATUS_LABELS.get(status, status or "未設定")


def _parse_scheduled_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ApplicationManagementError("日付はYYYY-MM-DD形式で入力してください。") from error


def is_milestone_overdue(milestone: ApplicationMilestone, today: date | None = None) -> bool:
    scheduled = _parse_scheduled_date(milestone.scheduled_date)
    return bool(
        milestone.status == MILESTONE_STATUS_PENDING
        and scheduled
        and scheduled <= (today or date.today())
    )


def is_milestone_upcoming(milestone: ApplicationMilestone, today: date | None = None) -> bool:
    base_date = today or date.today()
    scheduled = _parse_scheduled_date(milestone.scheduled_date)
    return bool(
        milestone.status == MILESTONE_STATUS_PENDING
        and scheduled
        and base_date < scheduled <= base_date + timedelta(days=7)
    )


def resolved_phase_category(phase: str, result: str = "") -> str:
    if result == "内定":
        return "内定"
    if result in {"不合格", "辞退"}:
        return "終了"
    if result == "保留":
        return "保留"
    return phase_category(phase)



def phase_category(phase: str) -> str:
    if phase == "内定": return "内定"
    if phase in {"不合格", "辞退", "見送り", "選考終了"}: return "終了"
    if phase == "保留": return "保留"
    if "オファー" in phase or "条件" in phase: return "オファー・条件確認"
    if "面接" in phase or "面談" in phase: return "面接"
    if "適性" in phase: return "適性検査"
    if "書類" in phase: return "書類選考"
    if phase in {"応募済", "応募依頼済／応募予定"}: return "応募"
    return "応募準備"


def _default_route(job_id: int) -> str:
    sources = load_job_sources(job_id)
    if sources:
        primary = next((source for _, source in sources if source.is_primary), sources[0][1])
        return primary.source_name or primary.source_type or "直接応募"
    job = load_job(job_id)
    return (job.source_name if job else "") or "直接応募"


def sync_applications_from_decisions() -> int:
    created = 0
    for job_id, decision in load_job_application_decisions().items():
        if decision.decision_status not in ACTIVE_DECISIONS:
            continue
        route = _default_route(job_id)
        before = get_application_by_job_route(get_current_user_id(), job_id, route)
        application_id = ensure_application_from_decision(
            job_id, decision.decision_status, decision.next_action,
            decision.action_deadline, route,
        )
        if not before and application_id:
            created += 1
    return created


def ensure_application_from_decision(job_id: int, decision_status: str, next_action: str = "",
                                     action_deadline: str | None = None, route: str = "") -> int | None:
    if decision_status not in ACTIVE_DECISIONS:
        return None
    user_id = get_current_user_id()
    actual_route = route or _default_route(job_id)
    existing = get_application_by_job_route(user_id, job_id, actual_route)
    if existing:
        return existing.id
    application = ApplicationRecord(user_id=user_id, job_id=job_id, actual_route=actual_route)
    application_id = save_application(application)
    add_phase_history(application_id, application.current_phase, application.phase_category)
    save_activity(ApplicationActivity(
        application_id=application_id, activity_type="application_created",
        occurred_at=datetime.now().isoformat(timespec="minutes"), title="応募管理へ追加",
        detail=f"応募判断「{decision_status}」から応募管理へ追加しました。", is_automatic=True,
    ))
    if next_action or action_deadline:
        add_milestone_data(ApplicationMilestone(
            application_id=application_id, milestone_type="その他",
            title=next_action or "次のアクション", schedule_kind="deadline",
            scheduled_date=action_deadline, status="pending",
        ))
    return application_id


def load_application_views(include_closed: bool = True) -> list[dict]:
    user_id = get_current_user_id()
    result = []
    for application in get_applications(user_id, include_closed):
        job = load_job(application.job_id)
        if not job:
            continue
        milestones = get_milestones(application.id)
        pending = [m for m in milestones if m.status == "pending"]
        next_milestone = min(pending, key=lambda m: (m.scheduled_date or "9999-12-31", m.id), default=None)
        result.append({"application": application, "job": job, "milestones": milestones,
                       "next_milestone": next_milestone})
    return result


def load_application_detail(application_id: int) -> dict | None:
    application = get_application(get_current_user_id(), application_id)
    if not application:
        return None
    job = load_job(application.job_id)
    return {"application": application, "job": job,
            "milestones": get_milestones(application_id),
            "activities": get_activities(application_id=application_id)}


def update_application_data(application: ApplicationRecord) -> None:
    previous = get_application(application.user_id, application.id)
    application.phase_category = resolved_phase_category(
        application.current_phase,
        application.selection_result,
    )
    application.status = (
        "closed"
        if application.phase_category in TERMINAL_CATEGORIES
        else "active"
    )
    save_application(application)

    phase_changed = (
        not previous
        or (previous.current_phase, previous.selection_result)
        != (application.current_phase, application.selection_result)
    )
    if phase_changed:
        add_phase_history(
            application.id,
            application.current_phase,
            application.phase_category,
            application.selection_result,
        )
        previous_phase = previous.current_phase if previous else "未設定"
        previous_result = previous.selection_result if previous else "未設定"
        save_activity(ApplicationActivity(
            application_id=application.id,
            activity_type="phase_changed",
            occurred_at=datetime.now().isoformat(timespec="minutes"),
            title="選考状況を更新",
            detail=(
                f"現在フェーズを「{previous_phase}」から"
                f"「{application.current_phase}」へ、選考結果を"
                f"「{previous_result or '未確定'}」から"
                f"「{application.selection_result or '未確定'}」へ更新しました。"
            ),
            is_automatic=True,
        ))

    if previous and previous.notes != application.notes:
        save_activity(ApplicationActivity(
            application_id=application.id,
            activity_type="notes_updated",
            occurred_at=datetime.now().isoformat(timespec="minutes"),
            title="応募メモを更新",
            detail="応募企業のメモを更新しました。",
            is_automatic=True,
        ))


def add_milestone_data(milestone: ApplicationMilestone) -> int:
    if milestone.application_id <= 0:
        raise ApplicationManagementError("応募企業が正しく指定されていません。")
    if not (milestone.title or milestone.milestone_type):
        raise ApplicationManagementError("予定の内容を入力してください。")
    _parse_scheduled_date(milestone.scheduled_date)
    milestone.status = MILESTONE_STATUS_PENDING
    milestone.completed_at = None
    milestone.cancelled_at = None
    milestone_id = save_milestone(milestone)
    date_text = f"（{milestone.scheduled_date}）" if milestone.scheduled_date else ""
    save_activity(ApplicationActivity(
        application_id=milestone.application_id,
        activity_type="milestone_created",
        occurred_at=datetime.now().isoformat(timespec="minutes"),
        title="予定を追加",
        detail=f"{milestone.title or milestone.milestone_type}{date_text}を追加しました。",
        is_automatic=True,
    ))
    return milestone_id


def complete_milestone(milestone: ApplicationMilestone) -> None:
    if milestone.status != MILESTONE_STATUS_PENDING:
        raise ApplicationManagementError("未完了の予定だけを完了できます。")
    milestone.status = MILESTONE_STATUS_COMPLETED
    milestone.completed_at = datetime.now().isoformat(timespec="minutes")
    save_milestone(milestone)
    save_activity(ApplicationActivity(
        application_id=milestone.application_id,
        activity_type="milestone_completed",
        occurred_at=milestone.completed_at,
        title="予定を完了",
        detail=f"{milestone.title or milestone.milestone_type}を完了しました。",
        is_automatic=True,
    ))


def postpone_milestone(
    milestone: ApplicationMilestone,
    new_scheduled_date: str,
    reason: str = "",
) -> int:
    if milestone.status != MILESTONE_STATUS_PENDING:
        raise ApplicationManagementError("未完了の予定だけを延期できます。")
    _parse_scheduled_date(new_scheduled_date)
    if new_scheduled_date == milestone.scheduled_date:
        raise ApplicationManagementError("変更後の日付を指定してください。")

    original_date = milestone.scheduled_date or "日付未設定"
    milestone.status = MILESTONE_STATUS_POSTPONED
    if reason.strip():
        milestone.memo = "\n".join(
            value for value in (milestone.memo, f"延期理由：{reason.strip()}") if value
        )
    save_milestone(milestone)

    replacement = ApplicationMilestone(
        application_id=milestone.application_id,
        milestone_type=milestone.milestone_type,
        title=milestone.title,
        schedule_kind=milestone.schedule_kind,
        scheduled_date=new_scheduled_date,
        detail_name=milestone.detail_name,
        start_time=milestone.start_time,
        end_time=milestone.end_time,
        status=MILESTONE_STATUS_PENDING,
        rescheduled_from_id=milestone.id,
        memo=milestone.memo,
    )
    replacement_id = save_milestone(replacement)
    reason_text = f" 理由：{reason.strip()}" if reason.strip() else ""
    save_activity(ApplicationActivity(
        application_id=milestone.application_id,
        activity_type="milestone_postponed",
        occurred_at=datetime.now().isoformat(timespec="minutes"),
        title="予定を延期",
        detail=(
            f"{milestone.title or milestone.milestone_type}を"
            f"{original_date}から{new_scheduled_date}へ延期しました。{reason_text}"
        ),
        is_automatic=True,
    ))
    return replacement_id


def cancel_milestone(milestone: ApplicationMilestone, reason: str = "") -> None:
    if milestone.status != MILESTONE_STATUS_PENDING:
        raise ApplicationManagementError("未完了の予定だけを中止できます。")
    milestone.status = MILESTONE_STATUS_CANCELLED
    milestone.cancelled_at = datetime.now().isoformat(timespec="minutes")
    if reason.strip():
        milestone.memo = "\n".join(
            value for value in (milestone.memo, f"中止理由：{reason.strip()}") if value
        )
    save_milestone(milestone)
    reason_text = f" 理由：{reason.strip()}" if reason.strip() else ""
    save_activity(ApplicationActivity(
        application_id=milestone.application_id,
        activity_type="milestone_cancelled",
        occurred_at=milestone.cancelled_at,
        title="予定を中止",
        detail=f"{milestone.title or milestone.milestone_type}を中止しました。{reason_text}",
        is_automatic=True,
    ))


def delete_milestone_data(milestone: ApplicationMilestone) -> None:
    """誤登録した予定を表示対象から削除する。"""

    if milestone.id <= 0:
        raise ApplicationManagementError("削除する予定が正しく指定されていません。")
    if not soft_delete_milestone(milestone.id):
        raise ApplicationManagementError("予定が見つからないか、すでに削除されています。")
    save_activity(ApplicationActivity(
        application_id=milestone.application_id,
        activity_type="milestone_deleted",
        occurred_at=datetime.now().isoformat(timespec="minutes"),
        title="予定を削除",
        detail=f"{milestone.title or milestone.milestone_type}を予定一覧から削除しました。",
        is_automatic=True,
    ))


def add_manual_activity(application_id: int, title: str, detail: str, occurred_at: str) -> None:
    save_activity(ApplicationActivity(application_id=application_id, activity_type="manual",
        occurred_at=occurred_at, title=title, detail=detail, is_automatic=False))


def load_preparation_items(application_id: int, selection_type: str) -> list[ApplicationPreparation]:
    existing = get_preparations(application_id)
    existing_keys = {(item.scope, item.theme_key) for item in existing}
    for order, (scope, key, title, description) in enumerate(PREPARATION_THEMES):
        if (scope, key) not in existing_keys:
            save_preparation(ApplicationPreparation(
                application_id=application_id, scope=scope, selection_type=selection_type,
                theme_key=key, title=title, description=description, sort_order=order,
            ))
    return get_preparations(application_id)


def save_preparation_item(item: ApplicationPreparation) -> None:
    item.is_completed = bool(item.is_completed or item.content.strip())
    save_preparation(item)


def add_custom_preparation(application_id: int, selection_type: str, title: str) -> None:
    key = f"custom_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    save_preparation(ApplicationPreparation(
        application_id=application_id, scope="selection", selection_type=selection_type,
        theme_key=key, title=title.strip(), description="自由に追加した準備テーマです。",
        is_custom=True, sort_order=1000,
    ))


def dashboard_summary() -> dict:
    views = load_application_views(True)
    applications = [view["application"] for view in views]
    categories = Counter(a.phase_category for a in applications)
    detailed = Counter(a.current_phase for a in applications)
    applied = len([a for a in applications if a.phase_category != "応募準備"])
    interview = len([a for a in applications if a.phase_category in {"面接", "オファー・条件確認", "内定"}])
    offers = len([a for a in applications if a.phase_category == "内定" or a.selection_result == "内定"])
    document_known = len([a for a in applications if a.phase_category not in {"応募準備", "応募", "書類選考"} or a.selection_result in {"通過", "不合格"}])
    document_pass = len([a for a in applications if a.phase_category in {"適性検査", "面接", "オファー・条件確認", "内定"}])
    route_rows = defaultdict(lambda: {"applications": 0, "document_known": 0, "document_pass": 0, "interview": 0, "offers": 0})
    for a in applications:
        row = route_rows[a.actual_route or "未設定"]
        row["applications"] += 1
        if a.phase_category not in {"応募準備", "応募", "書類選考"} or a.selection_result in {"通過", "不合格"}: row["document_known"] += 1
        if a.phase_category in {"適性検査", "面接", "オファー・条件確認", "内定"}: row["document_pass"] += 1
        if a.phase_category in {"面接", "オファー・条件確認", "内定"}: row["interview"] += 1
        if a.phase_category == "内定" or a.selection_result == "内定": row["offers"] += 1
    return {"total": len(applications), "applied": applied, "interview": interview, "offers": offers,
            "categories": categories, "detailed": detailed,
            "document_known": document_known, "document_pass": document_pass,
            "document_pass_rate": round(document_pass / document_known * 100) if document_known else None,
            "interview_rate": round(interview / document_known * 100) if document_known else None,
            "offer_rate": round(offers / applied * 100) if applied else None,
            "routes": dict(route_rows)}


def operational_summary(views: list[dict]) -> dict:
    today = date.today()
    upcoming, attention = [], []
    current_views = [
        view for view in views
        if view["application"].status == "active"
    ]
    for view in current_views:
        for milestone in view["milestones"]:
            if milestone.status != MILESTONE_STATUS_PENDING:
                continue
            try:
                scheduled = _parse_scheduled_date(milestone.scheduled_date)
            except ApplicationManagementError:
                continue
            if scheduled is None:
                continue
            item = {"view": view, "milestone": milestone, "date": scheduled}
            if is_milestone_overdue(milestone, today):
                attention.append(item)
            elif is_milestone_upcoming(milestone, today):
                upcoming.append(item)

    preparation = [
        view for view in current_views
        if view["application"].phase_category == "応募準備"
    ]
    active = [
        view for view in current_views
        if view["application"].phase_category
        not in {*TERMINAL_CATEGORIES, "応募準備"}
    ]
    offers = [
        view for view in current_views
        if view["application"].phase_category == "内定"
    ]
    return {
        "preparation": len(preparation),
        "active": len(active),
        "upcoming": len(upcoming),
        "attention": len(attention),
        "offers": len(offers),
        "preparation_application_ids": {
            view["application"].id for view in preparation
        },
        "active_application_ids": {
            view["application"].id for view in active
        },
        "upcoming_application_ids": {
            item["view"]["application"].id for item in upcoming
        },
        "attention_application_ids": {
            item["view"]["application"].id for item in attention
        },
        "upcoming_items": sorted(upcoming, key=lambda x: x["date"]),
        "attention_items": sorted(attention, key=lambda x: x["date"]),
    }
