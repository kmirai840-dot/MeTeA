"""求人登録画面。"""

import streamlit as st

from models import Job

from services.job_service import (
    DUPLICATE_DIFFERENT_SOURCE,
    DUPLICATE_EXACT,
    DUPLICATE_NONE,
    compare_jobs,
    create_job_data,
    delete_job_data,
    load_job,
    load_jobs,
    save_job_data,
    update_job_data,
)


# ========================================
# セッションキー
# ========================================

JOB_REGISTRATION_MODE_KEY = "job_registration_mode"
JOB_FORM_STEP_KEY = "job_form_step"
JOB_EDIT_ID_KEY = "job_edit_id"
JOB_PENDING_DATA_KEY = "job_pending_data"
JOB_DUPLICATE_ID_KEY = "job_duplicate_id"
JOB_DUPLICATE_TYPE_KEY = "job_duplicate_type"


# ========================================
# CSS
# ========================================

def render_styles() -> None:
    """求人登録画面用のスタイルを表示する。"""

    st.markdown(
        """
        <style>
        .job-page-title {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .job-page-description {
            color: #667085;
            font-size: 15px;
            margin-bottom: 28px;
        }

        .job-section-title {
            font-size: 20px;
            font-weight: 700;
            margin-top: 12px;
            margin-bottom: 4px;
        }

        .job-section-description {
            color: #667085;
            font-size: 14px;
            margin-bottom: 18px;
        }

        .job-input-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 4px;
        }

        .job-input-description {
            color: #667085;
            font-size: 14px;
            margin-bottom: 14px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ========================================
# 登録方法選択
# ========================================

def render_method_selection() -> None:
    """3種類の登録方法を横並びで表示する。"""

    st.markdown(
        """
        <div class="job-section-title">
            ① 登録方法の選択
        </div>
        <div class="job-section-description">
            3つの方法から選択してください。
            選択した方法に応じて入力欄が表示されます。
        </div>
        """,
        unsafe_allow_html=True,
    )

    url_col, text_col, manual_col = st.columns(3)

    # ------------------------
    # URL
    # ------------------------

    with url_col:
        with st.container(border=True):
            st.markdown("### 🔗")
            st.markdown("#### 求人URLから登録")

            st.caption(
                "求人ページのURLを入力すると、"
                "AIが情報を取得します。"
            )

            if st.button(
                "この方法を選択",
                key="select_job_url",
                type=(
                    "primary"
                    if st.session_state[
                        JOB_REGISTRATION_MODE_KEY
                    ] == "url"
                    else "secondary"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    JOB_REGISTRATION_MODE_KEY
                ] = "url"

                st.rerun()

    # ------------------------
    # 貼り付け
    # ------------------------

    with text_col:
        with st.container(border=True):
            st.markdown("### 📄")
            st.markdown(
                "#### 求人票を貼り付けて登録"
            )

            st.caption(
                "求人票の本文を貼り付けると、"
                "AIが情報を抽出します。"
            )

            if st.button(
                "この方法を選択",
                key="select_job_text",
                type=(
                    "primary"
                    if st.session_state[
                        JOB_REGISTRATION_MODE_KEY
                    ] == "text"
                    else "secondary"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    JOB_REGISTRATION_MODE_KEY
                ] = "text"
                st.rerun()

    # ------------------------
    # 手動
    # ------------------------

    with manual_col:
        with st.container(border=True):
            st.markdown("### ✏️")
            st.markdown("#### 手動入力")

            st.caption(
                "AIで取得できない場合や、"
                "手動で入力したい場合に選択します。"
            )

            if st.button(
                "この方法を選択",
                key="select_job_manual",
                type=(
                    "primary"
                    if st.session_state[
                        JOB_REGISTRATION_MODE_KEY
                    ] == "manual"
                    else "secondary"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    JOB_REGISTRATION_MODE_KEY
                ] = "manual"

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "form"

                st.rerun()  


# ========================================
# URL入力
# ========================================

def render_url_registration() -> None:
    """URL入力欄を表示する。"""

    with st.container(border=True):

        st.markdown(
            """
            <div class="job-input-title">
                求人URLから登録
            </div>
            <div class="job-input-description">
                求人ページのURLを入力してください。
            </div>
            """,
            unsafe_allow_html=True,
        )

        job_url = st.text_input(
            "求人URL",
            placeholder="https://example.com/jobs/...",
            key="job_registration_url",
        )

        if st.button(
            "🔍 求人情報を取得する",
            key="job_registration_url_button",
            type="primary",
            use_container_width=True,
        ):
            if not job_url.strip():
                st.warning(
                    "求人URLを入力してください。"
                )
            else:
                st.info(
                    "求人URLからの取得処理は"
                    "次の工程で接続します。"
                )


# ========================================
# 貼り付け入力
# ========================================

def render_text_registration() -> None:
    """求人票本文入力欄を表示する。"""

    with st.container(border=True):

        st.markdown(
            """
            <div class="job-input-title">
                求人票を貼り付け
            </div>
            <div class="job-input-description">
                求人票の文章を貼り付けてください。
            </div>
            """,
            unsafe_allow_html=True,
        )

        job_text = st.text_area(
            "求人票の内容",
            placeholder=(
                "ここに求人票の本文を"
                "貼り付けてください。"
            ),
            height=220,
            key="job_registration_text",
        )

        if st.button(
            "求人情報を抽出する",
            key="job_registration_text_button",
            type="primary",
            use_container_width=True,
        ):
            if not job_text.strip():
                st.warning(
                    "求人票の内容を"
                    "貼り付けてください。"
                )
            else:
                st.info(
                    "求人票のAI解析は"
                    "次の工程で接続します。"
                )


# ========================================
# 手動入力
# ========================================

def render_manual_registration() -> None:
    """手動入力画面の仮表示。"""

    with st.container(border=True):

        st.markdown(
            """
            <div class="job-input-title">
                手動入力
            </div>
            <div class="job-input-description">
                求人情報を項目ごとに入力します。
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(
            "ここに求人情報入力フォームを"
            "次の工程で実装します。"
        )


def text_to_list(
    value: str,
) -> list[str]:
    """改行区切りの文字列をリストへ変換する。"""

    return [
        line.strip()
        for line in value.splitlines()
        if line.strip()
    ]


def render_registered_jobs() -> None:
    """登録済み求人を表示する。"""

    jobs = load_jobs()

    if not jobs:
        return

    st.markdown(
        """
        <div class="job-section-title">
            登録済み求人
        </div>
        <div class="job-section-description">
            登録済みの求人を選択すると、
            内容を編集できます。
        </div>
        """,
        unsafe_allow_html=True,
    )

    for job_id, job in jobs:
        with st.container(border=True):

            col1, col2, col3 = st.columns(
                [4, 1, 1]
            )

            with col1:
                st.markdown(
                    f"**{job.company_name or '会社名未入力'}**"
                )

                st.caption(
                    job.job_title
                    or "求人名未入力"
                )

            with col2:
                if st.button(
                    "編集",
                    key=f"edit_job_{job_id}",
                    use_container_width=True,
                ):
                    load_job_for_edit(
                        job_id
                    )

                    st.rerun()

            with col3:
                if st.button(
                    "削除",
                    key=f"delete_job_{job_id}",
                    use_container_width=True,
                ):
                    deleted = delete_job_data(
                        job_id
                    )

                    if deleted:
                        st.rerun()
                    else:
                        st.error(
                            "求人を削除できませんでした。"
                        )


def load_job_for_edit(
    job_id: int,
) -> None:
    """登録済み求人を編集フォームへ復元する。"""

    job = load_job(job_id)

    if job is None:
        st.error(
            "編集対象の求人が見つかりませんでした。"
        )
        return

    st.session_state[
        JOB_EDIT_ID_KEY
    ] = job_id

    st.session_state[
        JOB_FORM_STEP_KEY
    ] = "form"

    st.session_state[
        JOB_REGISTRATION_MODE_KEY
    ] = job.registration_method or "manual"

    st.session_state[
        "job_form_company_name"
    ] = job.company_name

    st.session_state[
        "job_form_job_title"
    ] = job.job_title

    st.session_state[
        "job_form_job_number"
    ] = job.job_number

    st.session_state[
        "job_form_publication_start"
    ] = job.publication_start_date

    st.session_state[
        "job_form_publication_end"
    ] = job.publication_end_date

    st.session_state[
        "job_form_industry"
    ] = job.industry

    st.session_state[
        "job_form_business_description"
    ] = job.business_description

    st.session_state[
        "job_form_employee_count"
    ] = job.employee_count

    st.session_state[
        "job_form_established_date"
    ] = job.established_date

    st.session_state[
        "job_form_capital"
    ] = job.capital

    st.session_state[
        "job_form_listing_status"
    ] = job.listing_status

    st.session_state[
        "job_form_job_summary"
    ] = job.job_summary

    st.session_state[
        "job_form_job_details"
    ] = "\n".join(job.job_details)

    st.session_state[
        "job_form_responsibility_scope"
    ] = job.responsibility_scope

    st.session_state[
        "job_form_customers"
    ] = job.customers

    st.session_state[
        "job_form_internal_stakeholders"
    ] = job.internal_stakeholders

    st.session_state[
        "job_form_external_partners"
    ] = job.external_partners

    st.session_state[
        "job_form_goals_kpi"
    ] = job.goals_kpi

    st.session_state[
        "job_form_expected_results"
    ] = job.expected_results

    st.session_state[
        "job_form_occupation"
    ] = job.occupation

    st.session_state[
        "job_form_department"
    ] = job.department

    st.session_state[
        "job_form_planned_hires"
    ] = job.planned_hires

    st.session_state[
        "job_form_recruitment_reason"
    ] = job.recruitment_reason

    st.session_state[
        "job_form_source_name"
    ] = job.source_name

    st.session_state[
        "job_form_employment_type"
    ] = job.employment_type

    st.session_state[
        "job_form_probation_period"
    ] = job.probation_period

    st.session_state[
        "job_form_prefecture"
    ] = job.prefecture

    st.session_state[
        "job_form_municipality"
    ] = job.municipality

    st.session_state[
        "job_form_nearest_station"
    ] = job.nearest_station

    st.session_state[
        "job_form_transfer_required"
    ] = job.transfer_required

    st.session_state[
        "job_form_work_style"
    ] = job.work_style

    st.session_state[
        "job_form_start_time"
    ] = job.start_time

    st.session_state[
        "job_form_end_time"
    ] = job.end_time

    st.session_state[
        "job_form_break_minutes"
    ] = job.break_minutes

    st.session_state[
        "job_form_scheduled_work_hours"
    ] = job.scheduled_work_hours

    st.session_state[
        "job_form_flextime"
    ] = job.flextime

    st.session_state[
        "job_form_overtime"
    ] = job.overtime

    st.session_state[
        "job_form_holidays"
    ] = job.holidays

    st.session_state[
        "job_form_annual_holidays"
    ] = job.annual_holidays

    st.session_state[
        "job_form_monthly_salary"
    ] = job.monthly_salary

    st.session_state[
        "job_form_annual_salary"
    ] = job.annual_salary

    st.session_state[
        "job_form_expected_salary_min"
    ] = job.expected_salary_min

    st.session_state[
        "job_form_expected_salary_max"
    ] = job.expected_salary_max

    st.session_state[
        "job_form_fixed_overtime_hours"
    ] = job.fixed_overtime_hours

    st.session_state[
        "job_form_fixed_overtime_pay"
    ] = job.fixed_overtime_pay

    st.session_state[
        "job_form_bonus"
    ] = job.bonus

    st.session_state[
        "job_form_salary_increase"
    ] = job.salary_increase

    st.session_state[
        "job_form_incentive"
    ] = job.incentive

    st.session_state[
        "job_form_social_insurance"
    ] = job.social_insurance

    st.session_state[
        "job_form_commuting_allowance"
    ] = job.commuting_allowance

    st.session_state[
        "job_form_housing_allowance"
    ] = job.housing_allowance

    st.session_state[
        "job_form_retirement_plan"
    ] = job.retirement_plan

    st.session_state[
        "job_form_qualification_support"
    ] = job.qualification_support

    st.session_state[
        "job_form_training_program"
    ] = job.training_program

    st.session_state[
        "job_form_required_experience"
    ] = "\n".join(
        job.required_experience
    )

    st.session_state[
        "job_form_required_skills"
    ] = "\n".join(
        job.required_skills
    )

    st.session_state[
        "job_form_required_qualifications"
    ] = "\n".join(
        job.required_qualifications
    )

    st.session_state[
        "job_form_preferred_experience"
    ] = "\n".join(
        job.preferred_experience
    )

    st.session_state[
        "job_form_preferred_skills"
    ] = "\n".join(
        job.preferred_skills
    )

    st.session_state[
        "job_form_desired_personality"
    ] = "\n".join(
        job.desired_personality
    )

    st.session_state[
        "job_form_not_listed_fields"
    ] = "\n".join(
        job.not_listed_fields
    )

    st.session_state[
        "job_form_document_screening"
    ] = job.document_screening

    st.session_state[
        "job_form_interview"
    ] = job.interview

    st.session_state[
        "job_form_aptitude_test"
    ] = job.aptitude_test

    st.session_state[
        "job_form_interview_count"
    ] = job.interview_count

    st.session_state[
        "job_form_expected_join_date"
    ] = job.expected_join_date


def render_job_form() -> None:
    """求人情報の入力フォームを表示する。"""

    if st.button(
        "← 登録方法の選択に戻る",
        key="job_form_back",
    ):
        st.session_state[
            JOB_FORM_STEP_KEY
        ] = "select"
        st.rerun()

    edit_job_id = st.session_state.get(
        JOB_EDIT_ID_KEY
    )

    if edit_job_id is not None:
        st.info(
            f"求人ID {edit_job_id} を編集中です。"
        )

    st.markdown(
        """
        <div class="job-section-title">
            ② 求人情報の確認・入力
        </div>
        <div class="job-section-description">
            求人情報を確認し、
            必要に応じて修正してください。
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):

        st.markdown("### 求人基本情報")

        company_name = st.text_input(
            "会社名",
            key="job_form_company_name",
        )

        job_title = st.text_input(
            "求人名",
            key="job_form_job_title",
        )

        source_name = st.text_input(
            "紹介経路・求人媒体",
            placeholder="例：Indeed、企業採用ページ、リクルートエージェント",
            key="job_form_source_name",
        )

        job_number = st.text_input(
            "求人番号",
            key="job_form_job_number",
        )

        col1, col2 = st.columns(2)

        with col1:
            publication_start_date = st.text_input(
                "掲載開始日",
                placeholder="例：2026/08/01",
                key="job_form_publication_start",
            )

        with col2:
            publication_end_date = st.text_input(
                "掲載終了日",
                placeholder="例：2026/08/31",
                key="job_form_publication_end",
            )

        industry = st.text_input(
            "業種",
            key="job_form_industry",
        )

        business_description = st.text_area(
            "事業内容",
            key="job_form_business_description",
        )

        col3, col4 = st.columns(2)

        with col3:
            employee_count = st.text_input(
                "従業員数",
                key="job_form_employee_count",
            )

            established_date = st.text_input(
                "設立",
                key="job_form_established_date",
            )

        with col4:
            capital = st.text_input(
                "資本金",
                key="job_form_capital",
            )

            listing_status = st.text_input(
                "上場区分",
                key="job_form_listing_status",
            )

    with st.container(border=True):

        st.markdown("### 募集内容")

        col5, col6 = st.columns(2)

        with col5:
            occupation = st.text_input(
                "職種",
                key="job_form_occupation",
            )

            department = st.text_input(
                "配属部署",
                key="job_form_department",
            )

        with col6:
            planned_hires = st.text_input(
                "採用予定人数",
                key="job_form_planned_hires",
            )

        recruitment_reason = st.text_area(
            "募集背景・採用理由",
            key="job_form_recruitment_reason",
        )

    with st.container(border=True):

        st.markdown("### 仕事内容")

        job_summary = st.text_area(
            "仕事内容・業務概要",
            height=140,
            key="job_form_job_summary",
        )

        responsibility_scope = st.text_area(
            "担当範囲・役割",
            height=100,
            key="job_form_responsibility_scope",
        )

        col7, col8 = st.columns(2)

        with col7:
            customers = st.text_area(
                "顧客・対象者",
                key="job_form_customers",
            )

            internal_stakeholders = st.text_area(
                "社内の関係者",
                key="job_form_internal_stakeholders",
            )

        with col8:
            external_partners = st.text_area(
                "社外の関係者",
                key="job_form_external_partners",
            )

            goals_kpi = st.text_area(
                "目標・KPI",
                key="job_form_goals_kpi",
            )

        expected_results = st.text_area(
            "期待される成果",
            key="job_form_expected_results",
        )

    with st.container(border=True):

        st.markdown("### 勤務条件")

        col9, col10 = st.columns(2)

        with col9:
            employment_type = st.text_input(
                "雇用形態",
                key="job_form_employment_type",
            )

            probation_period = st.text_input(
                "試用期間",
                key="job_form_probation_period",
            )

            prefecture = st.text_input(
                "都道府県",
                key="job_form_prefecture",
            )

            municipality = st.text_input(
                "市区町村",
                key="job_form_municipality",
            )

            nearest_station = st.text_input(
                "最寄駅",
                key="job_form_nearest_station",
            )

        with col10:
            transfer_required = st.text_input(
                "転勤",
                key="job_form_transfer_required",
            )

            work_style = st.text_input(
                "勤務形態・働き方",
                placeholder="例：出社、在宅、ハイブリッド",
                key="job_form_work_style",
            )

            flextime = st.text_input(
                "フレックスタイム",
                key="job_form_flextime",
            )

            overtime = st.text_input(
                "残業",
                key="job_form_overtime",
            )

        col11, col12 = st.columns(2)

        with col11:
            start_time = st.text_input(
                "始業時間",
                placeholder="例：09:00",
                key="job_form_start_time",
            )

            break_minutes = st.text_input(
                "休憩時間",
                placeholder="例：60分",
                key="job_form_break_minutes",
            )

        with col12:
            end_time = st.text_input(
                "終業時間",
                placeholder="例：18:00",
                key="job_form_end_time",
            )

            scheduled_work_hours = st.text_input(
                "所定労働時間",
                key="job_form_scheduled_work_hours",
            )

        holidays = st.text_input(
            "休日・休暇",
            key="job_form_holidays",
        )

        annual_holidays = st.text_input(
            "年間休日数",
            placeholder="例：125日",
            key="job_form_annual_holidays",
        )

    with st.container(border=True):

        st.markdown("### 給与・待遇")

        col13, col14 = st.columns(2)

        with col13:
            monthly_salary = st.text_input(
                "月給",
                key="job_form_monthly_salary",
            )

            expected_salary_min = st.text_input(
                "想定年収（下限）",
                key="job_form_expected_salary_min",
            )

            fixed_overtime_hours = st.text_input(
                "固定残業時間",
                key="job_form_fixed_overtime_hours",
            )

            bonus = st.text_input(
                "賞与",
                key="job_form_bonus",
            )

        with col14:
            annual_salary = st.text_input(
                "年収",
                key="job_form_annual_salary",
            )

            expected_salary_max = st.text_input(
                "想定年収（上限）",
                key="job_form_expected_salary_max",
            )

            fixed_overtime_pay = st.text_input(
                "固定残業代",
                key="job_form_fixed_overtime_pay",
            )

            salary_increase = st.text_input(
                "昇給",
                key="job_form_salary_increase",
            )

        incentive = st.text_input(
            "インセンティブ",
            key="job_form_incentive",
        )

    with st.container(border=True):

        st.markdown("### 福利厚生")

        col15, col16 = st.columns(2)

        with col15:
            social_insurance = st.text_input(
                "社会保険",
                key="job_form_social_insurance",
            )

            commuting_allowance = st.text_input(
                "通勤手当",
                key="job_form_commuting_allowance",
            )

            housing_allowance = st.text_input(
                "住宅手当",
                key="job_form_housing_allowance",
            )

        with col16:
            retirement_plan = st.text_input(
                "退職金制度",
                key="job_form_retirement_plan",
            )

            qualification_support = st.text_input(
                "資格取得支援",
                key="job_form_qualification_support",
            )

            training_program = st.text_input(
                "研修制度",
                key="job_form_training_program",
            )

    with st.container(border=True):

        st.markdown("### 応募条件・求める人物像")

        st.caption(
            "複数ある場合は、1行に1項目ずつ入力してください。"
        )

        col17, col18 = st.columns(2)

        with col17:
            required_experience_text = st.text_area(
                "必須経験",
                placeholder=(
                    "例：\n"
                    "法人営業経験3年以上\n"
                    "顧客折衝経験"
                ),
                key="job_form_required_experience",
            )

            required_skills_text = st.text_area(
                "必須スキル",
                placeholder=(
                    "例：\n"
                    "Excel\n"
                    "PowerPoint"
                ),
                key="job_form_required_skills",
            )

            required_qualifications_text = st.text_area(
                "必須資格",
                key="job_form_required_qualifications",
            )

        with col18:
            preferred_experience_text = st.text_area(
                "歓迎経験",
                key="job_form_preferred_experience",
            )

            preferred_skills_text = st.text_area(
                "歓迎スキル",
                key="job_form_preferred_skills",
            )

            desired_personality_text = st.text_area(
                "求める人物像",
                key="job_form_desired_personality",
            )

        job_details_text = st.text_area(
            "具体的な業務内容",
            placeholder=(
                "複数ある場合は1行ずつ入力してください。"
            ),
            key="job_form_job_details",
        )

        not_listed_fields_text = st.text_area(
            "求人票に記載がない項目・確認したいこと",
            placeholder=(
                "例：\n"
                "平均残業時間の記載なし\n"
                "在宅勤務頻度の記載なし"
            ),
            key="job_form_not_listed_fields",
        )

    with st.container(border=True):

        st.markdown("### 選考情報")

        col19, col20 = st.columns(2)

        with col19:
            document_screening = st.text_input(
                "書類選考",
                key="job_form_document_screening",
            )

            aptitude_test = st.text_input(
                "適性検査",
                key="job_form_aptitude_test",
            )

            expected_join_date = st.text_input(
                "入社予定・入社可能時期",
                key="job_form_expected_join_date",
            )

        with col20:
            interview = st.text_input(
                "面接",
                key="job_form_interview",
            )

            interview_count = st.text_input(
                "面接回数",
                key="job_form_interview_count",
            )

        st.divider()

    edit_job_id = st.session_state.get(
        JOB_EDIT_ID_KEY
    )

    save_button_label = (
        "変更を保存する"
        if edit_job_id is not None
        else "求人情報を保存する"
    )

    if st.button(
        save_button_label,
        key="job_form_save",
        type="primary",
        use_container_width=True,
    ):
        job = Job(
            registration_method=st.session_state[
                JOB_REGISTRATION_MODE_KEY
            ],
            source_url=st.session_state.get(
                "job_registration_url",
                "",
            ),
            source_text=st.session_state.get(
                "job_registration_text",
                "",
            ),
            acquired_at="",
            source_name=source_name,

            company_name=company_name,
            job_title=job_title,
            job_number=job_number,
            publication_start_date=publication_start_date,
            publication_end_date=publication_end_date,
            industry=industry,
            business_description=business_description,
            employee_count=employee_count,
            established_date=established_date,
            capital=capital,
            listing_status=listing_status,

            occupation=occupation,
            department=department,
            planned_hires=planned_hires,
            recruitment_reason=recruitment_reason,

            job_summary=job_summary,
            responsibility_scope=responsibility_scope,
            customers=customers,
            internal_stakeholders=internal_stakeholders,
            external_partners=external_partners,
            goals_kpi=goals_kpi,
            expected_results=expected_results,

            employment_type=employment_type,
            probation_period=probation_period,
            prefecture=prefecture,
            municipality=municipality,
            nearest_station=nearest_station,
            transfer_required=transfer_required,
            work_style=work_style,
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
            scheduled_work_hours=scheduled_work_hours,
            flextime=flextime,
            overtime=overtime,
            holidays=holidays,
            annual_holidays=annual_holidays,

            monthly_salary=monthly_salary,
            annual_salary=annual_salary,
            expected_salary_min=expected_salary_min,
            expected_salary_max=expected_salary_max,
            fixed_overtime_hours=fixed_overtime_hours,
            fixed_overtime_pay=fixed_overtime_pay,
            bonus=bonus,
            salary_increase=salary_increase,
            incentive=incentive,

            social_insurance=social_insurance,
            commuting_allowance=commuting_allowance,
            housing_allowance=housing_allowance,
            retirement_plan=retirement_plan,
            qualification_support=qualification_support,
            training_program=training_program,

            document_screening=document_screening,
            interview=interview,
            aptitude_test=aptitude_test,
            interview_count=interview_count,
            expected_join_date=expected_join_date,

            job_details=text_to_list(
                job_details_text
            ),
            required_experience=text_to_list(
                required_experience_text
            ),
            required_skills=text_to_list(
                required_skills_text
            ),
            required_qualifications=text_to_list(
                required_qualifications_text
            ),
            preferred_experience=text_to_list(
                preferred_experience_text
            ),
            preferred_skills=text_to_list(
                preferred_skills_text
            ),
            desired_personality=text_to_list(
                desired_personality_text
            ),
            not_listed_fields=text_to_list(
                not_listed_fields_text
            ),
        )

        if edit_job_id is not None:
            errors = update_job_data(
                edit_job_id,
                job,
            )

            if errors:
                for error in errors:
                    st.error(error)

            else:
                st.success(
                    "求人情報を更新しました。"
                )

                st.caption(
                    f"求人ID：{edit_job_id}"
                )

        else:
            duplicate_type, existing_job_id, errors = (
                save_job_data(job)
            )

            if errors:
                for error in errors:
                    st.error(error)

            elif duplicate_type == DUPLICATE_NONE:
                job_id, create_errors = (
                    create_job_data(job)
                )

                if create_errors:
                    for error in create_errors:
                        st.error(error)

                else:
                    st.success(
                        "求人情報を保存しました。"
                    )

                    st.caption(
                        f"求人ID：{job_id}"
                    )

            elif duplicate_type == DUPLICATE_EXACT:
                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = job

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = existing_job_id

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = DUPLICATE_EXACT

                st.rerun()

            elif (
                duplicate_type
                == DUPLICATE_DIFFERENT_SOURCE
            ):
                job_id, create_errors = (
                    create_job_data(job)
                )

                if create_errors:
                    for error in create_errors:
                        st.error(error)

                else:
                    st.success(
                        "同じ会社・職種の求人が"
                        "別の紹介経路ですでに登録されています。"
                        "別求人として新規登録しました。"
                    )

                    st.caption(
                        f"求人ID：{job_id}"
                    )


def render_duplicate_confirmation() -> None:
    """同一求人が見つかった場合に差分と更新確認を表示する。"""

    duplicate_type = st.session_state.get(
        JOB_DUPLICATE_TYPE_KEY
    )

    if duplicate_type != DUPLICATE_EXACT:
        return

    pending_job = st.session_state.get(
        JOB_PENDING_DATA_KEY
    )

    existing_job_id = st.session_state.get(
        JOB_DUPLICATE_ID_KEY
    )

    if (
        pending_job is None
        or existing_job_id is None
    ):
        return

    existing_job = load_job(
        existing_job_id
    )

    if existing_job is None:
        st.error(
            "既存の求人情報を取得できませんでした。"
        )
        return

    st.warning(
        "同一求人がすでに登録されています。"
        "既存情報を更新しますか？"
    )

    differences = compare_jobs(
        existing_job,
        pending_job,
    )

    if differences:
        st.markdown(
            "### 既存情報との比較"
        )

        comparison_data = [
            {
                "項目": label,
                "既存情報": old_value,
                "今回の情報": new_value,
            }
            for (
                label,
                old_value,
                new_value,
            ) in differences
        ]

        st.dataframe(
            comparison_data,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "既存情報と今回の入力内容に"
            "変更はありません。"
        )

    yes_col, no_col = st.columns(2)

    with yes_col:
        if st.button(
            "既存情報を更新する",
            key="duplicate_job_update",
            type="primary",
            use_container_width=True,
        ):
            errors = update_job_data(
                existing_job_id,
                pending_job,
            )

            if errors:
                for error in errors:
                    st.error(error)

            else:
                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = None

                st.success(
                    "既存の求人情報を更新しました。"
                )

    with no_col:
        if st.button(
            "更新しない",
            key="duplicate_job_cancel",
            use_container_width=True,
        ):
            st.session_state[
                JOB_PENDING_DATA_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_ID_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_TYPE_KEY
            ] = None

            st.info(
                "更新をキャンセルしました。"
            )

            st.rerun()


# ========================================
# 画面本体
# ========================================

def show_page() -> None:
    """求人登録画面を表示する。"""

    render_styles()

    if JOB_REGISTRATION_MODE_KEY not in st.session_state:
        st.session_state[
            JOB_REGISTRATION_MODE_KEY
        ] = "url"

    if JOB_FORM_STEP_KEY not in st.session_state:
        st.session_state[
            JOB_FORM_STEP_KEY
        ] = "select"

    if JOB_EDIT_ID_KEY not in st.session_state:
        st.session_state[
            JOB_EDIT_ID_KEY
        ] = None

    if st.session_state[
        JOB_FORM_STEP_KEY
    ] == "form":
        render_job_form()

        render_duplicate_confirmation()

        return

    st.markdown(
        """
        <div class="job-page-title">
            求人を登録する
        </div>
        <div class="job-page-description">
            気になる求人の情報を取り込みます。
            登録方法を選択してください。
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3枚を常に横並び表示
    render_method_selection()

    render_registered_jobs()

    st.write("")

    # 選択された方法だけ下に表示
    mode = st.session_state[
        JOB_REGISTRATION_MODE_KEY
    ]

    if mode == "url":
        render_url_registration()

    elif mode == "text":
        render_text_registration()

    elif mode == "manual":
        render_manual_registration()