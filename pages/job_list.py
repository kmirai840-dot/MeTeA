"""登録済み求人の一覧画面。"""

import streamlit as st

from pages.job_registration import (
    JOB_FORM_RETURN_PAGE_KEY,
    load_job_for_edit,
    start_new_job_registration,
)
from services.job_service import (
    delete_job_data,
    load_job_sources,
    load_jobs,
)


JOB_DELETE_CONFIRM_KEY = (
    "job_list_delete_confirm_id"
)

JOB_COMPARE_SELECTED_KEY = (
    "job_compare_selected_ids"
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
            start_new_job_registration()
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
    """求人1件分をリスト形式で表示する。"""

    sources = load_job_sources(job_id)

    job_name = (
        job.job_title
        or job.occupation
        or "求人名未入力"
    )

    # 紹介経路を一覧表示用に整形
    if sources:
        source_names = []

        for _, source in sources:
            source_name = source.source_name or "名称未入力"

            if (
                source.source_type
                and source.source_name
            ):
                source_name = (
                    f"{source.source_type}／"
                    f"{source.source_name}"
                )

            source_names.append(source_name)

        source_text = "、".join(source_names)

    else:
        source_text = "未入力"

    # 1求人＝1行
    with st.container(border=True):
        
        selected = st.checkbox(
            "比較対象に選択",
            key=f"compare_job_{job_id}",
        )

        (
            company_col,
            position_col,
            location_col,
            salary_col,
            source_col,
            action_col,
        ) = st.columns(
            [2.1, 1.8, 1.4, 1.5, 2.4, 2.0]
        )

        with company_col:
            st.caption("会社名")
            st.write(
                job.company_name
                or "会社名未入力"
            )

            st.caption(
                f"求人ID：{job_id}"
            )

        with position_col:
            st.caption("募集ポジション")
            st.write(
                job.occupation
                or "未入力"
            )

            st.caption("求人名")
            st.write(job_name)

        with location_col:
            st.caption("勤務地")

            location_parts = [
                value
                for value in (
                    job.prefecture,
                    job.municipality,
                )
                if value
            ]

            st.write(
                "".join(location_parts)
                or "未入力"
            )

        with salary_col:
            st.caption("想定年収")

            if (
                job.expected_salary_min
                or job.expected_salary_max
            ):
                salary_min = (
                    job.expected_salary_min
                    or "―"
                )
                salary_max = (
                    job.expected_salary_max
                    or "―"
                )

                st.write(
                    f"{salary_min} ～ {salary_max}"
                )

            elif job.annual_salary:
                st.write(job.annual_salary)

            else:
                st.write("未入力")

        with source_col:
            st.caption("紹介経路")

            if sources:
                for _, source in sources:
                    source_text = (
                        source.source_name
                        or "名称未入力"
                    )

                    if (
                        source.source_type
                        and source.source_name
                    ):
                        source_text = (
                            f"{source.source_type}／"
                            f"{source.source_name}"
                        )

                    st.write(
                        f"・{source_text}"
                    )

                if len(sources) > 1:
                    st.caption(
                        f"計 {len(sources)}件"
                    )
            else:
                st.write("未入力")

        with action_col:
            st.caption("操作")

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

    if (
        JOB_COMPARE_SELECTED_KEY
        not in st.session_state
    ):
        st.session_state[
            JOB_COMPARE_SELECTED_KEY
        ] = []

    jobs = load_jobs()

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
            start_new_job_registration()

            move_to_page(
                "job_registration"
            )

    summary_col1, summary_col2, summary_col3, summary_col4 = (
        st.columns(4)
    )

    with summary_col1:
        st.metric(
            "登録求人",
            f"{len(jobs)}件",
        )

    with summary_col2:
        st.metric(
            "未判断",
            "―",
        )

    with summary_col3:
        st.metric(
            "期限超過",
            "―",
        )

    with summary_col4:
        st.metric(
            "次のアクション未設定",
            "―",
        )

    search_keyword = st.text_input(
        "求人を検索",
        placeholder="会社名・求人名・職種・キーワードで検索",
        key="job_list_search_keyword",
    )

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    prefectures = sorted(
        {
            job.prefecture
            for _, job in jobs
            if job.prefecture
        }
    )

    industries = sorted(
        {
            job.industry
            for _, job in jobs
            if job.industry
        }
    )

    source_names = sorted(
        {
            source.source_name
            for job_id, _ in jobs
            for _, source in load_job_sources(job_id)
            if source.source_name
        }
    )

    with filter_col1:
        selected_prefecture = st.selectbox(
            "勤務地",
            ["すべて"] + prefectures,
            key="job_list_filter_prefecture",
        )

    with filter_col2:
        selected_industry = st.selectbox(
            "業種",
            ["すべて"] + industries,
            key="job_list_filter_industry",
        )

    with filter_col3:
        selected_source_name = st.selectbox(
            "紹介元",
            ["すべて"] + source_names,
            key="job_list_filter_source_name",
        )

    filtered_jobs = jobs

    if search_keyword.strip():
        keyword = search_keyword.strip().lower()

        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if keyword in (
                f"{job.company_name} "
                f"{job.job_title} "
                f"{job.occupation} "
                f"{job.industry} "
                f"{job.prefecture} "
                f"{job.municipality}"
            ).lower()
        ]

    if selected_prefecture != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if job.prefecture == selected_prefecture
        ]

    if selected_industry != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if job.industry == selected_industry
        ]

    if selected_source_name != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if any(
                source.source_name
                == selected_source_name
                for _, source
                in load_job_sources(job_id)
            )
        ]

    if not jobs:
        render_empty_state()

    elif not filtered_jobs:
        st.info(
            "検索条件に一致する求人はありません。"
        )

    else:
        st.caption(
            f"{len(filtered_jobs)}件の求人を表示しています。"
        )

        for job_id, job in filtered_jobs:
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