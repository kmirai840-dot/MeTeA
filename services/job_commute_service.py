"""求人ごとの電車移動時間に関する処理を担当する。"""

from datetime import date
from urllib.parse import urlencode

from database.repositories.job_commute_repository import (
    get_job_commute_check,
    save_job_commute_check,
)
from models import JobCommuteCheck
from services.current_user_service import get_current_user_id


GOOGLE_MAPS_DIRECTIONS_URL = (
    "https://www.google.com/maps/dir/"
)
MAX_TRAIN_COMMUTE_MINUTES = 600


def build_google_maps_transit_url(
    origin_station_name: str,
    destination_station_name: str,
) -> str:
    """駅間の公共交通経路を確認するGoogleマップURLを作る。"""

    normalized_origin = origin_station_name.strip()
    normalized_destination = (
        destination_station_name.strip()
    )

    if not normalized_origin or not normalized_destination:
        return ""

    query = urlencode(
        {
            "api": "1",
            "origin": normalized_origin,
            "destination": normalized_destination,
            "travelmode": "transit",
        }
    )

    return f"{GOOGLE_MAPS_DIRECTIONS_URL}?{query}"


def validate_train_commute_minutes(
    duration_minutes: int | None,
) -> str | None:
    """電車移動時間を確認し、エラー文またはNoneを返す。"""

    if duration_minutes is None:
        return "電車移動時間を入力してください"

    if duration_minutes < 0:
        return "電車移動時間は0分以上で入力してください"

    if duration_minutes > MAX_TRAIN_COMMUTE_MINUTES:
        return (
            "電車移動時間は"
            f"{MAX_TRAIN_COMMUTE_MINUTES}分以内で入力してください"
        )

    return None


def save_manual_job_commute(
    job_id: int,
    origin_station_name: str,
    origin_station_place_id: str,
    destination_station_name: str,
    duration_minutes: int | None,
) -> JobCommuteCheck:
    """利用者が確認した電車移動時間を保存する。"""

    normalized_origin_name = origin_station_name.strip()
    normalized_origin_place_id = (
        origin_station_place_id.strip()
    )
    normalized_destination_name = (
        destination_station_name.strip()
    )

    if not normalized_origin_name:
        raise ValueError(
            "基本情報で現在の最寄駅を登録してください"
        )

    if not normalized_origin_place_id:
        raise ValueError(
            "基本情報で現在の最寄駅を検索し、"
            "候補から選び直してください"
        )

    if not normalized_destination_name:
        raise ValueError(
            "求人情報に勤務地の最寄駅が登録されていません"
        )

    validation_error = validate_train_commute_minutes(
        duration_minutes,
    )

    if validation_error is not None:
        raise ValueError(validation_error)

    assert duration_minutes is not None

    commute_check = JobCommuteCheck(
        job_id=job_id,
        origin_station_name=normalized_origin_name,
        origin_station_place_id=(
            normalized_origin_place_id
        ),
        destination_station_name=(
            normalized_destination_name
        ),
        duration_minutes=duration_minutes,
        source_type="manual",
        checked_at=date.today().isoformat(),
    )

    save_job_commute_check(
        user_id=get_current_user_id(),
        commute_check=commute_check,
    )

    return commute_check


def load_current_job_commute(
    job_id: int,
    current_origin_station_place_id: str,
    current_destination_station_name: str,
) -> JobCommuteCheck | None:
    """現在の駅情報と一致する保存済み電車時間を取得する。"""

    commute_check = get_job_commute_check(
        user_id=get_current_user_id(),
        job_id=job_id,
    )

    if commute_check is None:
        return None

    normalized_origin_place_id = (
        current_origin_station_place_id.strip()
    )
    normalized_destination_name = (
        current_destination_station_name.strip()
    )

    if (
        commute_check.origin_station_place_id
        != normalized_origin_place_id
    ):
        return None

    if (
        commute_check.destination_station_name
        != normalized_destination_name
    ):
        return None

    return commute_check