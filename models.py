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