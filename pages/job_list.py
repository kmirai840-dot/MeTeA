"""登録済み求人の一覧画面。"""

import streamlit as st

from pages.job_registration import (
    JOB_FORM_RETURN_PAGE_KEY,
    load_job_for_edit,
)
from services.job_service import (
    delete_job_data,
    load_jobs,
)


JOB_DELETE_CONFIRM_KEY = (
    "job_list_delete_confirm_id"
)


def move_to_page(
    page_name: str | None,
) -> None:
    """指定した画面へ移動する。"""

    if page_name is None:
        st.query_params.clear()
    else:
        st.query_params["page"] = page_name

    st.rerun()


def render_empty_state() -> None:
    """求人が未登録の場合の案内を表示する。"""

    with st.container(border=True):
        st.info(
            "登録済みの求人はありません。"
            "気になる求人を登録してみましょう。"
        )

        if st.button(
            "求人を登録する",
            key="empty_job_registration",
            type="primary",
            width="stretch",
        ):
            move_to_page("job_registration")


def render_delete_confirmation(
    job_id: int,
    company_name: str,
    job_name: str,
) -> None:
    """求人を削除する前の確認を表示する。"""

    pending_job_id = st.session_state.get(
        JOB_DELETE_CONFIRM_KEY
    )

    if pending_job_id != job_id:
        return

    st.warning(
        f"「{company_name}／{job_name}」を"
        "求人一覧から削除しますか？"
    )

    st.caption(
        "削除した求人は通常の一覧には"
        "表示されなくなります。"
    )

    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button(
            "削除する",
            key=f"confirm_delete_job_{job_id}",
            type="primary",
            width="stretch",
        ):
            deleted = delete_job_data(
                job_id
            )

            if deleted:
                st.session_state[
                    JOB_DELETE_CONFIRM_KEY
                ] = None

                st.toast(
                    "求人を削除しました。"
                )

                st.rerun()

            else:
                st.error(
                    "求人を削除できませんでした。"
                )

    with cancel_col:
        if st.button(
            "キャンセル",
            key=f"cancel_delete_job_{job_id}",
            width="stretch",
        ):
            st.session_state[
                JOB_DELETE_CONFIRM_KEY
            ] = None

            st.rerun()


def render_job_card(
    job_id: int,
    job,
) -> None:
    """求人1件分の概要と操作を表示する。"""

    with st.container(border=True):
        title_col, id_col = st.columns(
            [4, 1]
        )

        with title_col:
            st.markdown(
                f"### {job.company_name}"
            )

            job_name = (
                job.job_title
                or job.occupation
                or "求人名未入力"
            )

            st.markdown(job_name)

        with id_col:
            st.caption(
                f"求人ID：{job_id}"
            )

        detail_col1, detail_col2 = st.columns(2)

        with detail_col1:
            st.caption("募集ポジション")

            st.write(
                job.occupation
                or "未入力"
            )

        with detail_col2:
            st.caption("紹介経路")

            source_text = job.source_name

            if (
                job.source_type
                and job.source_name
            ):
                source_text = (
                    f"{job.source_type}／"
                    f"{job.source_name}"
                )

            st.write(
                source_text
                or "未入力"
            )

        if job.job_summary:
            st.caption("仕事内容")

            summary = job.job_summary

            if len(summary) > 120:
                summary = (
                    summary[:120]
                    + "…"
                )

            st.write(summary)

        detail_col, edit_col, delete_col = (
            st.columns(3)
        )

        with detail_col:
            if st.button(
                "詳細",
                key=f"detail_job_{job_id}",
                width="stretch",
            ):
                st.query_params["page"] = (
                    "job_detail"
                )

                st.query_params["job_id"] = (
                    str(job_id)
                )

                st.rerun()

        with edit_col:
            if st.button(
                "編集",
                key=f"edit_job_{job_id}",
                width="stretch",
            ):
                st.session_state[
                    JOB_FORM_RETURN_PAGE_KEY
                ] = "job_list"

                load_job_for_edit(
                    job_id
                )

                move_to_page(
                    "job_registration"
                )

        with delete_col:
            if st.button(
                "削除",
                key=f"delete_job_{job_id}",
                width="stretch",
            ):
                st.session_state[
                    JOB_DELETE_CONFIRM_KEY
                ] = job_id

                st.rerun()

        render_delete_confirmation(
            job_id=job_id,
            company_name=(
                job.company_name
                or "会社名未入力"
            ),
            job_name=job_name,
        )


def show_page() -> None:
    """求人一覧画面を表示する。"""

    if (
        JOB_DELETE_CONFIRM_KEY
        not in st.session_state
    ):
        st.session_state[
            JOB_DELETE_CONFIRM_KEY
        ] = None

    header_col, register_col = st.columns(
        [4, 1]
    )

    with header_col:
        st.title("求人一覧")

        st.caption(
            "登録した求人を確認・管理します。"
        )

    with register_col:
        if st.button(
            "＋ 求人を登録する",
            key="job_list_registration",
            type="primary",
            width="stretch",
        ):
            move_to_page(
                "job_registration"
            )

    jobs = load_jobs()

    if not jobs:
        render_empty_state()

    else:
        st.caption(
            f"{len(jobs)}件の求人を登録しています。"
        )

        for job_id, job in jobs:
            render_job_card(
                job_id,
                job,
            )

    st.divider()

    if st.button(
        "トップへ戻る",
        key="job_list_back_home",
    ):
        move_to_page(None)