"""基本情報の入力確認とデータ作成を担当する。"""

from datetime import date

from data.master_data import GENDER_LABELS, PREFECTURES
from database.repositories.draft_repository import get_draft, save_draft
from database.repositories.home_activity_repository import save_general_activity
from database.repositories.user_repository import (
    get_user_profile,
    get_user_profile_updated_at,
    save_user_profile,
)
from models import BasicInfo
from services.current_user_service import get_current_user_id
from services.job_matching_cache_service import (
    invalidate_current_user_job_evaluations,
)


MAX_NAME_LENGTH = 30
MAX_MUNICIPALITY_LENGTH = 50
MAX_STATION_NAME_LENGTH = 100
BASIC_INFO_FORM_NAME = "basic_info"


def validate_basic_info(
    family_name: str,
    given_name: str,
    gender: str | None,
    birth_year: int | None,
    birth_month: int | None,
    birth_day: int | None,
    prefecture: str | None,
    municipality: str,
    nearest_station: str,
    nearest_station_place_id: str = "",
) -> tuple[BasicInfo | None, dict[str, str]]:
    """基本情報を確認し、正常なデータまたはエラー一覧を返す。"""

    errors: dict[str, str] = {}

    normalized_family_name = family_name.strip()
    normalized_given_name = given_name.strip()
    normalized_municipality = municipality.strip()
    normalized_nearest_station = nearest_station.strip()
    normalized_nearest_station_place_id = (
        nearest_station_place_id.strip()
    )

    # 姓
    if not normalized_family_name:
        errors["family_name"] = "姓を入力してください"
    elif len(normalized_family_name) > MAX_NAME_LENGTH:
        errors["family_name"] = (
            f"姓は{MAX_NAME_LENGTH}文字以内で入力してください"
        )

    # 名
    if not normalized_given_name:
        errors["given_name"] = "名を入力してください"
    elif len(normalized_given_name) > MAX_NAME_LENGTH:
        errors["given_name"] = (
            f"名は{MAX_NAME_LENGTH}文字以内で入力してください"
        )

    # 性別
    if gender is None or gender not in GENDER_LABELS:
        errors["gender"] = "性別を選択してください"

    # 生年月日の必須確認
    if birth_year is None:
        errors["birth_year"] = "生年月日の年を選択してください"

    if birth_month is None:
        errors["birth_month"] = "生年月日の月を選択してください"

    if birth_day is None:
        errors["birth_day"] = "生年月日の日を選択してください"

    birth_date_value: date | None = None

    # 年・月・日がすべて選択された場合だけ、日付へ変換する
    if (
        birth_year is not None
        and birth_month is not None
        and birth_day is not None
    ):
        try:
            birth_date_value = date(
                birth_year,
                birth_month,
                birth_day,
            )
        except ValueError:
            errors["birth_date"] = (
                "正しい生年月日を選択してください"
            )
        else:
            if birth_date_value >= date.today():
                errors["birth_date"] = (
                    "今日以降の日付は選択できません"
                )

    # 都道府県
    if prefecture is None or prefecture not in PREFECTURES:
        errors["prefecture"] = (
            "都道府県を選択してください"
        )

    # 市区町村
    if not normalized_municipality:
        errors["municipality"] = (
            "市区町村を入力してください"
        )
    elif len(normalized_municipality) > MAX_MUNICIPALITY_LENGTH:
        errors["municipality"] = (
            f"市区町村は{MAX_MUNICIPALITY_LENGTH}文字以内で入力してください"
        )

    # 現在の最寄駅
    if (
        not normalized_nearest_station
        or not normalized_nearest_station_place_id
    ):
        errors["nearest_station"] = (
            "駅を検索し、候補から現在の最寄駅を選択してください"
        )
    elif len(normalized_nearest_station) > MAX_STATION_NAME_LENGTH:
        errors["nearest_station"] = (
            f"現在の最寄駅は{MAX_STATION_NAME_LENGTH}文字以内で入力してください"
        )

    # エラーが1件でもあれば、保存用データは作成しない
    if errors:
        return None, errors

    # ここへ到達した時点で必須項目はすべて確認済み
    assert gender is not None
    assert birth_date_value is not None
    assert prefecture is not None

    basic_info = BasicInfo(
        family_name=normalized_family_name,
        given_name=normalized_given_name,
        gender=gender,
        birth_date=birth_date_value,
        prefecture=prefecture,
        municipality=normalized_municipality,
        nearest_station=normalized_nearest_station,
        nearest_station_place_id=(
            normalized_nearest_station_place_id
        ),
    )

    return basic_info, {}


def save_basic_info_draft(
    draft_data: dict[str, object],
) -> None:
    """基本情報の入力途中データを保存する。"""

    save_draft(
        user_id=get_current_user_id(),
        form_name=BASIC_INFO_FORM_NAME,
        draft_data=draft_data,
    )


def load_basic_info_draft() -> dict[str, object] | None:
    """基本情報の入力途中データを取得する。"""

    return get_draft(
        user_id=get_current_user_id(),
        form_name=BASIC_INFO_FORM_NAME,
    )


def save_basic_info(
    basic_info: BasicInfo,
) -> None:
    """基本情報を正式保存する。"""

    user_id = get_current_user_id()
    saved_basic_info = get_user_profile(
        user_id=user_id,
    )

    save_user_profile(
        user_id=user_id,
        basic_info=basic_info,
        draft_form_name=BASIC_INFO_FORM_NAME,
    )

    if saved_basic_info != basic_info:
        save_general_activity(
            user_id,
            "basic_info_updated",
            "基本情報を更新しました",
            target_page="basic_info",
            icon_name="user.svg",
        )
        invalidate_current_user_job_evaluations(
            reason="基本情報が変更されました。",
        )


def load_basic_info() -> BasicInfo | None:
    """正式保存済みの基本情報を取得する。"""

    return get_user_profile(
        user_id=get_current_user_id(),
    )


def load_basic_info_updated_at() -> str | None:
    """基本情報の最終更新日時を返す。"""
    return get_user_profile_updated_at(user_id=get_current_user_id())
