"""AIを再実行せず、処理中だけ保存結果の変化を監視する。"""
import streamlit as st

from database.connection import get_connection
from database.access_control import require_user_id
from services.current_user_service import get_current_user_id
from services.job_evaluation_service import load_job_match_evaluations
from services.job_matching_auto_evaluation_service import enqueue_stale_job_evaluations


def evaluation_snapshot():
    user_id = require_user_id(get_current_user_id())
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT e.job_id, e.evaluation_status, e.is_stale, e.evaluated_at
            FROM user_job_match_evaluations e
            JOIN user_jobs j ON j.id = e.job_id AND j.user_id = e.user_id
            WHERE e.user_id = ? AND e.deleted_at IS NULL AND j.deleted_at IS NULL
            ORDER BY e.job_id""", (user_id,),
        ).fetchall()
        return tuple((r['job_id'], r['evaluation_status'], bool(r['is_stale']),
                      str(r['evaluated_at'] or '')) for r in rows)
    finally:
        connection.close()


def has_pending(snapshot):
    return any(status in {'queued', 'running'} or (stale and status != 'failed')
               for _, status, stale, _ in snapshot)


def result_signature(snapshot):
    # queued → runningだけでは画面全体を再描画しない。
    return tuple((job, 'pending' if status in {'queued', 'running'} else status,
                  stale if status not in {'queued', 'running'} else False, evaluated)
                 for job, status, stale, evaluated in snapshot)


def render_evaluation_progress():
    # 画面を開いた時だけルール更新と未処理の変更を確認する。
    evaluations = load_job_match_evaluations()
    initial = tuple((job_id, e.evaluation_status, e.is_stale, str(e.evaluated_at or ''))
                    for job_id, e in sorted(evaluations.items()))
    if not has_pending(initial):
        return evaluations
    if any(e.is_stale and e.evaluation_status not in {'queued', 'running', 'failed'}
           for e in evaluations.values()):
        enqueue_stale_job_evaluations()
        initial = evaluation_snapshot()
    baseline = result_signature(initial)

    @st.fragment(run_every=3)
    def watch():
        latest = evaluation_snapshot()
        if result_signature(latest) != baseline or not has_pending(latest):
            st.rerun()
        st.info('AI評価を更新中です。前回の結果がある場合は表示を続け、完了すると自動で切り替わります。')

    watch()
    return evaluations
