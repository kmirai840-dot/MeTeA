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