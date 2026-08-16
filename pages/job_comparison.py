"""選択した求人の比較結果画面。"""

from html import escape

import streamlit as st

from services.job_evaluation_service import (
    load_job_match_evaluations,
)
from services.job_service import load_jobs

from pages.job_layout import (
    render_job_navigation,
)


JOB_COMPARE_SELECTED_KEY = (
    "job_compare_selected_ids"
)


def move_to_job_list() -> None:
    """比較状態を維持して求人一覧へ移動する。"""

    selected_job_ids = st.session_state.get(
        JOB_COMPARE_SELECTED_KEY,
        [],
    )

    for job_id in selected_job_ids:
        st.session_state[
            f"compare_job_{job_id}"
        ] = True

    st.query_params["page"] = "job_list"

    if "job_ids" in st.query_params:
        del st.query_params["job_ids"]

    st.rerun()


def display_value(
    value,
) -> str:
    """未入力値を比較画面用に整える。"""

    if value is None:
        return "未入力"

    if isinstance(value, list):
        values = [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

        if not values:
            return "未入力"

        return "\n".join(
            f"・{item}"
            for item in values
        )

    text = str(value).strip()

    return text or "未入力"


def display_location(
    job,
) -> str:
    """勤務地を表示用に整える。"""

    location = "".join(
        value
        for value in (
            job.prefecture,
            job.municipality,
        )
        if value
    )

    return location or "未入力"


def display_salary(
    job,
) -> str:
    """年収を表示用に整える。"""

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

        return f"{salary_min} ～ {salary_max}"

    return display_value(
        job.annual_salary
    )


def display_evaluation_score(
    evaluations,
    job_id: int,
    field_name: str,
) -> str:
    """AI評価項目を比較画面用に整える。"""

    evaluation = evaluations.get(
        job_id
    )

    if evaluation is None:
        return "未評価"

    score = getattr(
        evaluation,
        field_name,
        None,
    )

    if score is None:
        return "未評価"

    return f"{score}点"


def render_comparison_row(
    label: str,
    values: list[str],
) -> None:
    """比較項目を横並びで表示する。"""

    with st.container(border=True):
        label_col, *value_columns = st.columns(
            [1.2] + [2] * len(values)
        )

        with label_col:
            st.markdown(
                f"**{label}**"
            )

        for column, value in zip(
            value_columns,
            values,
        ):
            with column:
                st.write(value)


def show_page() -> None:
    """求人比較結果を表示する。"""

    render_job_navigation(
        "job_comparison"
    )

    selected_job_ids = st.session_state.get(
        JOB_COMPARE_SELECTED_KEY,
        [],
    )

    job_ids_value = st.query_params.get(
        "job_ids",
        "",
    )

    if job_ids_value:
        restored_job_ids = []

        for job_id_text in str(
            job_ids_value
        ).split(","):
            try:
                restored_job_ids.append(
                    int(job_id_text)
                )

            except ValueError:
                continue

        if restored_job_ids:
            selected_job_ids = (
                restored_job_ids
            )

            st.session_state[
                JOB_COMPARE_SELECTED_KEY
            ] = selected_job_ids

    all_jobs = dict(load_jobs())

    selected_jobs = [
        (
            job_id,
            all_jobs[job_id],
        )
        for job_id in selected_job_ids
        if job_id in all_jobs
    ]

    if st.button(
        "← 求人一覧へ戻る",
        key="job_comparison_back_top",
    ):
        move_to_job_list()

    st.title("比較結果")

    st.caption(
        "選択した求人の違いを横並びで比較しています。"
    )

    if len(selected_jobs) < 2:
        st.warning(
            "比較する求人を2件以上選択してください。"
        )

        if st.button(
            "求人一覧で選択する",
            key="job_comparison_select_jobs",
            type="primary",
        ):
            move_to_job_list()

        return

    if len(selected_jobs) > 3:
        st.warning(
            "一度に比較できる求人は3件までです。"
            "求人一覧へ戻って選択を調整してください。"
        )

        return

    evaluations = (
        load_job_match_evaluations()
    )

    st.write(
        f"比較対象：{len(selected_jobs)}件"
    )

    with st.container(border=True):
        empty_col, *header_columns = st.columns(
            [1.2] + [2] * len(selected_jobs)
        )

        with empty_col:
            st.markdown("**比較項目**")

        for column, (
            job_id,
            job,
        ) in zip(
            header_columns,
            selected_jobs,
        ):
            with column:
                company_name = (
                    job.company_name
                    or "会社名未入力"
                )

                comparison_job_ids = (
                    ",".join(
                        str(selected_job_id)
                        for selected_job_id, _
                        in selected_jobs
                    )
                )

                company_link_html = (
                    '<a '
                    'style="'
                    'color:#1268f3;'
                    'font-size:20px;'
                    'font-weight:800;'
                    'text-decoration:none;'
                    '" '
                    f'href="?page=job_detail'
                    f'&amp;job_id={job_id}'
                    '&amp;return_page=job_comparison'
                    f'&amp;job_ids={comparison_job_ids}" '
                    'target="_self">'
                    f'{escape(company_name)}'
                    '</a>'
                )

                st.markdown(
                    company_link_html,
                    unsafe_allow_html=True,
                )

                st.caption(
                    job.job_title
                    or job.occupation
                    or "求人名未入力"
                )

                evaluation = evaluations.get(
                    job_id
                )

                if (
                    evaluation is not None
                    and evaluation.overall_score
                    is not None
                ):
                    st.metric(
                        "AI総合マッチ度",
                        f"{evaluation.overall_score}点",
                    )

                else:
                    st.metric(
                        "AI総合マッチ度",
                        "未評価",
                    )

    st.subheader("AIマッチング比較")

    render_comparison_row(
        "希望条件",
        [
            display_evaluation_score(
                evaluations,
                job_id,
                "hope_condition_score",
            )
            for job_id, _ in selected_jobs
        ],
    )

    render_comparison_row(
        "価値観",
        [
            display_evaluation_score(
                evaluations,
                job_id,
                "work_value_score",
            )
            for job_id, _ in selected_jobs
        ],
    )

    render_comparison_row(
        "職務経歴・スキル",
        [
            display_evaluation_score(
                evaluations,
                job_id,
                "career_skill_score",
            )
            for job_id, _ in selected_jobs
        ],
    )

    render_comparison_row(
        "必須条件",
        [
            display_evaluation_score(
                evaluations,
                job_id,
                "required_condition_score",
            )
            for job_id, _ in selected_jobs
        ],
    )

    st.subheader("求人条件比較")

    render_comparison_row(
        "年収",
        [
            display_salary(job)
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "勤務地",
        [
            display_location(job)
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "雇用形態",
        [
            display_value(
                job.employment_type
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "仕事内容",
        [
            display_value(
                job.job_summary
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "働き方",
        [
            display_value(
                job.work_style
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "フレックスタイム",
        [
            display_value(
                job.flextime
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "残業",
        [
            display_value(
                job.overtime
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "勤務時間",
        [
            (
                f"{job.start_time} ～ {job.end_time}"
                if (
                    job.start_time
                    or job.end_time
                )
                else "未入力"
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "休日・休暇",
        [
            display_value(
                job.holidays
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "年間休日数",
        [
            display_value(
                job.annual_holidays
            )
            for _, job in selected_jobs
        ],
    )

    render_comparison_row(
        "福利厚生",
        [
            "\n".join(
                value
                for value in (
                    job.social_insurance,
                    job.commuting_allowance,
                    job.housing_allowance,
                    job.retirement_plan,
                    job.qualification_support,
                )
                if value
            )
            or "未入力"
            for _, job in selected_jobs
        ],
    )

    st.divider()

    if st.button(
        "比較対象を変更する",
        key="job_comparison_change",
        width="stretch",
    ):
        move_to_job_list()