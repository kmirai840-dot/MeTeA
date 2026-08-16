"""求人登録画面。"""

from dataclasses import asdict
from datetime import (
    date,
    datetime,
    time,
)

import streamlit as st

from models import Job

from services.job_extraction_service import (
    extract_job_data,
)
from services.job_matching_auto_evaluation_service import (
    automatically_evaluate_and_save_job,
)

from services.job_service import (
    DUPLICATE_DIFFERENT_SOURCE,
    DUPLICATE_EXACT,
    DUPLICATE_NONE,
    DUPLICATE_POSSIBLE,
    add_job_source_data,
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
JOB_CONFIRM_DATA_KEY = "job_confirm_data"
JOB_COMPLETE_MESSAGE_KEY = "job_complete_message"
JOB_COMPLETE_NOTE_KEY = "job_complete_note"
JOB_COMPLETE_JOB_ID_KEY = "job_complete_job_id"
JOB_DUPLICATE_ID_KEY = "job_duplicate_id"
JOB_DUPLICATE_TYPE_KEY = "job_duplicate_type"
JOB_FORM_RETURN_PAGE_KEY = (
    "job_form_return_page"
)


def start_new_job_registration() -> None:
    """新規求人登録を初期状態から開始する。"""

    st.session_state[
        JOB_REGISTRATION_MODE_KEY
    ] = "url"

    st.session_state[
        JOB_FORM_STEP_KEY
    ] = "select"

    st.session_state[
        JOB_EDIT_ID_KEY
    ] = None

    st.session_state[
        JOB_PENDING_DATA_KEY
    ] = None

    st.session_state[
        JOB_CONFIRM_DATA_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_MESSAGE_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_NOTE_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_JOB_ID_KEY
    ] = None

    st.session_state[
        JOB_DUPLICATE_ID_KEY
    ] = None

    st.session_state[
        JOB_DUPLICATE_TYPE_KEY
    ] = None


SOURCE_TYPES = (
    "選択してください",
    "転職エージェント",
    "求人サイト",
    "企業採用ページ",
    "ハローワーク",
    "スカウト",
    "知人・社員紹介",
    "その他",
)

LISTING_STATUSES = (
    "",
    "上場",
    "非上場",
    "不明",
)

EMPLOYMENT_TYPES = (
    "",
    "正社員",
    "契約社員",
    "派遣社員",
    "パート・アルバイト",
    "業務委託",
    "その他",
)

WAGE_TYPES = (
    "",
    "月給制",
    "年俸制",
    "時給制",
    "日給制",
    "その他",
)

SELECTION_STEP_OPTIONS = (
    "",
    "あり",
    "なし",
    "不明",
)

PROBATION_PERIOD_OPTIONS = (
    "",
    "あり",
    "なし",
    "不明",
)

FIXED_OVERTIME_OPTIONS = (
    "",
    "あり",
    "なし",
    "不明",
)

FLEXTIME_OPTIONS = (
    "",
    "あり",
    "なし",
    "条件付き",
    "不明",
)

TRANSFER_OPTIONS = (
    "",
    "あり",
    "なし",
    "条件付き",
    "不明",
)

WORK_STYLE_OPTIONS = (
    "",
    "出社のみ",
    "一部在宅",
    "完全在宅",
    "相談可",
    "不明",
)

PREFECTURES = (
    "",
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
    "海外",
    "勤務地不明",
)


def options_with_current(
    options: tuple[str, ...],
    current_value: str,
) -> tuple[str, ...]:
    """既存の自由記述値を失わず選択肢へ含める。"""

    if (
        current_value
        and current_value not in options
    ):
        return (
            *options,
            current_value,
        )

    return options


def infer_source_type(
    source_name: str,
) -> str:
    """既存の紹介経路名から種別を推定する。"""

    normalized = source_name.strip().casefold()

    if not normalized:
        return "選択してください"

    if "エージェント" in source_name:
        return "転職エージェント"

    if normalized in {
        "indeed",
        "求人ボックス",
        "スタンバイ",
    }:
        return "求人サイト"

    if (
        "採用" in source_name
        or "企業" in source_name
    ):
        return "企業採用ページ"

    if "ハローワーク" in source_name:
        return "ハローワーク"

    if "スカウト" in source_name:
        return "スカウト"

    return "その他"

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

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "source"

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

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "source"

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
                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "form"

                st.rerun()



def apply_extracted_job_data(
    extracted_data: dict,
) -> None:
    """AI抽出結果を共通フォームへ反映する。"""

    text_field_map = {
        "company_name": "job_form_company_name",
        "job_title": "job_form_job_title",
        "job_number": "job_form_job_number",
        "industry": "job_form_industry",
        "business_description": (
            "job_form_business_description"
        ),
        "established_date": (
            "job_form_established_date"
        ),
        "capital": "job_form_capital",
        "listing_status": (
            "job_form_listing_status"
        ),
        "occupation": "job_form_occupation",
        "department": "job_form_department",
        "recruitment_reason": (
            "job_form_recruitment_reason"
        ),
        "job_summary": "job_form_job_summary",
        "responsibility_scope": (
            "job_form_responsibility_scope"
        ),
        "customers": "job_form_customers",
        "internal_stakeholders": (
            "job_form_internal_stakeholders"
        ),
        "external_partners": (
            "job_form_external_partners"
        ),
        "goals_kpi": "job_form_goals_kpi",
        "expected_results": (
            "job_form_expected_results"
        ),
        "employment_type": (
            "job_form_employment_type"
        ),
        "probation_period_status": (
            "job_form_probation_period_status"
        ),
        "probation_period": (
            "job_form_probation_period"
        ),
        "prefecture": "job_form_prefecture",
        "municipality": "job_form_municipality",
        "nearest_station": (
            "job_form_nearest_station"
        ),
        "transfer_required": (
            "job_form_transfer_required"
        ),
        "work_style": "job_form_work_style",
        "flextime": "job_form_flextime",
        "holidays": "job_form_holidays",
        "wage_type": "job_form_wage_type",
        "fixed_overtime_system": (
            "job_form_fixed_overtime_system"
        ),
        "overtime_extra_pay": (
            "job_form_overtime_extra_pay"
        ),
        "bonus": "job_form_bonus",
        "salary_increase": (
            "job_form_salary_increase"
        ),
        "incentive": "job_form_incentive",
        "social_insurance": (
            "job_form_social_insurance"
        ),
        "commuting_allowance": (
            "job_form_commuting_allowance"
        ),
        "housing_allowance": (
            "job_form_housing_allowance"
        ),
        "retirement_plan": (
            "job_form_retirement_plan"
        ),
        "qualification_support": (
            "job_form_qualification_support"
        ),
        "training_program": (
            "job_form_training_program"
        ),
        "document_screening_status": (
            "job_form_document_screening_status"
        ),
        "document_screening": (
            "job_form_document_screening"
        ),
        "interview": "job_form_interview",
        "aptitude_test_status": (
            "job_form_aptitude_test_status"
        ),
        "aptitude_test": (
            "job_form_aptitude_test"
        ),
        "expected_join_date": (
            "job_form_expected_join_date"
        ),
    }

    for (
        field_name,
        form_key,
    ) in text_field_map.items():
        extracted_value = extracted_data.get(
            field_name,
            "",
        )

        st.session_state[form_key] = str(
            extracted_value or ""
        ).strip()

    list_field_map = {
        "job_details": "job_form_job_details",
        "required_experience": (
            "job_form_required_experience"
        ),
        "required_skills": (
            "job_form_required_skills"
        ),
        "required_qualifications": (
            "job_form_required_qualifications"
        ),
        "preferred_experience": (
            "job_form_preferred_experience"
        ),
        "preferred_skills": (
            "job_form_preferred_skills"
        ),
        "desired_personality": (
            "job_form_desired_personality"
        ),
        "not_listed_fields": (
            "job_form_not_listed_fields"
        ),
    }

    for (
        field_name,
        form_key,
    ) in list_field_map.items():
        extracted_values = extracted_data.get(
            field_name,
            [],
        )

        if not isinstance(
            extracted_values,
            list,
        ):
            extracted_values = []

        st.session_state[form_key] = "\n".join(
            str(value).strip()
            for value in extracted_values
            if str(value).strip()
        )

    def extracted_integer(
        field_name: str,
    ) -> int | None:
        return parse_integer_value(
            str(
                extracted_data.get(
                    field_name,
                    "",
                )
                or ""
            )
        )

    def apply_optional_integer(
        field_name: str,
        state_key: str,
        checkbox_key: str,
        value_key: str,
    ) -> None:
        extracted_value = extracted_integer(
            field_name
        )

        st.session_state[state_key] = (
            extracted_value
        )

        st.session_state[checkbox_key] = (
            extracted_value is not None
        )

        if extracted_value is not None:
            st.session_state[value_key] = (
                extracted_value
            )
        else:
            st.session_state.pop(
                value_key,
                None,
            )

    employee_count_min = extracted_integer(
        "employee_count_min"
    )

    employee_count_max = extracted_integer(
        "employee_count_max"
    )

    has_employee_count = (
        employee_count_min is not None
        or employee_count_max is not None
    )

    st.session_state[
        "job_form_has_employee_count"
    ] = has_employee_count

    st.session_state[
        "job_form_employee_count_min"
    ] = employee_count_min

    st.session_state[
        "job_form_employee_count_max"
    ] = employee_count_max

    apply_optional_integer(
        "planned_hires",
        "job_form_planned_hires",
        "job_form_has_planned_hires",
        "job_form_planned_hires_value",
    )

    apply_optional_integer(
        "annual_holidays",
        "job_form_annual_holidays",
        "job_form_has_annual_holidays",
        "job_form_annual_holidays_value",
    )

    interview_count_min = extracted_integer(
        "interview_count_min"
    )

    interview_count_max = extracted_integer(
        "interview_count_max"
    )

    has_interview_count = (
        interview_count_min is not None
        or interview_count_max is not None
    )

    st.session_state[
        "job_form_has_interview_count"
    ] = has_interview_count

    st.session_state[
        "job_form_interview_count_min"
    ] = interview_count_min

    st.session_state[
        "job_form_interview_count_max"
    ] = interview_count_max

    st.session_state[
        "job_form_probation_period_months"
    ] = extracted_integer(
        "probation_period_months"
    )

    start_time_value = parse_time_value(
        str(
            extracted_data.get(
                "start_time",
                "",
            )
            or ""
        )
    )

    end_time_value = parse_time_value(
        str(
            extracted_data.get(
                "end_time",
                "",
            )
            or ""
        )
    )

    st.session_state[
        "job_form_start_time"
    ] = start_time_value

    st.session_state[
        "job_form_end_time"
    ] = end_time_value

    break_minutes_value = extracted_integer(
        "break_minutes"
    )

    st.session_state[
        "job_form_has_break_minutes"
    ] = break_minutes_value is not None

    if break_minutes_value is not None:
        st.session_state[
            "job_form_break_minutes_value"
        ] = break_minutes_value
    else:
        st.session_state.pop(
            "job_form_break_minutes_value",
            None,
        )

    scheduled_work_hours_value = parse_hour_value(
        str(
            extracted_data.get(
                "scheduled_work_hours",
                "",
            )
            or ""
        )
    )

    st.session_state[
        "job_form_has_scheduled_work_hours"
    ] = scheduled_work_hours_value is not None

    if scheduled_work_hours_value is not None:
        st.session_state[
            "job_form_scheduled_work_hours_value"
        ] = scheduled_work_hours_value
    else:
        st.session_state.pop(
            "job_form_scheduled_work_hours_value",
            None,
        )

    overtime_value = extracted_integer(
        "overtime"
    )

    st.session_state[
        "job_form_has_overtime"
    ] = overtime_value is not None

    if overtime_value is not None:
        st.session_state[
            "job_form_overtime_value"
        ] = overtime_value
    else:
        st.session_state.pop(
            "job_form_overtime_value",
            None,
        )

    numeric_form_fields = {
        "monthly_salary_min": (
            "job_form_monthly_salary_min"
        ),
        "monthly_salary_max": (
            "job_form_monthly_salary_max"
        ),
        "base_salary_min": (
            "job_form_base_salary_min"
        ),
        "base_salary_max": (
            "job_form_base_salary_max"
        ),
        "expected_salary_min": (
            "job_form_expected_salary_min"
        ),
        "expected_salary_max": (
            "job_form_expected_salary_max"
        ),
        "fixed_overtime_hours": (
            "job_form_fixed_overtime_hours"
        ),
        "fixed_overtime_pay_min": (
            "job_form_fixed_overtime_pay_min"
        ),
        "fixed_overtime_pay_max": (
            "job_form_fixed_overtime_pay_max"
        ),
    }

    for (
        field_name,
        form_key,
    ) in numeric_form_fields.items():
        st.session_state[form_key] = (
            extracted_integer(field_name)
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
                try:
                    with st.spinner(
                        "AIが求人票の情報を整理しています..."
                    ):
                        extracted_data = (
                            extract_job_data(
                                job_text
                            )
                        )

                except Exception as error:
                    st.error(
                        "求人票のAI抽出に失敗しました。"
                        "入力内容とAPI設定を確認して、"
                        "もう一度お試しください。"
                    )

                    st.caption(
                        f"エラー内容：{error}"
                    )

                    return

                apply_extracted_job_data(
                    extracted_data
                )

                st.session_state[
                    "job_extracted_data"
                ] = extracted_data

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "form"

                st.session_state[
                    "job_extraction_completed"
                ] = True

                st.rerun()


# ========================================
# 手動入力
# ========================================


def parse_date_value(
    value: str,
) -> date | None:
    """保存済みの日付文字列を日付へ変換する。"""

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    date_formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
    )

    for date_format in date_formats:
        try:
            return datetime.strptime(
                cleaned_value,
                date_format,
            ).date()

        except ValueError:
            continue

    return None


def date_to_text(
    value: date | None,
) -> str:
    """選択された日付を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return value.isoformat()


def parse_time_value(
    value: str,
) -> time | None:
    """保存済みの時刻文字列を時刻へ変換する。"""

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    time_formats = (
        "%H:%M",
        "%H:%M:%S",
    )

    for time_format in time_formats:
        try:
            return datetime.strptime(
                cleaned_value,
                time_format,
            ).time()

        except ValueError:
            continue

    return None


def time_to_text(
    value: time | None,
) -> str:
    """選択された時刻を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return value.strftime("%H:%M")


def parse_integer_value(
    value: str,
    unit: str = "",
) -> int | None:
    """保存済みの整数文字列を数値へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
    )

    if (
        unit
        and cleaned_value.endswith(unit)
    ):
        cleaned_value = cleaned_value[
            :-len(unit)
        ].strip()

    if not cleaned_value:
        return None

    try:
        return int(cleaned_value)

    except ValueError:
        return None


def integer_to_text(
    value: int | None,
) -> str:
    """入力された整数を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return str(value)


def parse_hour_value(
    value: str,
) -> float | None:
    """保存済みの時間文字列を数値へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
        .replace("　", "")
        .replace(" ", "")
        .replace("時間／日", "")
        .replace("時間/日", "")
        .replace("時間", "")
    )

    if not cleaned_value:
        return None

    try:
        return float(cleaned_value)

    except ValueError:
        return None


def hour_to_text(
    value: float | None,
) -> str:
    """入力された時間を保存用文字列へ変換する。"""

    if value is None:
        return ""

    return f"{value:g}"


def parse_monthly_overtime_hours(
    value: str,
) -> int | None:
    """残業時間の文字列を月平均の整数へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
        .replace("　", "")
        .replace(" ", "")
    )

    removable_texts = (
        "1か月あたり",
        "1ヶ月あたり",
        "月平均",
        "時間程度",
        "時間／月",
        "時間/月",
        "約",
        "平均",
        "月",
        "時間",
    )

    for removable_text in removable_texts:
        cleaned_value = cleaned_value.replace(
            removable_text,
            "",
        )

    if not cleaned_value:
        return None

    try:
        return int(cleaned_value)

    except ValueError:
        return None


def parse_yen_value(
    value: str,
) -> int | None:
    """保存済みの金額を円単位へ変換する。"""

    cleaned_value = (
        value.strip()
        .replace(",", "")
        .replace(" ", "")
    )

    if not cleaned_value:
        return None

    if cleaned_value.endswith("万円"):
        number_text = cleaned_value[:-2]

        try:
            return int(
                float(number_text)
                * 10000
            )

        except ValueError:
            return None

    if cleaned_value.endswith("円"):
        cleaned_value = cleaned_value[:-1]

    try:
        return int(cleaned_value)

    except ValueError:
        return None


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
    ] = parse_date_value(
        job.publication_start_date
    )

    st.session_state[
        "job_form_publication_end"
    ] = parse_date_value(
        job.publication_end_date
    )

    st.session_state[
        "job_form_industry"
    ] = job.industry

    st.session_state[
        "job_form_business_description"
    ] = job.business_description

    employee_count_min = parse_integer_value(
        job.employee_count_min,
        "名",
    )

    employee_count_max = parse_integer_value(
        job.employee_count_max,
        "名",
    )

    legacy_employee_count = parse_integer_value(
        job.employee_count,
        "名",
    )

    if (
        employee_count_min is None
        and employee_count_max is None
        and legacy_employee_count is not None
    ):
        employee_count_min = legacy_employee_count
        employee_count_max = legacy_employee_count

    st.session_state[
        "job_form_has_employee_count"
    ] = (
        employee_count_min is not None
        or employee_count_max is not None
    )

    st.session_state[
        "job_form_employee_count_min"
    ] = employee_count_min

    st.session_state[
        "job_form_employee_count_max"
    ] = employee_count_max

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

    planned_hires_value = (
        parse_integer_value(
            job.planned_hires,
            "名",
        )
    )

    st.session_state[
        "job_form_planned_hires"
    ] = planned_hires_value

    st.session_state[
        "job_form_has_planned_hires"
    ] = (
        planned_hires_value
        is not None
    )

    if planned_hires_value is not None:
        st.session_state[
            "job_form_planned_hires_value"
        ] = planned_hires_value

    st.session_state[
        "job_form_recruitment_reason"
    ] = job.recruitment_reason

    st.session_state[
        "job_form_source_name"
    ] = job.source_name

    st.session_state[
        "job_form_source_type"
    ] = (
        job.source_type
        or infer_source_type(
            job.source_name
        )
    )

    st.session_state[
        "job_form_employment_type"
    ] = job.employment_type

    probation_period_status = (
        job.probation_period_status
    )

    if (
        not probation_period_status
        and (
            job.probation_period
            or job.probation_period_months
        )
    ):
        probation_period_status = "あり"

    st.session_state[
        "job_form_probation_period_status"
    ] = probation_period_status

    st.session_state[
        "job_form_probation_period_months"
    ] = parse_integer_value(
        job.probation_period_months
    )

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
    ] = parse_time_value(
        job.start_time
    )

    st.session_state[
        "job_form_end_time"
    ] = parse_time_value(
        job.end_time
    )

    st.session_state[
        "job_form_break_minutes_legacy"
    ] = job.break_minutes

    break_minutes_value = parse_integer_value(
        job.break_minutes,
        "分",
    )

    st.session_state[
        "job_form_has_break_minutes"
    ] = break_minutes_value is not None

    if break_minutes_value is not None:
        st.session_state[
            "job_form_break_minutes_value"
        ] = break_minutes_value

    st.session_state[
        "job_form_scheduled_work_hours_legacy"
    ] = job.scheduled_work_hours

    scheduled_work_hours_value = parse_hour_value(
        job.scheduled_work_hours
    )

    st.session_state[
        "job_form_has_scheduled_work_hours"
    ] = scheduled_work_hours_value is not None

    if scheduled_work_hours_value is not None:
        st.session_state[
            "job_form_scheduled_work_hours_value"
        ] = scheduled_work_hours_value
    st.session_state[
        "job_form_flextime"
    ] = job.flextime

    st.session_state[
        "job_form_overtime_legacy"
    ] = job.overtime

    overtime_value = parse_monthly_overtime_hours(
        job.overtime
    )

    st.session_state[
        "job_form_has_overtime"
    ] = overtime_value is not None

    if overtime_value is not None:
        st.session_state[
            "job_form_overtime_value"
        ] = overtime_value

    st.session_state[
        "job_form_holidays"
    ] = job.holidays

    annual_holidays_value = (
        parse_integer_value(
            job.annual_holidays,
            "日",
        )
    )

    st.session_state[
        "job_form_annual_holidays"
    ] = annual_holidays_value

    st.session_state[
        "job_form_has_annual_holidays"
    ] = (
        annual_holidays_value
        is not None
    )

    if annual_holidays_value is not None:
        st.session_state[
            "job_form_annual_holidays_value"
        ] = annual_holidays_value

    st.session_state[
        "job_form_wage_type"
    ] = job.wage_type

    monthly_salary_min_value = (
        parse_yen_value(
            job.monthly_salary_min
        )
    )

    if monthly_salary_min_value is None:
        monthly_salary_min_value = (
            parse_yen_value(
                job.monthly_salary
            )
        )

    st.session_state[
        "job_form_monthly_salary_min"
    ] = monthly_salary_min_value

    st.session_state[
        "job_form_monthly_salary_max"
    ] = parse_yen_value(
        job.monthly_salary_max
    )

    st.session_state[
        "job_form_base_salary_min"
    ] = parse_yen_value(
        job.base_salary_min
    )

    st.session_state[
        "job_form_base_salary_max"
    ] = parse_yen_value(
        job.base_salary_max
    )

    st.session_state[
        "job_form_monthly_salary"
    ] = job.monthly_salary

    st.session_state[
        "job_form_annual_salary"
    ] = job.annual_salary

    st.session_state[
        "job_form_expected_salary_min"
    ] = parse_integer_value(
        job.expected_salary_min,
        "万円",
    )

    st.session_state[
        "job_form_expected_salary_max"
    ] = parse_integer_value(
        job.expected_salary_max,
        "万円",
    )

    fixed_overtime_system = (
        job.fixed_overtime_system
    )

    if (
        not fixed_overtime_system
        and (
            job.fixed_overtime_hours
            or job.fixed_overtime_pay
            or job.fixed_overtime_pay_min
            or job.fixed_overtime_pay_max
        )
    ):
        fixed_overtime_system = "あり"

    st.session_state[
        "job_form_fixed_overtime_system"
    ] = fixed_overtime_system

    st.session_state[
        "job_form_fixed_overtime_hours"
    ] = parse_integer_value(
        job.fixed_overtime_hours,
        "時間",
    )

    fixed_overtime_pay_min = (
        job.fixed_overtime_pay_min
        or job.fixed_overtime_pay
    )

    st.session_state[
        "job_form_fixed_overtime_pay_min"
    ] = parse_yen_value(
        fixed_overtime_pay_min
    )

    st.session_state[
        "job_form_fixed_overtime_pay_max"
    ] = parse_yen_value(
        job.fixed_overtime_pay_max
    )

    st.session_state[
        "job_form_overtime_extra_pay"
    ] = job.overtime_extra_pay

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

    document_screening_status = (
        job.document_screening_status
    )

    if (
        not document_screening_status
        and job.document_screening
    ):
        document_screening_status = "あり"

    st.session_state[
        "job_form_document_screening_status"
    ] = document_screening_status

    st.session_state[
        "job_form_document_screening"
    ] = job.document_screening

    st.session_state[
        "job_form_interview"
    ] = job.interview

    aptitude_test_status = (
        job.aptitude_test_status
    )

    if (
        not aptitude_test_status
        and job.aptitude_test
    ):
        aptitude_test_status = "あり"

    st.session_state[
        "job_form_aptitude_test_status"
    ] = aptitude_test_status

    st.session_state[
        "job_form_aptitude_test"
    ] = job.aptitude_test

    interview_count_min = parse_integer_value(
        job.interview_count_min,
        "回",
    )

    interview_count_max = parse_integer_value(
        job.interview_count_max,
        "回",
    )

    legacy_interview_count = parse_integer_value(
        job.interview_count,
        "回",
    )

    if (
        interview_count_min is None
        and interview_count_max is None
        and legacy_interview_count is not None
    ):
        interview_count_min = legacy_interview_count
        interview_count_max = legacy_interview_count

    st.session_state[
        "job_form_has_interview_count"
    ] = (
        interview_count_min is not None
        or interview_count_max is not None
    )

    st.session_state[
        "job_form_interview_count_min"
    ] = interview_count_min

    st.session_state[
        "job_form_interview_count_max"
    ] = interview_count_max

    st.session_state[
        "job_form_expected_join_date"
    ] = job.expected_join_date


def render_job_form() -> None:
    """求人情報の入力フォームを表示する。"""

    edit_job_id = st.session_state.get(
        JOB_EDIT_ID_KEY
    )

    return_page = st.session_state.get(
        JOB_FORM_RETURN_PAGE_KEY
    )

    back_button_label = (
        "← 求人一覧へ戻る"
        if (
            edit_job_id is not None
            and return_page == "job_list"
        )
        else "← 登録方法の選択に戻る"
    )

    if st.button(
        back_button_label,
        key="job_form_back",
    ):
        if (
            edit_job_id is not None
            and return_page == "job_list"
        ):
            st.session_state[
                JOB_EDIT_ID_KEY
            ] = None

            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

            st.session_state[
                JOB_FORM_RETURN_PAGE_KEY
            ] = None

            st.query_params["page"] = (
                "job_list"
            )

        else:
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

        st.rerun()

    if edit_job_id is not None:
        st.info(
            f"求人ID {edit_job_id} を編集中です。"
        )

    st.markdown(
        """
        <div class="job-section-title">
            ② AI抽出内容を確認してください
        </div>
        <div class="job-section-description">
            AIが整理した求人情報を確認し、
            誤りや不足があれば修正してください。
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get(
        "job_extraction_completed",
        False,
    ):
        st.info(
            "求人票から取得できた情報を"
            "入力フォームへ反映しました。"
            "内容を確認し、不足項目を入力してください。"
        )

    with st.container(border=True):

        st.markdown("### 求人基本情報")

        company_name = st.text_input(
            "会社名 *",
            key="job_form_company_name",
        )

        job_title = st.text_input(
            "求人名",
            key="job_form_job_title",
        )

        source_type = st.selectbox(
            "紹介経路の種別 *",
            SOURCE_TYPES,
            key="job_form_source_type",
        )

        source_name = st.text_input(
            "紹介経路の具体名 *",
            placeholder=(
                "例：リクルートエージェント、"
                "Indeed、企業採用ページ"
            ),
            key="job_form_source_name",
        )

        job_number = st.text_input(
            "求人番号",
            key="job_form_job_number",
        )

        col1, col2 = st.columns(2)

        with col1:
            publication_start_date = st.date_input(
                "掲載開始日",
                value=None,
                format="YYYY/MM/DD",
                key="job_form_publication_start",
            )

        with col2:
            publication_end_date = st.date_input(
                "掲載終了日",
                value=None,
                format="YYYY/MM/DD",
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
            has_employee_count = st.checkbox(
                "従業員数の記載あり",
                key="job_form_has_employee_count",
            )

            if has_employee_count:
                employee_count_col1, employee_count_col2 = (
                    st.columns(2)
                )

                with employee_count_col1:
                    employee_count_min = st.number_input(
                        "従業員数（下限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：51",
                        key="job_form_employee_count_min",
                    )

                with employee_count_col2:
                    employee_count_max = st.number_input(
                        "従業員数（上限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：100",
                        key="job_form_employee_count_max",
                    )

                st.caption(
                    "単位：名。単一の人数が記載されている場合は、"
                    "下限と上限へ同じ人数を入力します。"
                )

            else:
                employee_count_min = None
                employee_count_max = None

            established_date = st.text_input(
                "設立",
                key="job_form_established_date",
            )

        with col4:
            capital = st.text_input(
                "資本金",
                key="job_form_capital",
            )

            listing_status = st.selectbox(
                "上場区分",
                options_with_current(
                    LISTING_STATUSES,
                    st.session_state.get(
                        "job_form_listing_status",
                        "",
                    ),
                ),
                key="job_form_listing_status",
            )

    with st.container(border=True):

        st.markdown("### 募集内容")

        col5, col6 = st.columns(2)

        with col5:
            occupation = st.text_input(
                "募集ポジション（職種） *",
                key="job_form_occupation",
            )

            department = st.text_input(
                "配属部署",
                key="job_form_department",
            )

        with col6:
            has_planned_hires = st.checkbox(
                "採用予定人数の記載あり",
                value=(
                    st.session_state.get(
                        "job_form_planned_hires"
                    )
                    is not None
                ),
                key="job_form_has_planned_hires",
            )

            if has_planned_hires:
                planned_hires = st.number_input(
                    "採用予定人数",
                    min_value=1,
                    step=1,
                    value=(
                        st.session_state.get(
                            "job_form_planned_hires"
                        )
                        or 1
                    ),
                    key="job_form_planned_hires_value",
                )

                st.caption("単位：名")

            else:
                planned_hires = None

        recruitment_reason = st.text_area(
            "募集背景・採用理由",
            key="job_form_recruitment_reason",
        )

    with st.container(border=True):

        st.markdown("### 仕事内容")

        job_summary = st.text_area(
            "仕事内容・業務概要 *",
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
            employment_type = st.selectbox(
                "雇用形態",
                options_with_current(
                    EMPLOYMENT_TYPES,
                    st.session_state.get(
                        "job_form_employment_type",
                        "",
                    ),
                ),
                key="job_form_employment_type",
            )

            probation_period_status = st.selectbox(
                "試用期間",
                options_with_current(
                    PROBATION_PERIOD_OPTIONS,
                    st.session_state.get(
                        "job_form_probation_period_status",
                        "",
                    ),
                ),
                key="job_form_probation_period_status",
            )

            if probation_period_status == "あり":
                probation_period_months = st.number_input(
                    "試用期間の月数",
                    min_value=1,
                    max_value=60,
                    step=1,
                    value=None,
                    placeholder="例：3",
                    key="job_form_probation_period_months",
                )

                st.caption(
                    "単位：か月。期間が日数で記載されている場合や、"
                    "条件に補足がある場合は下の補足欄へ入力します。"
                )

            else:
                probation_period_months = None

            probation_period = st.text_input(
                "試用期間の補足",
                placeholder=(
                    "例：試用期間中も待遇変更なし、"
                    "試用期間14日間"
                ),
                key="job_form_probation_period",
            )

            prefecture = st.selectbox(
                "都道府県",
                options_with_current(
                    PREFECTURES,
                    st.session_state.get(
                        "job_form_prefecture",
                        "",
                    ),
                ),
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
            transfer_required = st.selectbox(
                "転勤",
                options_with_current(
                    TRANSFER_OPTIONS,
                    st.session_state.get(
                        "job_form_transfer_required",
                        "",
                    ),
                ),
                key="job_form_transfer_required",
            )

            work_style = st.selectbox(
                "勤務形態・働き方",
                options_with_current(
                    WORK_STYLE_OPTIONS,
                    st.session_state.get(
                        "job_form_work_style",
                        "",
                    ),
                ),
                key="job_form_work_style",
            )

            flextime = st.selectbox(
                "フレックスタイム",
                options_with_current(
                    FLEXTIME_OPTIONS,
                    st.session_state.get(
                        "job_form_flextime",
                        "",
                    ),
                ),
                key="job_form_flextime",
            )

            has_overtime = st.checkbox(
                "月平均残業時間の記載あり",
                key="job_form_has_overtime",
            )

            if has_overtime:
                overtime = st.number_input(
                    "月平均残業時間",
                    min_value=0,
                    max_value=744,
                    step=1,
                    value=(
                        st.session_state.get(
                            "job_form_overtime_value"
                        )
                        if st.session_state.get(
                            "job_form_overtime_value"
                        )
                        is not None
                        else 20
                    ),
                    key="job_form_overtime_value",
                )

                st.caption(
                    "単位：時間／月。"
                    "求人票に記載された月平均時間を"
                    "0～744時間で入力してください。"
                )

            else:
                overtime = None

        col11, col12 = st.columns(2)

        with col11:
            start_time = st.time_input(
                "始業時間",
                value=None,
                step=900,
                key="job_form_start_time",
            )

            has_break_minutes = st.checkbox(
                "休憩時間の記載あり",
                key="job_form_has_break_minutes",
            )

            if has_break_minutes:
                break_minutes = st.number_input(
                    "休憩時間",
                    min_value=0,
                    max_value=1440,
                    step=1,
                    value=(
                        st.session_state.get(
                            "job_form_break_minutes_value"
                        )
                        if st.session_state.get(
                            "job_form_break_minutes_value"
                        )
                        is not None
                        else 60
                    ),
                    key="job_form_break_minutes_value",
                )

                st.caption(
                    "単位：分。0～1440分の範囲で"
                    "入力してください。"
                )

            else:
                break_minutes = None

        with col12:
            end_time = st.time_input(
                "終業時間",
                value=None,
                step=900,
                key="job_form_end_time",
            )

            has_scheduled_work_hours = st.checkbox(
                "所定労働時間の記載あり",
                key="job_form_has_scheduled_work_hours",
            )

            if has_scheduled_work_hours:
                scheduled_work_hours = st.number_input(
                    "所定労働時間",
                    min_value=0.0,
                    max_value=24.0,
                    step=0.25,
                    value=(
                        st.session_state.get(
                            "job_form_scheduled_work_hours_value"
                        )
                        if st.session_state.get(
                            "job_form_scheduled_work_hours_value"
                        )
                        is not None
                        else 8.0
                    ),
                    key=(
                        "job_form_"
                        "scheduled_work_hours_value"
                    ),
                )

                st.caption(
                    "単位：時間／日。"
                    "例：7時間30分の場合は7.5と入力します。"
                )

            else:
                scheduled_work_hours = None

        holidays = st.text_input(
            "休日・休暇",
            key="job_form_holidays",
        )

        has_annual_holidays = st.checkbox(
            "年間休日数の記載あり",
            value=(
                st.session_state.get(
                    "job_form_annual_holidays"
                )
                is not None
            ),
            key="job_form_has_annual_holidays",
        )

        if has_annual_holidays:
            annual_holidays = st.number_input(
                "年間休日数",
                min_value=1,
                max_value=366,
                step=1,
                value=(
                    st.session_state.get(
                        "job_form_annual_holidays"
                    )
                    or 120
                ),
                key="job_form_annual_holidays_value",
            )

            st.caption(
                "1年間の休日数を"
                "1～366日の範囲で入力してください。"
            )

        else:
            annual_holidays = None
    with st.container(border=True):

        st.markdown("### 給与・待遇")

        wage_type = st.selectbox(
            "賃金形態",
            options_with_current(
                WAGE_TYPES,
                st.session_state.get(
                    "job_form_wage_type",
                    "",
                ),
            ),
            key="job_form_wage_type",
        )

        st.caption(
            "月給・基本給は円単位、"
            "想定年収は万円単位で入力します。"
        )

        col13, col14 = st.columns(2)

        with col13:
            monthly_salary_min = st.number_input(
                "月給最低額（円）",
                min_value=0,
                step=1000,
                value=None,
                placeholder="例：280000",
                key="job_form_monthly_salary_min",
            )

            base_salary_min = st.number_input(
                "基本給最低額（円）",
                min_value=0,
                step=1000,
                value=None,
                placeholder="例：240000",
                key="job_form_base_salary_min",
            )

            expected_salary_min = st.number_input(
                "想定年収最低額（万円）",
                min_value=0,
                step=10,
                value=None,
                placeholder="例：400",
                key="job_form_expected_salary_min",
            )

            bonus = st.text_input(
                "賞与",
                key="job_form_bonus",
            )

        with col14:
            monthly_salary_max = st.number_input(
                "月給最高額（円）",
                min_value=0,
                step=1000,
                value=None,
                placeholder="例：350000",
                key="job_form_monthly_salary_max",
            )

            base_salary_max = st.number_input(
                "基本給最高額（円）",
                min_value=0,
                step=1000,
                value=None,
                placeholder="例：300000",
                key="job_form_base_salary_max",
            )

            expected_salary_max = st.number_input(
                "想定年収最高額（万円）",
                min_value=0,
                step=10,
                value=None,
                placeholder="例：550",
                key="job_form_expected_salary_max",
            )

            salary_increase = st.text_input(
                "昇給",
                key="job_form_salary_increase",
            )

        st.divider()

        fixed_overtime_system = st.selectbox(
            "固定残業制",
            options_with_current(
                FIXED_OVERTIME_OPTIONS,
                st.session_state.get(
                    "job_form_fixed_overtime_system",
                    "",
                ),
            ),
            key="job_form_fixed_overtime_system",
        )

        if fixed_overtime_system == "あり":
            st.caption(
                "求人票に記載された固定残業時間と"
                "固定残業代を入力してください。"
            )

            fixed_col1, fixed_col2 = st.columns(2)

            with fixed_col1:
                fixed_overtime_hours = st.number_input(
                    "固定残業時間（時間／月）",
                    min_value=0,
                    step=1,
                    value=None,
                    placeholder="例：20",
                    key="job_form_fixed_overtime_hours",
                )

                fixed_overtime_pay_min = st.number_input(
                    "固定残業代最低額（円）",
                    min_value=0,
                    step=1000,
                    value=None,
                    placeholder="例：40000",
                    key="job_form_fixed_overtime_pay_min",
                )

            with fixed_col2:
                fixed_overtime_pay_max = st.number_input(
                    "固定残業代最高額（円）",
                    min_value=0,
                    step=1000,
                    value=None,
                    placeholder="例：60000",
                    key="job_form_fixed_overtime_pay_max",
                )

                overtime_extra_pay = st.selectbox(
                    "固定残業時間の超過分を追加支給",
                    options_with_current(
                        FIXED_OVERTIME_OPTIONS,
                        st.session_state.get(
                            "job_form_overtime_extra_pay",
                            "",
                        ),
                    ),
                    key="job_form_overtime_extra_pay",
                )

            st.caption(
                "固定残業代について求人票に記載がない項目は、"
                "未入力のままで保存できます。"
            )

        else:
            fixed_overtime_hours = None
            fixed_overtime_pay_min = None
            fixed_overtime_pay_max = None
            overtime_extra_pay = ""

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
            document_screening_status = st.selectbox(
                "書類選考",
                options_with_current(
                    SELECTION_STEP_OPTIONS,
                    st.session_state.get(
                        "job_form_document_screening_status",
                        "",
                    ),
                ),
                key="job_form_document_screening_status",
            )

            document_screening = st.text_input(
                "書類選考の補足",
                placeholder=(
                    "例：履歴書・職務経歴書による選考"
                ),
                key="job_form_document_screening",
            )

            aptitude_test_status = st.selectbox(
                "適性検査",
                options_with_current(
                    SELECTION_STEP_OPTIONS,
                    st.session_state.get(
                        "job_form_aptitude_test_status",
                        "",
                    ),
                ),
                key="job_form_aptitude_test_status",
            )

            aptitude_test = st.text_input(
                "適性検査の補足",
                placeholder="例：Web適性検査、SPI",
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

            has_interview_count = st.checkbox(
                "面接回数の記載あり",
                key="job_form_has_interview_count",
            )

            if has_interview_count:
                interview_count_col1, interview_count_col2 = (
                    st.columns(2)
                )

                with interview_count_col1:
                    interview_count_min = st.number_input(
                        "面接回数（下限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：1",
                        key="job_form_interview_count_min",
                    )

                with interview_count_col2:
                    interview_count_max = st.number_input(
                        "面接回数（上限）",
                        min_value=1,
                        step=1,
                        value=None,
                        placeholder="例：2",
                        key="job_form_interview_count_max",
                    )

                st.caption(
                    "単位：回。面接が2回と確定している場合は、"
                    "下限と上限へ同じ回数を入力します。"
                )

            else:
                interview_count_min = None
                interview_count_max = None

    st.divider()

    edit_job_id = st.session_state.get(
        JOB_EDIT_ID_KEY
    )

    save_button_label = (
        "変更内容を確認する"
        if edit_job_id is not None
        else "登録内容を確認する"
    )

    interview_count_error = ""

    if (
        interview_count_min is not None
        and interview_count_max is not None
        and interview_count_min > interview_count_max
    ):
        interview_count_error = (
            "面接回数の下限が上限を超えています。"
        )

    employee_count_error = ""

    if (
        employee_count_min is not None
        and employee_count_max is not None
        and employee_count_min > employee_count_max
    ):
        employee_count_error = (
            "従業員数の下限が上限を超えています。"
        )

    salary_range_errors: list[str] = []

    salary_ranges = (
        (
            monthly_salary_min,
            monthly_salary_max,
            "月給",
        ),
        (
            base_salary_min,
            base_salary_max,
            "基本給",
        ),
        (
            expected_salary_min,
            expected_salary_max,
            "想定年収",
        ),
        (
            fixed_overtime_pay_min,
            fixed_overtime_pay_max,
            "固定残業代",
        ),
    )

    for (
        minimum_value,
        maximum_value,
        salary_label,
    ) in salary_ranges:
        if (
            minimum_value is not None
            and maximum_value is not None
            and minimum_value > maximum_value
        ):
            salary_range_errors.append(
                f"{salary_label}の最低額が"
                "最高額を超えています。"
            )

    if st.button(
        save_button_label,
        key="job_form_save",
        type="primary",
        use_container_width=True,
    ):
        if interview_count_error:
            st.error(interview_count_error)
            return

        if employee_count_error:
            st.error(employee_count_error)
            return

        if salary_range_errors:
            for error in salary_range_errors:
                st.error(error)

            return
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
            source_type=source_type,
            source_name=source_name,

            company_name=company_name,
            job_title=job_title,
            job_number=job_number,
            publication_start_date=date_to_text(
                publication_start_date
            ),
            publication_end_date=date_to_text(
                publication_end_date
            ),
            industry=industry,
            business_description=business_description,
            employee_count_min=integer_to_text(
                employee_count_min
            ),
            employee_count_max=integer_to_text(
                employee_count_max
            ),
            employee_count=(
                integer_to_text(employee_count_min)
                if (
                    employee_count_min is not None
                    and employee_count_min
                    == employee_count_max
                )
                else ""
            ),
            established_date=established_date,
            capital=capital,
            listing_status=listing_status,

            occupation=occupation,
            department=department,
            planned_hires=integer_to_text(
                planned_hires
            ),
            recruitment_reason=recruitment_reason,

            job_summary=job_summary,
            responsibility_scope=responsibility_scope,
            customers=customers,
            internal_stakeholders=internal_stakeholders,
            external_partners=external_partners,
            goals_kpi=goals_kpi,
            expected_results=expected_results,

            employment_type=employment_type,
            probation_period_status=(
                probation_period_status
            ),
            probation_period_months=integer_to_text(
                probation_period_months
            ),
            probation_period=probation_period,
            prefecture=prefecture,
            municipality=municipality,
            nearest_station=nearest_station,
            transfer_required=transfer_required,
            work_style=work_style,
            start_time=time_to_text(
                start_time
            ),
            end_time=time_to_text(
                end_time
            ),
            break_minutes=(
                integer_to_text(break_minutes)
                if break_minutes is not None
                else st.session_state.get(
                    "job_form_break_minutes_legacy",
                    "",
                )
            ),
            scheduled_work_hours=(
                hour_to_text(scheduled_work_hours)
                if scheduled_work_hours is not None
                else st.session_state.get(
                    "job_form_scheduled_work_hours_legacy",
                    "",
                )
            ),
            flextime=flextime,
            overtime=(
                integer_to_text(overtime)
                if overtime is not None
                else st.session_state.get(
                    "job_form_overtime_legacy",
                    "",
                )
            ),
            holidays=holidays,
            annual_holidays=integer_to_text(
                annual_holidays
            ),

            wage_type=wage_type,
            monthly_salary_min=integer_to_text(
                monthly_salary_min
            ),
            monthly_salary_max=integer_to_text(
                monthly_salary_max
            ),
            base_salary_min=integer_to_text(
                base_salary_min
            ),
            base_salary_max=integer_to_text(
                base_salary_max
            ),

            monthly_salary=st.session_state.get(
                "job_form_monthly_salary",
                "",
            ),
            annual_salary=st.session_state.get(
                "job_form_annual_salary",
                "",
            ),
            expected_salary_min=integer_to_text(
                expected_salary_min
            ),
            expected_salary_max=integer_to_text(
                expected_salary_max
            ),
            fixed_overtime_system=fixed_overtime_system,
            fixed_overtime_pay_min=integer_to_text(
                fixed_overtime_pay_min
            ),
            fixed_overtime_pay_max=integer_to_text(
                fixed_overtime_pay_max
            ),
            overtime_extra_pay=overtime_extra_pay,

            fixed_overtime_hours=integer_to_text(
                fixed_overtime_hours
            ),
            fixed_overtime_pay=integer_to_text(
                fixed_overtime_pay_min
            ),
            bonus=bonus,
            salary_increase=salary_increase,
            incentive=incentive,

            social_insurance=social_insurance,
            commuting_allowance=commuting_allowance,
            housing_allowance=housing_allowance,
            retirement_plan=retirement_plan,
            qualification_support=qualification_support,
            training_program=training_program,

            document_screening_status=(
                document_screening_status
            ),
            document_screening=document_screening,
            interview=interview,
            aptitude_test_status=(
                aptitude_test_status
            ),
            aptitude_test=aptitude_test,
            interview_count_min=integer_to_text(
                interview_count_min
            ),
            interview_count_max=integer_to_text(
                interview_count_max
            ),
            interview_count=(
                integer_to_text(interview_count_min)
                if (
                    interview_count_min is not None
                    and interview_count_min
                    == interview_count_max
                )
                else ""
            ),
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

        st.session_state[
            JOB_CONFIRM_DATA_KEY
        ] = job

        st.session_state[
            JOB_FORM_STEP_KEY
        ] = "confirm"

        st.rerun()


# ========================================
# 登録内容の最終確認
# ========================================

def render_job_confirmation() -> None:
    """保存前の求人情報を確認する画面。"""

    job = st.session_state.get(
        JOB_CONFIRM_DATA_KEY
    )

    if job is None:
        st.error(
            "確認する求人情報を取得できませんでした。"
        )

        if st.button(
            "入力画面へ戻る",
            key="job_confirm_missing_back",
        ):
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "form"

            st.session_state[
                "job_extraction_completed"
            ] = False

            st.rerun()

        return

    st.markdown(
        """
        <div class="job-section-title">
            ③ 登録内容を確認してください
        </div>
        <div class="job-section-description">
            以下の内容で求人情報を登録します。
            誤りがある場合は入力画面へ戻って修正してください。
        </div>
        """,
        unsafe_allow_html=True,
    )

    def show_value(
        label: str,
        value,
    ) -> None:
        """確認用にラベルと値を表示する。"""

        if isinstance(value, list):
            display_value = "\n".join(
                f"・{item}"
                for item in value
                if str(item).strip()
            )
        else:
            display_value = str(
                value or ""
            ).strip()

        if not display_value:
            display_value = "未入力"

        st.markdown(f"**{label}**")
        st.text(display_value)

    with st.container(border=True):
        st.markdown("### 求人基本情報")

        confirm_col1, confirm_col2 = st.columns(2)

        with confirm_col1:
            show_value(
                "会社名",
                job.company_name,
            )
            show_value(
                "求人名",
                job.job_title,
            )
            show_value(
                "募集ポジション（職種）",
                job.occupation,
            )
            show_value(
                "業種",
                job.industry,
            )

        with confirm_col2:
            show_value(
                "紹介経路の種別",
                job.source_type,
            )
            show_value(
                "紹介経路の具体名",
                job.source_name,
            )
            show_value(
                "求人番号",
                job.job_number,
            )
            show_value(
                "配属部署",
                job.department,
            )

    with st.container(border=True):
        st.markdown("### 仕事内容・応募条件")

        show_value(
            "仕事内容・業務概要",
            job.job_summary,
        )
        show_value(
            "具体的な業務内容",
            job.job_details,
        )
        show_value(
            "必須経験",
            job.required_experience,
        )
        show_value(
            "必須スキル",
            job.required_skills,
        )
        show_value(
            "必須資格",
            job.required_qualifications,
        )

    with st.container(border=True):
        st.markdown("### 勤務条件")

        condition_col1, condition_col2 = (
            st.columns(2)
        )

        with condition_col1:
            show_value(
                "雇用形態",
                job.employment_type,
            )
            show_value(
                "勤務地",
                (
                    f"{job.prefecture}"
                    f"{job.municipality}"
                ),
            )
            show_value(
                "勤務形態・働き方",
                job.work_style,
            )
            show_value(
                "転勤",
                job.transfer_required,
            )

        with condition_col2:
            show_value(
                "始業時間",
                job.start_time,
            )
            show_value(
                "終業時間",
                job.end_time,
            )
            show_value(
                "月平均残業時間",
                job.overtime,
            )
            show_value(
                "年間休日数",
                job.annual_holidays,
            )

    with st.container(border=True):
        st.markdown("### 給与・選考")

        salary_col, selection_col = st.columns(2)

        with salary_col:
            show_value(
                "賃金形態",
                job.wage_type,
            )
            show_value(
                "想定年収最低額（万円）",
                job.expected_salary_min,
            )
            show_value(
                "想定年収最高額（万円）",
                job.expected_salary_max,
            )
            show_value(
                "固定残業制",
                job.fixed_overtime_system,
            )

        with selection_col:
            show_value(
                "書類選考",
                job.document_screening_status,
            )
            show_value(
                "適性検査",
                job.aptitude_test_status,
            )
            show_value(
                "面接回数（下限）",
                job.interview_count_min,
            )
            show_value(
                "面接回数（上限）",
                job.interview_count_max,
            )

    if job.not_listed_fields:
        with st.container(border=True):
            st.markdown(
                "### 未入力・確認が必要な項目"
            )

            show_value(
                "求人票から確認できなかった内容",
                job.not_listed_fields,
            )

    confirm_back_col, confirm_save_col = (
        st.columns(2)
    )

    with confirm_back_col:
        if st.button(
            "入力画面へ戻って修正する",
            key="job_confirm_back",
            use_container_width=True,
        ):
            apply_extracted_job_data(
                asdict(job)
            )

            st.session_state[
                "job_form_source_type"
            ] = job.source_type

            st.session_state[
                "job_form_source_name"
            ] = job.source_name

            st.session_state[
                "job_form_publication_start"
            ] = parse_date_value(
                job.publication_start_date
            )

            st.session_state[
                "job_form_publication_end"
            ] = parse_date_value(
                job.publication_end_date
            )

            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "form"

            st.rerun()

    with confirm_save_col:
        if st.button(
            "この内容で登録する",
            key="job_confirm_save",
            type="primary",
            use_container_width=True,
        ):
            edit_job_id = st.session_state.get(
                JOB_EDIT_ID_KEY
            )

            if edit_job_id is not None:
                errors = update_job_data(
                    edit_job_id,
                    job,
                )

                if errors:
                    for error in errors:
                        st.error(error)

                    return

                move_to_job_completion_after_ai_evaluation(
                    message="求人情報を更新しました。",
                    job_id=edit_job_id,
                )

            duplicate_type, existing_job_id, errors = (
                save_job_data(job)
            )

            if errors:
                for error in errors:
                    st.error(error)

                return

            if duplicate_type == DUPLICATE_NONE:
                job_id, create_errors = (
                    create_job_data(job)
                )

                if create_errors:
                    for error in create_errors:
                        st.error(error)

                    return

                move_to_job_completion_after_ai_evaluation(
                    message="求人情報を保存しました。",
                    job_id=job_id,
                )

            if duplicate_type == DUPLICATE_POSSIBLE:
                if existing_job_id is None:
                    st.error(
                        "類似する求人情報を取得できませんでした。"
                    )
                    return

                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = job

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = existing_job_id

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = DUPLICATE_POSSIBLE

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "duplicate"

                st.rerun()

            if duplicate_type == DUPLICATE_EXACT:
                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = job

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = existing_job_id

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = DUPLICATE_EXACT

                st.session_state[
                    JOB_FORM_STEP_KEY
                ] = "duplicate"

                st.rerun()

            if (
                duplicate_type
                == DUPLICATE_DIFFERENT_SOURCE
            ):
                if existing_job_id is None:
                    st.error(
                        "登録済み求人を取得できませんでした。"
                    )
                    return

                source_errors = add_job_source_data(
                    existing_job_id,
                    job,
                )

                if source_errors:
                    for error in source_errors:
                        st.error(error)

                    return

                move_to_job_completion(
                    message=(
                        "登録済みの求人へ、"
                        "新しい紹介経路を追加しました。"
                    ),
                    job_id=existing_job_id,
                    note=(
                        "二重応募を避けるため、"
                        "応募前に紹介元のエージェント等へ"
                        "応募経路を確認してください。"
                    ),
                )


def move_to_job_completion(
    message: str,
    job_id: int,
    note: str = "",
) -> None:
    """保存完了画面へ移動する。"""

    st.session_state[
        JOB_CONFIRM_DATA_KEY
    ] = None

    st.session_state[
        JOB_COMPLETE_MESSAGE_KEY
    ] = message

    st.session_state[
        JOB_COMPLETE_NOTE_KEY
    ] = note

    st.session_state[
        JOB_COMPLETE_JOB_ID_KEY
    ] = job_id

    st.session_state[
        JOB_FORM_STEP_KEY
    ] = "complete"

    st.rerun()


def move_to_job_completion_after_ai_evaluation(
    message: str,
    job_id: int,
) -> None:
    """求人保存後にAI評価を行い、完了画面へ移動する。"""

    with st.spinner(
        "求人情報を保存しました。"
        "AIマッチング評価を行っています。"
    ):
        (
            evaluation,
            evaluation_error,
        ) = automatically_evaluate_and_save_job(
            job_id=job_id
        )

    if evaluation_error:
        move_to_job_completion(
            message=message,
            job_id=job_id,
            note=evaluation_error,
        )
        return

    completion_message = (
        f"{message.rstrip('。')}。"
        "AIマッチング評価も完了しました。"
    )

    if (
        evaluation is not None
        and evaluation.is_provisional
    ):
        completion_message = (
            f"{completion_message}"
            "現在評価できた情報："
            f"{evaluation.evaluation_coverage}%"
        )

    move_to_job_completion(
        message=completion_message,
        job_id=job_id,
    )


def render_job_completion() -> None:
    """求人情報の保存完了画面を表示する。"""

    message = st.session_state.get(
        JOB_COMPLETE_MESSAGE_KEY
    )

    note = st.session_state.get(
        JOB_COMPLETE_NOTE_KEY,
        "",
    )

    job_id = st.session_state.get(
        JOB_COMPLETE_JOB_ID_KEY
    )

    if not message or job_id is None:
        st.error(
            "保存した求人情報を取得できませんでした。"
        )

        if st.button(
            "求人一覧へ戻る",
            key="job_complete_error_back",
        ):
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

            st.query_params["page"] = "job_list"
            st.rerun()

        return

    st.success(message)

    if note:
        st.warning(note)

    st.caption(
        f"求人ID：{job_id}"
    )

    detail_col, list_col = st.columns(2)

    with detail_col:
        if st.button(
            "登録した求人を確認する",
            key="job_complete_to_detail",
            type="primary",
            use_container_width=True,
        ):
            st.query_params["page"] = "job_detail"
            st.query_params["job_id"] = str(job_id)
            st.rerun()

    with list_col:
        if st.button(
            "求人一覧へ戻る",
            key="job_complete_to_list",
            use_container_width=True,
        ):
            st.query_params["page"] = "job_list"
            st.query_params.pop("job_id", None)
            st.rerun()


def render_duplicate_confirmation() -> None:
    """登録済みの同一求人を案内する画面。"""

    duplicate_type = st.session_state.get(
        JOB_DUPLICATE_TYPE_KEY
    )

    pending_job = st.session_state.get(
        JOB_PENDING_DATA_KEY
    )

    existing_job_id = st.session_state.get(
        JOB_DUPLICATE_ID_KEY
    )

    if (
        duplicate_type
        not in (
            DUPLICATE_EXACT,
            DUPLICATE_POSSIBLE,
        )
        or pending_job is None
        or existing_job_id is None
    ):
        st.error(
            "重複確認に必要な情報を取得できませんでした。"
        )

        if st.button(
            "求人登録へ戻る",
            key="duplicate_missing_back",
        ):
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

            st.session_state[
                JOB_PENDING_DATA_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_ID_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_TYPE_KEY
            ] = None

            st.rerun()

        return

    existing_job = load_job(
        existing_job_id
    )

    if existing_job is None:
        st.error(
            "登録済みの求人情報を取得できませんでした。"
        )
        return

    if duplicate_type == DUPLICATE_POSSIBLE:
        st.warning(
            "同じ求人の可能性がある求人が見つかりました。"
            "内容を確認して、同じ求人かどうか判断してください。"
        )

        st.markdown("### 類似する登録済み求人")

    else:
        st.warning(
            "この求人はすでに登録されています。"
            "同じ求人を重複して登録することはできません。"
        )

        st.markdown("### 登録済みの求人")

    with st.container(border=True):
        st.markdown(
            f"**{existing_job.company_name}**"
        )

        st.write(
            existing_job.job_title
            or existing_job.occupation
            or "求人名未入力"
        )

        st.caption(
            f"紹介経路："
            f"{existing_job.source_type}／"
            f"{existing_job.source_name}"
        )

        st.caption(
            f"求人ID：{existing_job_id}"
        )

    differences = compare_jobs(
        existing_job,
        pending_job,
    )

    if differences:
        st.markdown(
            "### 登録済み情報との違い"
        )

        st.caption(
            "今回入力した内容には以下の違いがあります。"
            "この画面から既存求人を上書きすることはありません。"
        )

        comparison_data = [
            {
                "項目": label,
                "登録済み情報": old_value,
                "今回の入力": new_value,
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
            "登録済み情報と今回の入力内容は同じです。"
        )

    if duplicate_type == DUPLICATE_POSSIBLE:
        st.markdown("### この求人をどう登録しますか？")

        st.caption(
            "同じ求人で紹介経路だけが異なる場合は、"
            "既存求人へ紹介経路を追加してください。"
        )

        same_job_col, new_job_col = st.columns(2)

        with same_job_col:
            if st.button(
                "同じ求人として紹介経路を追加する",
                key="possible_add_source",
                type="primary",
                use_container_width=True,
            ):
                source_errors = add_job_source_data(
                    existing_job_id,
                    pending_job,
                )

                if source_errors:
                    for error in source_errors:
                        st.error(error)

                    return

                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = None

                st.session_state[
                    JOB_CONFIRM_DATA_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = None

                move_to_job_completion(
                    message=(
                        "登録済みの求人へ、"
                        "新しい紹介経路を追加しました。"
                    ),
                    job_id=existing_job_id,
                    note=(
                        "二重応募を避けるため、"
                        "応募前に紹介元のエージェント等へ"
                        "応募経路を確認してください。"
                    ),
                )

        with new_job_col:
            if st.button(
                "別の求人として登録する",
                key="possible_register_as_new",
                use_container_width=True,
            ):
                job_id, create_errors = create_job_data(
                    pending_job
                )

                if create_errors:
                    for error in create_errors:
                        st.error(error)

                    return

                st.session_state[
                    JOB_PENDING_DATA_KEY
                ] = None

                st.session_state[
                    JOB_CONFIRM_DATA_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_ID_KEY
                ] = None

                st.session_state[
                    JOB_DUPLICATE_TYPE_KEY
                ] = None

                move_to_job_completion_after_ai_evaluation(
                    message="別の求人として保存しました。",
                    job_id=job_id,
                )

    detail_col, back_col = st.columns(2)

    with detail_col:
        if st.button(
            "登録済みの求人を確認する",
            key="duplicate_open_existing",
            type="primary",
            use_container_width=True,
        ):
            st.session_state[
                JOB_PENDING_DATA_KEY
            ] = None

            st.session_state[
                JOB_CONFIRM_DATA_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_ID_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_TYPE_KEY
            ] = None

            st.query_params["page"] = (
                "job_detail"
            )

            st.query_params["job_id"] = str(
                existing_job_id
            )

            st.rerun()

    with back_col:
        if st.button(
            "入力画面へ戻る",
            key="duplicate_back_to_form",
            use_container_width=True,
        ):
            apply_extracted_job_data(
                asdict(pending_job)
            )

            st.session_state[
                "job_form_source_type"
            ] = pending_job.source_type

            st.session_state[
                "job_form_source_name"
            ] = pending_job.source_name

            st.session_state[
                "job_form_publication_start"
            ] = parse_date_value(
                pending_job.publication_start_date
            )

            st.session_state[
                "job_form_publication_end"
            ] = parse_date_value(
                pending_job.publication_end_date
            )

            st.session_state[
                JOB_PENDING_DATA_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_ID_KEY
            ] = None

            st.session_state[
                JOB_DUPLICATE_TYPE_KEY
            ] = None

            st.session_state[
                JOB_CONFIRM_DATA_KEY
            ] = pending_job

            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "form"

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

    current_step = st.session_state[
        JOB_FORM_STEP_KEY
    ]

    if current_step == "form":
        render_job_form()
        return

    if current_step == "confirm":
        render_job_confirmation()
        return

    if current_step == "complete":
        render_job_completion()
        return

    if current_step == "duplicate":
        render_duplicate_confirmation()
        return

    if current_step == "source":
        if st.button(
            "← 登録方法の選択に戻る",
            key="job_source_back",
        ):
            st.session_state[
                JOB_FORM_STEP_KEY
            ] = "select"

            st.rerun()

        st.markdown(
            """
            <div class="job-page-title">
                求人を登録する
            </div>
            <div class="job-page-description">
                登録元の情報を入力してください。
            </div>
            """,
            unsafe_allow_html=True,
        )

        mode = st.session_state[
            JOB_REGISTRATION_MODE_KEY
        ]

        if mode == "url":
            render_url_registration()

        elif mode == "text":
            render_text_registration()

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

    render_method_selection()