"""求人詳細の評価・確認操作を、ページ内だけで更新する。"""
import streamlit as st
from pathlib import Path
from time import monotonic
from streamlit.components.v2 import component
from database.operation import database_operation
from services.job_evaluation_service import load_job_match_evaluations
from services.job_confirmation_service import load_confirmation_records
from services.job_matching_auto_evaluation_service import enqueue_job_evaluation
from ui.page_execution import rerun_current_page

_poll = component('metea_job_evaluation_poll', js=Path(__file__).with_name('job_evaluation_poll.js').read_text(encoding='utf-8'))


def refresh_confirmation_area(job_id):
    st.session_state[f'confirmation_refresh_{job_id}'] = True
    rerun_current_page()


def pending(evaluation):
    return bool(evaluation and (evaluation.evaluation_status in {'queued', 'running'}
                or (evaluation.is_stale and evaluation.evaluation_status != 'failed')))


@database_operation
def load_area_updates(job_id):
    records = load_confirmation_records(job_id)
    return dict(evaluations=load_job_match_evaluations(), confirmation_records=records,
                resolutions={row['item_key']:row['status'] for row in records})


def render_evaluation_area(job_id, snapshot, render_score, render_detail):
    # ページの通常描画時に作成する、当該ブラウザ専用のスナップショット。
    current = dict(snapshot)
    detail_snapshot = dict(snapshot)

    @st.fragment
    def area():
        dirty = st.session_state.pop(f'confirmation_refresh_{job_id}', False)
        evaluation = current['evaluations'].get(job_id)
        if dirty or pending(evaluation):
            current.update(load_area_updates(job_id))
            evaluation = current['evaluations'].get(job_id)
        if evaluation and evaluation.is_stale and evaluation.evaluation_status not in {'queued', 'running', 'failed'}:
            enqueue_job_evaluation(job_id)
        with st.container(key=f'evaluation_progress_notice_{job_id}'):
            if pending(evaluation):
                st.info('確認内容は保存されています。AI評価を更新中です。完了するとこの欄へ反映します。')
        _poll(key=f'job_evaluation_poll_{job_id}', data={'jobId': job_id, 'pending': pending(evaluation), 'sequence': monotonic()},
              on_poll_change=lambda: None, height=0)
        render_score(job_id=job_id, job=current['job'], evaluations=current['evaluations'], snapshot=current)


    # 詳細フォームは別fragment。スコアのポーリングでは再実行しない。
    @st.fragment
    def detail():
        saved = st.session_state.pop(f'confirmation_detail_saved_{job_id}', None)
        if saved is not None:
            for key in st.session_state.pop(f'confirmation_reset_keys_{job_id}', []):
                st.session_state.pop(key, None)
            records = load_confirmation_records(job_id)
            detail_snapshot.update(confirmation_records=records,
                                   resolutions={r['item_key']: r['status'] for r in records})
            # 送信済みの操作チェックを次回の保存へ持ち越さない。
            for key in list(st.session_state):
                if (key.startswith(f'batch_{job_id}_') and key.endswith('_action')) or key.startswith(f'batch_restore_{job_id}_'):
                    del st.session_state[key]
        render_detail(job_id, evaluations=detail_snapshot['evaluations'], snapshot=detail_snapshot)
        if saved is not None:
            st.success(f'{saved}項目を保存し、確認欄に反映しました。' if saved else '保存済みの内容を確認欄に反映しました。')
            notify_evaluation_saved(job_id)

    with st.container(key='local_job_evaluation'):
        area()
        st.divider()
        detail()


def notify_evaluation_saved(job_id):
    st.session_state[f'confirmation_refresh_{job_id}'] = True
    # 保存完了の通知だけを描画。フォームの再生成は要求しない。
    st.html(f'<span data-metea-saved="{job_id}" data-sequence="{monotonic()}" style="display:none"></span>')


def refresh_saved_confirmation_details(job_id, count):
    st.session_state[f'confirmation_detail_saved_{job_id}'] = count
    rerun_current_page()
