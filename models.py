from dataclasses import dataclass
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