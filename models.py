from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class BasicInfo:
    """入力確認を通過した基本情報を保持するクラス。"""

    family_name: str
    given_name: str
    gender: str
    birth_date: date
    prefecture: str
    municipality: str


# ========================================
# 希望条件
# ========================================
@dataclass(frozen=True)
class HopeCondition:
    """入力確認を通過した希望条件を保持するクラス。"""

    minimum_salary: int
    desired_salary: int
    ideal_salary: int
    commute_minutes: int
    transfer_condition: str
    commute_priority: str
    transfer_priority: str
    overtime_limit: int
    overtime_priority: str
    start_time: str
    start_time_priority: str
    end_time: str
    end_time_priority: str
    shift_work: str
    shift_work_priority: str
    night_work: str
    night_work_priority: str
    holiday_priority: str
    annual_holidays: int
    annual_holiday_priority: str
    available_date: date | None
    other_jobs: str
    other_conditions: str

@dataclass(frozen=True)
class HopeConditionItem:
    """複数登録できる希望条件を1件ずつ保持するクラス。"""

    condition_type: str
    condition_value: str
    priority: str
    rank: int | None = None
    detail_value: str | None = None


# ========================================
# 就活の軸
# ========================================
@dataclass(frozen=True)
class JobHuntingAxis:
    """入力確認を通過した就活の軸を1件保持するクラス。"""

    axis_title: str
    axis_description: str
    priority_rank: int
    source_type: str


# ========================================
# 価値観
# ========================================
@dataclass(frozen=True)
class WorkValueRanking:
    """順位付きで選択した価値観回答を1件保持するクラス。"""

    question_type: str
    selected_value: str
    priority_rank: int
    custom_value: str | None = None


@dataclass(frozen=True)
class WorkValueDetail:
    """価値観画面の自由記述回答を1件保持するクラス。"""

    detail_type: str
    detail_text: str


@dataclass(frozen=True)
class WorkStyleAnswer:
    """仕事の進め方に関する5段階回答を1件保持するクラス。"""

    question_type: str
    answer_score: int


# ========================================
# 職務経歴
# ========================================
@dataclass(frozen=True)
class Career:
    """1社分の職務経歴を保持するクラス。"""

    company_name: str
    employment_type: str
    industry: str
    start_year: int
    start_month: int
    end_year: int | None
    end_month: int | None
    is_current: bool
    display_order: int


@dataclass(frozen=True)
class CareerHistory:
    """1社内の部署・役割ごとの経歴を保持するクラス。"""

    department: str
    position: str
    occupation: str
    start_year: int
    start_month: int
    end_year: int | None
    end_month: int | None
    job_description: str
    achievements: str
    display_order: int

# ========================================
# 求人情報
# ========================================
@dataclass
class Job:
    """登録した求人1件分の情報を保持するクラス。"""

    # ------------------------------------
    # 情報元
    # ------------------------------------
    registration_method: str = ""
    source_url: str = ""
    source_text: str = ""
    acquired_at: str = ""
    source_type: str = ""
    source_name: str = ""

    # ------------------------------------
    # 求人基本情報
    # ------------------------------------
    company_name: str = ""
    job_title: str = ""
    job_number: str = ""
    publication_start_date: str = ""
    publication_end_date: str = ""
    industry: str = ""
    business_description: str = ""
    employee_count: str = ""
    established_date: str = ""
    capital: str = ""
    listing_status: str = ""

    # ------------------------------------
    # 募集内容
    # ------------------------------------
    occupation: str = ""
    department: str = ""
    planned_hires: str = ""
    recruitment_reason: str = ""

    # ------------------------------------
    # 仕事内容
    # ------------------------------------
    job_summary: str = ""
    job_details: list[str] = field(
        default_factory=list
    )
    responsibility_scope: str = ""
    customers: str = ""
    internal_stakeholders: str = ""
    external_partners: str = ""
    goals_kpi: str = ""
    expected_results: str = ""

    # ------------------------------------
    # 応募要件
    # ------------------------------------
    required_experience: list[str] = field(
        default_factory=list
    )
    required_skills: list[str] = field(
        default_factory=list
    )
    required_qualifications: list[str] = field(
        default_factory=list
    )
    preferred_experience: list[str] = field(
        default_factory=list
    )
    preferred_skills: list[str] = field(
        default_factory=list
    )
    desired_personality: list[str] = field(
        default_factory=list
    )

    # ------------------------------------
    # 勤務条件
    # ------------------------------------
    employment_type: str = ""
    probation_period: str = ""
    prefecture: str = ""
    municipality: str = ""
    nearest_station: str = ""
    transfer_required: str = ""
    work_style: str = ""
    start_time: str = ""
    end_time: str = ""
    break_minutes: str = ""
    scheduled_work_hours: str = ""
    flextime: str = ""
    overtime: str = ""
    holidays: str = ""
    annual_holidays: str = ""

    # ------------------------------------
    # 給与・待遇
    # ------------------------------------
    monthly_salary: str = ""
    annual_salary: str = ""
    expected_salary_min: str = ""
    expected_salary_max: str = ""
    fixed_overtime_hours: str = ""
    fixed_overtime_pay: str = ""
    bonus: str = ""
    salary_increase: str = ""
    incentive: str = ""

    # ------------------------------------
    # 福利厚生
    # ------------------------------------
    social_insurance: str = ""
    commuting_allowance: str = ""
    housing_allowance: str = ""
    retirement_plan: str = ""
    qualification_support: str = ""
    training_program: str = ""

    # ------------------------------------
    # 選考情報
    # ------------------------------------
    document_screening: str = ""
    interview: str = ""
    aptitude_test: str = ""
    interview_count: str = ""
    expected_join_date: str = ""

    # ------------------------------------
    # 情報取得状態
    # ------------------------------------
    not_listed_fields: list[str] = field(
        default_factory=list
    )