"""登録済み求人の詳細画面。"""

import streamlit as st

from services.job_service import load_job


def move_to_job_list() -> None:
    """求人一覧へ移動する。"""

    st.query_params["page"] = "job_list"

    if "job_id" in st.query_params:
        del st.query_params["job_id"]

    st.rerun()


def display_value(
    value,
) -> str:
    """未入力値を画面表示用に整える。"""

    if value is None:
        return "未入力"

    if isinstance(value, list):
        cleaned_values = [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

        if not cleaned_values:
            return "未入力"

        return "\n".join(
            f"・{item}"
            for item in cleaned_values
        )

    cleaned_value = str(value).strip()

    return cleaned_value or "未入力"


def render_field(
    label: str,
    value,
) -> None:
    """項目名と内容を表示する。"""

    st.caption(label)

    st.write(
        display_value(value)
    )


def render_basic_information(
    job,
) -> None:
    """求人基本情報を表示する。"""

    with st.container(border=True):
        st.subheader("基本情報")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "会社名",
                job.company_name,
            )

            render_field(
                "求人名",
                job.job_title,
            )

            render_field(
                "募集ポジション（職種）",
                job.occupation,
            )

            render_field(
                "業種",
                job.industry,
            )

        with col2:
            source_text = job.source_name

            if (
                job.source_type
                and job.source_name
            ):
                source_text = (
                    f"{job.source_type}／"
                    f"{job.source_name}"
                )

            render_field(
                "紹介経路",
                source_text,
            )

            render_field(
                "求人番号",
                job.job_number,
            )

            render_field(
                "雇用形態",
                job.employment_type,
            )

            render_field(
                "配属部署",
                job.department,
            )


def render_job_description(
    job,
) -> None:
    """仕事内容を表示する。"""

    with st.container(border=True):
        st.subheader("仕事内容")

        render_field(
            "仕事内容・業務概要",
            job.job_summary,
        )

        render_field(
            "具体的な業務内容",
            job.job_details,
        )

        render_field(
            "担当範囲・役割",
            job.responsibility_scope,
        )

        render_field(
            "顧客・対象者",
            job.customers,
        )

        render_field(
            "目標・KPI",
            job.goals_kpi,
        )

        render_field(
            "期待される成果",
            job.expected_results,
        )


def render_requirements(
    job,
) -> None:
    """応募要件を表示する。"""

    with st.container(border=True):
        st.subheader("応募要件")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "必須経験",
                job.required_experience,
            )

            render_field(
                "必須スキル",
                job.required_skills,
            )

            render_field(
                "必須資格",
                job.required_qualifications,
            )

        with col2:
            render_field(
                "歓迎経験",
                job.preferred_experience,
            )

            render_field(
                "歓迎スキル",
                job.preferred_skills,
            )

            render_field(
                "求める人物像",
                job.desired_personality,
            )


def render_working_conditions(
    job,
) -> None:
    """勤務条件を表示する。"""

    with st.container(border=True):
        st.subheader("勤務条件")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "勤務地",
                " ".join(
                    value
                    for value in (
                        job.prefecture,
                        job.municipality,
                    )
                    if value
                ),
            )

            render_field(
                "最寄駅",
                job.nearest_station,
            )

            render_field(
                "勤務形態・働き方",
                job.work_style,
            )

            render_field(
                "転勤",
                job.transfer_required,
            )

        with col2:
            render_field(
                "勤務時間",
                (
                    f"{job.start_time}～"
                    f"{job.end_time}"
                    if (
                        job.start_time
                        or job.end_time
                    )
                    else ""
                ),
            )

            render_field(
                "フレックスタイム",
                job.flextime,
            )

            render_field(
                "残業",
                job.overtime,
            )

            render_field(
                "年間休日数",
                job.annual_holidays,
            )


def render_salary_and_benefits(
    job,
) -> None:
    """給与と福利厚生を表示する。"""

    with st.container(border=True):
        st.subheader("給与・待遇")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "年収",
                job.annual_salary,
            )

            render_field(
                "想定年収（下限）",
                job.expected_salary_min,
            )

            render_field(
                "想定年収（上限）",
                job.expected_salary_max,
            )

            render_field(
                "月給",
                job.monthly_salary,
            )

        with col2:
            render_field(
                "賞与",
                job.bonus,
            )

            render_field(
                "昇給",
                job.salary_increase,
            )

            render_field(
                "社会保険",
                job.social_insurance,
            )

            render_field(
                "研修制度",
                job.training_program,
            )


def show_page() -> None:
    """求人詳細画面を表示する。"""

    job_id_value = st.query_params.get(
        "job_id"
    )

    try:
        job_id = int(job_id_value)
    except (
        TypeError,
        ValueError,
    ):
        st.error(
            "表示する求人を特定できませんでした。"
        )

        if st.button(
            "求人一覧へ戻る",
            key="invalid_job_back",
        ):
            move_to_job_list()

        return

    job = load_job(job_id)

    if job is None:
        st.error(
            "求人が見つかりませんでした。"
        )

        if st.button(
            "求人一覧へ戻る",
            key="missing_job_back",
        ):
            move_to_job_list()

        return

    if st.button(
        "← 求人一覧へ戻る",
        key="job_detail_back",
    ):
        move_to_job_list()

    header_col, source_col = st.columns(
        [4, 1]
    )

    with header_col:
        st.title(
            job.company_name
            or "会社名未入力"
        )

        st.subheader(
            job.job_title
            or job.occupation
            or "求人名未入力"
        )

    with source_col:
        st.caption(
            f"求人ID：{job_id}"
        )

    render_basic_information(job)
    render_job_description(job)
    render_requirements(job)
    render_working_conditions(job)
    render_salary_and_benefits(job)