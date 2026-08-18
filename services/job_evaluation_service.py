"""求人のAI評価と応募判断に関するService。"""

from database.repositories.job_evaluation_repository import (
    get_job_application_decisions,
    get_job_match_evaluations,
    save_job_application_decision,
    save_job_match_evaluation,
)
from models import (
    JobApplicationDecision,
    JobMatchEvaluation,
)
from services.current_user_service import (
    get_current_user_id,
)
from services.job_matching_ai_service import PROMPT_VERSION
from services.job_matching_rule_service import EVALUATION_RULE_VERSION
from database.repositories.job_evaluation_repository import mark_job_match_evaluation_stale
from database.repositories.job_evaluation_repository import mark_job_match_evaluation_result_seen


APPLICATION_DECISION_OPTIONS = (
    "応募する",
    "条件を確認して応募",
    "保留",
    "応募しない",
    "他経路から応募する",
)


def is_job_match_evaluation_ready(
    evaluation: JobMatchEvaluation | None,
) -> bool:
    """利用者向けのAIマッチング詳細を表示できる完了状態か判定する。"""

    return bool(
        evaluation is not None
        # 現行のバックグラウンド評価は completed を保存する。
        # ready は旧データとの互換性のため、完了状態として引き続き扱う。
        and evaluation.evaluation_status in {"completed", "ready"}
        and not evaluation.is_stale
        and evaluation.overall_score is not None
    )


# ========================================
# AIマッチング評価
# ========================================
def load_job_match_evaluations(
) -> dict[int, JobMatchEvaluation]:
    """現在の利用者に紐づくAI評価を取得する。"""

    user_id = get_current_user_id()
    evaluations = get_job_match_evaluations(user_id)
    version_mismatch_found = False
    for evaluation in evaluations.values():
        if (
            evaluation.rule_version != EVALUATION_RULE_VERSION
            or evaluation.prompt_version != PROMPT_VERSION
        ):
            mark_job_match_evaluation_stale(
                user_id=user_id,
                job_id=evaluation.job_id,
                stale_reason=(
                    "AI評価ルールまたは判定基準が更新されました。"
                ),
            )
            version_mismatch_found = True

    if version_mismatch_found:
        return get_job_match_evaluations(user_id)
    return evaluations


def save_job_match_evaluation_data(
    evaluation: JobMatchEvaluation,
) -> list[str]:
    """AI評価を検証して保存する。"""

    errors = []

    score_fields = (
        (
            evaluation.overall_score,
            "AI総合マッチ度",
        ),
        (
            evaluation.hope_condition_score,
            "希望条件との一致度",
        ),
        (
            evaluation.work_value_score,
            "就活の軸との一致度",
        ),
        (
            evaluation.career_skill_score,
            "職務経歴・スキルとの一致度",
        ),
        (
            evaluation.required_condition_score,
            "必須条件充足率",
        ),
    )

    for score, label in score_fields:
        if score is None:
            continue

        if score < 0 or score > 100:
            errors.append(
                f"{label}は0から100の範囲で入力してください。"
            )

    if errors:
        return errors

    save_job_match_evaluation(
        user_id=get_current_user_id(),
        evaluation=evaluation,
    )

    return []


# ========================================
# 応募判断
# ========================================
def load_job_application_decisions(
) -> dict[int, JobApplicationDecision]:
    """現在の利用者に紐づく応募判断を取得する。"""

    return get_job_application_decisions(
        get_current_user_id()
    )


def save_job_application_decision_data(
    decision: JobApplicationDecision,
) -> list[str]:
    """応募判断を検証して保存する。"""

    if (
        decision.decision_status
        not in APPLICATION_DECISION_OPTIONS
    ):
        return [
            "応募判断を選択してください。"
        ]

    save_job_application_decision(
        user_id=get_current_user_id(),
        decision=decision,
    )

    if decision.decision_status in {
        "応募する",
        "他経路から応募する",
    }:
        from services.application_management_service import (
            ensure_application_from_decision,
        )
        ensure_application_from_decision(
            job_id=decision.job_id,
            decision_status=decision.decision_status,
            next_action=decision.next_action,
            action_deadline=decision.action_deadline,
        )
    return []


def acknowledge_job_match_evaluation_result(job_id: int) -> None:
    """AI評価完了通知を確認済みにする。"""

    mark_job_match_evaluation_result_seen(get_current_user_id(), job_id)
