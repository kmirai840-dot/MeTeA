"""登録済み求人の一覧画面。"""

from html import escape

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
from services.job_evaluation_service import (
    APPLICATION_DECISION_OPTIONS,
    load_job_application_decisions,
    load_job_match_evaluations,
)
from services.job_matching_auto_evaluation_service import (
    automatically_refresh_stale_job_evaluations,
)
from services.job_matching_cache_service import (
    load_current_user_stale_job_ids,
)

from pages.job_layout import (
    render_job_navigation,
)

JOB_DELETE_CONFIRM_KEY = (
    "job_list_delete_confirm_id"
)

JOB_COMPARE_SELECTED_KEY = (
    "job_compare_selected_ids"
)

JOB_LIST_PAGE_KEY = (
    "job_list_current_page"
)

JOB_STALE_REFRESH_SIGNATURE_KEY = (
    "job_list_stale_refresh_signature"
)

JOB_LIST_PAGE_SIZE = 20


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


def render_job_table_header() -> None:
    """求人一覧の列見出しを表示する。"""

    (
        company_col,
        position_col,
        location_col,
        salary_col,
        source_col,
        action_col,
    ) = st.columns(
        [2.2, 2.0, 1.4, 1.5, 2.4, 1.5]
    )

    with company_col:
        st.caption("会社名 / 求人ID")

    with position_col:
        st.caption("募集ポジション / 求人名")

    with location_col:
        st.caption("勤務地")

    with salary_col:
        st.caption("想定年収 / AIマッチ度")

    with source_col:
        st.caption("紹介経路 / 応募判断")

    with action_col:
        st.caption("操作")


def render_job_card(
    job_id: int,
    job,
    evaluation,
    decision,
) -> bool:
    """求人1件分をコンパクトな一覧行として表示する。"""

    sources = load_job_sources(job_id)

    job_name = (
        job.job_title
        or job.occupation
        or "求人名未入力"
    )

    company_name = (
        job.company_name
        or "会社名未入力"
    )

    location_parts = [
        value
        for value in (
            job.prefecture,
            job.municipality,
        )
        if value
    ]

    location_text = (
        "".join(location_parts)
        or "未入力"
    )

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

        salary_text = (
            f"{salary_min} ～ {salary_max}"
        )

    elif job.annual_salary:
        salary_text = job.annual_salary

    else:
        salary_text = "未入力"

    if (
        evaluation is not None
        and evaluation.is_stale
    ):
        evaluation_text = "再評価待ち"

    elif (
        evaluation is not None
        and evaluation.overall_score
        is not None
    ):
        evaluation_text = (
            f"{evaluation.overall_score}点"
        )

    else:
        evaluation_text = "未評価"

    if (
        decision is not None
        and decision.decision_status
    ):
        decision_text = (
            decision.decision_status
        )

    else:
        decision_text = "未対応"

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
            [2.2, 2.0, 1.4, 1.5, 2.4, 1.5]
        )

        with company_col:
            company_link_html = (
                '<a class="job-detail-link" '
                f'href="?page=job_detail&job_id={job_id}" '
                'target="_self">'
                f'{escape(company_name)}'
                '</a>'
            )

            st.markdown(
                company_link_html,
                unsafe_allow_html=True,
            )

            st.caption(
                f"求人ID：{job_id}"
            )

        with position_col:
            st.write(
                job.occupation
                or "未入力"
            )

            st.caption(job_name)

        with location_col:
            st.write(location_text)

        with salary_col:
            st.write(salary_text)

            if evaluation_text == "未評価":
                st.caption(
                    "AI：未評価"
                )

            else:
                st.markdown(
                    f"**AI：{evaluation_text}**"
                )

        with source_col:
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
                        f"紹介経路：計{len(sources)}件"
                    )

            else:
                st.write("未入力")

            if decision_text == "未対応":
                st.caption(
                    "応募判断：未対応"
                )

            else:
                st.markdown(
                    f"**応募判断：{decision_text}**"
                )

        with action_col:
            edit_col, delete_col = st.columns(
                2
            )

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
            company_name=company_name,
            job_name=job_name,
        )

    return selected


def get_salary_minimum(
    job,
) -> int:
    """年収下限を並び替え用の数値に変換する。"""

    salary_text = (
        job.expected_salary_min
        or job.annual_salary
        or ""
    )

    number_text = "".join(
        character
        for character in str(salary_text)
        if character.isdigit()
    )

    if not number_text:
        return 0

    try:
        return int(number_text)

    except ValueError:
        return 0


def render_recommendation_candidate(
    rank: int,
    job_id: int,
    job,
    evaluation,
) -> None:
    """AIおすすめ求人のカードを表示する。"""

    job_name = (
        job.job_title
        or job.occupation
        or "求人名未入力"
    )

    with st.container(border=True):
        st.caption(
            f"おすすめ {rank}位"
        )

        st.markdown(
            f"**{job.company_name or '会社名未入力'}**"
        )

        st.caption(job_name)

        st.metric(
            "AI総合マッチ度",
            f"{evaluation.overall_score}点",
        )

        score_col1, score_col2 = st.columns(2)

        with score_col1:
            st.caption("希望条件")

            st.write(
                (
                    f"{evaluation.hope_condition_score}点"
                    if evaluation.hope_condition_score
                    is not None
                    else "未評価"
                )
            )

            st.caption("価値観")

            st.write(
                (
                    f"{evaluation.work_value_score}点"
                    if evaluation.work_value_score
                    is not None
                    else "未評価"
                )
            )

        with score_col2:
            st.caption("職務経歴・スキル")

            st.write(
                (
                    f"{evaluation.career_skill_score}点"
                    if evaluation.career_skill_score
                    is not None
                    else "未評価"
                )
            )

            st.caption("必須条件")

            st.write(
                (
                    f"{evaluation.required_condition_score}点"
                    if evaluation.required_condition_score
                    is not None
                    else "未評価"
                )
            )

        if st.button(
            "詳細を見る",
            key=f"recommendation_detail_{job_id}",
            width="stretch",
        ):
            st.query_params["page"] = (
                "job_detail"
            )

            st.query_params["job_id"] = (
                str(job_id)
            )

            st.rerun()


def show_page() -> None:
    """求人一覧画面を表示する。"""

    render_job_navigation(
        "job_list"
    )

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

    if (
        JOB_LIST_PAGE_KEY
        not in st.session_state
    ):
        st.session_state[
            JOB_LIST_PAGE_KEY
        ] = 1

    stale_job_ids = (
        load_current_user_stale_job_ids()
    )

    stale_signature = tuple(
        stale_job_ids
    )

    previous_stale_signature = (
        st.session_state.get(
            JOB_STALE_REFRESH_SIGNATURE_KEY
        )
    )

    if (
        stale_job_ids
        and previous_stale_signature
        != stale_signature
    ):
        st.session_state[
            JOB_STALE_REFRESH_SIGNATURE_KEY
        ] = stale_signature

        with st.spinner(
            "更新された利用者情報をもとに、"
            "求人のAI評価を更新しています..."
        ):
            (
                refreshed_count,
                remaining_count,
                failed_job_ids,
            ) = (
                automatically_refresh_stale_job_evaluations()
            )

        if refreshed_count > 0:
            st.toast(
                f"{refreshed_count}件のAI評価を"
                "更新しました。"
            )

        if remaining_count > 0:
            st.info(
                f"残り{remaining_count}件の求人は、"
                "続けて自動更新されます。"
            )

        if failed_job_ids:
            st.warning(
                "一部の求人についてAI評価を"
                "更新できませんでした。"
                "求人情報は保存されています。"
            )

    if not stale_job_ids:
        st.session_state[
            JOB_STALE_REFRESH_SIGNATURE_KEY
        ] = ()

    jobs = load_jobs()

    evaluations = (
        load_job_match_evaluations()
    )

    decisions = (
        load_job_application_decisions()
    )

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1380px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e4eaf2;
            border-radius: 12px;
            padding: 16px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff;
            border-color: #dfe6f0;
            border-radius: 12px;
        }

        .stButton > button[kind="primary"] {
            background: #1268f3;
            border-color: #1268f3;
        }
        .job-pending-notice {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            margin: 12px 0 28px;
            padding: 20px 24px;
            background: #fffaf0;
            border: 1px solid #f6c85f;
            border-radius: 12px;
        }

        .job-pending-notice-main {
            display: flex;
            align-items: flex-start;
            gap: 14px;
        }

        .job-pending-notice-icon {
            color: #f59e0b;
            font-size: 26px;
            line-height: 1;
        }

        .job-pending-notice-title {
            margin: 0 0 6px;
            color: #c45a05;
            font-size: 18px;
            font-weight: 800;
        }

        .job-pending-notice-description {
            margin: 0;
            color: #53627a;
            font-size: 14px;
        }

        .job-pending-notice-count {
            min-width: 100px;
            padding-left: 20px;
            color: #c45a05;
            border-left: 1px solid #f6d994;
            text-align: center;
            white-space: nowrap;
        }

        .job-pending-notice-count strong {
            display: block;
            font-size: 28px;
            line-height: 1.2;
        }

        .job-pending-notice-count span {
            font-size: 12px;
        }
                .job-detail-link {
            color: #1268f3 !important;
            font-weight: 700;
            line-height: 1.5;
            text-decoration: none !important;
        }

        .job-detail-link:hover {
            color: #0759d9 !important;
            text-decoration: underline !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    header_col, register_col = st.columns(
        [4, 1]
    )

    with header_col:
        st.title("求人一覧")

        st.caption(
            "登録した求人を管理し、"
            "AIのおすすめや比較結果を確認できます。"
        )

    with register_col:
        if st.button(
            "＋ 求人を登録",
            key="job_list_registration",
            type="primary",
            width="stretch",
        ):
            start_new_job_registration()

            move_to_page(
                "job_registration"
            )

    pending_count = sum(
        1
        for job_id, _ in jobs
        if (
            job_id not in decisions
            or not decisions[
                job_id
            ].decision_status.strip()
        )
    )

    pending_notice_html = (
        '<div class="job-pending-notice">'
        '<div class="job-pending-notice-main">'
        '<div class="job-pending-notice-icon">'
        '♢'
        '</div>'
        '<div>'
        '<p class="job-pending-notice-title">'
        f'応募判断未対応の求人が'
        f'{pending_count}件あります'
        '</p>'
        '<p class="job-pending-notice-description">'
        '求人一覧から内容を確認し、'
        '応募判断を行いましょう。'
        '</p>'
        '</div>'
        '</div>'
        '<div class="job-pending-notice-count">'
        f'<strong>{pending_count}件</strong>'
        '<span>未対応</span>'
        '</div>'
        '</div>'
    )

    st.markdown(
        pending_notice_html,
        unsafe_allow_html=True,
    )

    st.subheader("AIおすすめ求人 TOP3")

    st.caption(
        "AI評価が完了している求人から、"
        "総合マッチ度が高い順に3件表示しています。"
    )

    jobs_by_id = {
        job_id: job
        for job_id, job in jobs
    }

    recommendation_evaluations = sorted(
        (
            evaluation
            for job_id, evaluation
            in evaluations.items()
            if (
                job_id in jobs_by_id
                and not evaluation.is_stale
                and evaluation.overall_score
                is not None
            )
        ),
        key=lambda evaluation: (
            evaluation.overall_score
        ),
        reverse=True,
    )[:3]

    if recommendation_evaluations:
        recommendation_columns = st.columns(
            3
        )

        for index, evaluation in enumerate(
            recommendation_evaluations,
            start=1,
        ):
            job_id = evaluation.job_id
            job = jobs_by_id[job_id]

            with recommendation_columns[index - 1]:
                render_recommendation_candidate(
                    rank=index,
                    job_id=job_id,
                    job=job,
                    evaluation=evaluation,
                )

    else:
        st.info(
            "AI評価済みの求人はまだありません。"
        )

    st.subheader("求人検索・絞り込み")

    search_keyword = st.text_input(
        "求人を検索",
        placeholder="会社名・求人名・職種・キーワードで検索",
        key="job_list_search_keyword",
    )

    (
        filter_col1,
        filter_col2,
        filter_col3,
        decision_filter_col,
        sort_col,
    ) = st.columns(5)

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

    with decision_filter_col:
        selected_decision = st.selectbox(
            "応募判断",
            [
                "すべて",
                "未対応",
                *APPLICATION_DECISION_OPTIONS,
            ],
            key="job_list_filter_decision",
        )

    with sort_col:
        selected_sort = st.selectbox(
            "並び替え",
            [
                "AIおすすめ順",
                "未対応・登録が古い順",
                "登録が新しい順",
                "登録が古い順",
                "年収下限が高い順",
                "会社名順",
            ],
            key="job_list_sort",
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

    if selected_decision == "未対応":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if (
                job_id not in decisions
                or not decisions[
                    job_id
                ].decision_status.strip()
            )
        ]

    elif selected_decision != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if (
                job_id in decisions
                and decisions[
                    job_id
                ].decision_status
                == selected_decision
            )
        ]

    if (
        selected_sort
        == "未対応・登録が古い順"
    ):
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if (
                job_id not in decisions
                or not decisions[
                    job_id
                ].decision_status.strip()
            )
        ]

        filtered_jobs = list(
            reversed(filtered_jobs)
        )

    elif selected_sort == "AIおすすめ順":
        filtered_jobs = sorted(
            filtered_jobs,
            key=lambda item: (
                evaluations[
                    item[0]
                ].overall_score
                if (
                    item[0] in evaluations
                    and not evaluations[
                        item[0]
                    ].is_stale
                    and evaluations[
                        item[0]
                    ].overall_score
                    is not None
                )
                else -1
            ),
            reverse=True,
        )

    elif selected_sort == "登録が古い順":
        filtered_jobs = list(
            reversed(filtered_jobs)
        )

    elif selected_sort == "年収下限が高い順":
        filtered_jobs = sorted(
            filtered_jobs,
            key=lambda item: get_salary_minimum(
                item[1]
            ),
            reverse=True,
        )

    elif selected_sort == "会社名順":
        filtered_jobs = sorted(
            filtered_jobs,
            key=lambda item: (
                item[1].company_name
                or ""
            ).casefold(),
        )

    st.subheader("求人一覧")

    total_job_count = len(
        filtered_jobs
    )

    total_pages = max(
        1,
        (
            total_job_count
            + JOB_LIST_PAGE_SIZE
            - 1
        )
        // JOB_LIST_PAGE_SIZE,
    )

    current_page = st.session_state[
        JOB_LIST_PAGE_KEY
    ]

    current_page = max(
        1,
        min(
            current_page,
            total_pages,
        ),
    )

    st.session_state[
        JOB_LIST_PAGE_KEY
    ] = current_page

    page_start = (
        current_page - 1
    ) * JOB_LIST_PAGE_SIZE

    page_end = (
        page_start
        + JOB_LIST_PAGE_SIZE
    )

    visible_jobs = filtered_jobs[
        page_start:page_end
    ]

    if not jobs:
        render_empty_state()

    elif not filtered_jobs:
        st.info(
            "検索条件に一致する求人はありません。"
        )

    else:
        display_start = page_start + 1

        display_end = min(
            page_end,
            total_job_count,
        )

        st.caption(
            f"全{total_job_count}件中 "
            f"{display_start}～{display_end}件を"
            "表示しています。"
        )

        render_job_table_header()

        for job_id, job in visible_jobs:
            render_job_card(
                job_id=job_id,
                job=job,
                evaluation=(
                    evaluations.get(job_id)
                ),
                decision=(
                    decisions.get(job_id)
                ),
            )

        if total_pages > 1:
            (
                previous_col,
                page_col,
                next_col,
            ) = st.columns(
                [1, 3, 1]
            )

            with previous_col:
                if st.button(
                    "← 前へ",
                    key="job_list_previous_page",
                    width="stretch",
                    disabled=(
                        current_page <= 1
                    ),
                ):
                    st.session_state[
                        JOB_LIST_PAGE_KEY
                    ] = (
                        current_page - 1
                    )

                    st.rerun()

            with page_col:
                st.markdown(
                    (
                        f"<div style='"
                        "text-align:center;"
                        "padding-top:8px;"
                        "'>"
                        f"{current_page} / "
                        f"{total_pages}ページ"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

            with next_col:
                if st.button(
                    "次へ →",
                    key="job_list_next_page",
                    width="stretch",
                    disabled=(
                        current_page
                        >= total_pages
                    ),
                ):
                    st.session_state[
                        JOB_LIST_PAGE_KEY
                    ] = (
                        current_page + 1
                    )

                    st.rerun()

    selected_job_ids = [
        job_id
        for job_id, _ in jobs
        if st.session_state.get(
            f"compare_job_{job_id}",
            False,
        )
    ]

    st.session_state[
        JOB_COMPARE_SELECTED_KEY
    ] = selected_job_ids

    if selected_job_ids:
        with st.container(border=True):
            action_col, clear_col, compare_col = st.columns(
                [2, 1, 2]
            )

            with action_col:
                st.write(
                    f"比較対象：{len(selected_job_ids)}件選択中"
                )

                st.caption(
                    "選択した求人を比較できます。"
                )

            with clear_col:
                if st.button(
                    "選択をクリア",
                    key="job_list_clear_compare",
                    width="stretch",
                ):
                    for job_id, _ in jobs:
                        checkbox_key = f"compare_job_{job_id}"

                        if checkbox_key in st.session_state:
                            st.session_state[
                                checkbox_key
                            ] = False

                    st.session_state[
                        JOB_COMPARE_SELECTED_KEY
                    ] = []

                    st.rerun()

            with compare_col:
                compare_disabled = (
                    len(selected_job_ids) < 2
                    or len(selected_job_ids) > 3
                )

                if st.button(
                    f"比較する（{len(selected_job_ids)}件）",
                    key="job_list_compare",
                    type="primary",
                    width="stretch",
                    disabled=compare_disabled,
                ):
                    st.session_state[
                        JOB_COMPARE_SELECTED_KEY
                    ] = selected_job_ids

                    st.query_params["page"] = (
                        "job_comparison"
                    )

                    st.query_params["job_ids"] = (
                        ",".join(
                            str(job_id)
                            for job_id
                            in selected_job_ids
                        )
                    )

                    st.rerun()

                if len(selected_job_ids) > 3:
                    st.caption(
                        "比較対象は3件まで選択できます。"
                    )

    st.divider()

    if st.button(
        "トップへ戻る",
        key="job_list_back_home",
    ):
        move_to_page(None)