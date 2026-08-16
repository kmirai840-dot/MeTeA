"""Google Routes APIを使用して駅間の電車所要時間を取得する。"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import requests


ROUTES_API_URL = (
    "https://routes.googleapis.com/"
    "directions/v2:computeRoutes"
)
REQUEST_TIMEOUT_SECONDS = 15
JAPAN_TIME_ZONE = ZoneInfo("Asia/Tokyo")
COMMUTE_ARRIVAL_HOUR = 9


@dataclass(frozen=True)
class CommuteRouteResult:
    """駅間の電車経路計算結果を保持するクラス。"""

    duration_minutes: int
    distance_meters: int


class CommuteRouteError(Exception):
    """電車経路を正常に計算できなかった場合のエラー。"""


def build_next_commute_arrival_time() -> str:
    """次の平日午前9時を経路検索の到着時刻として作る。"""

    current_time = datetime.now(
        JAPAN_TIME_ZONE,
    )
    arrival_time = current_time.replace(
        hour=COMMUTE_ARRIVAL_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )

    if arrival_time <= current_time:
        arrival_time += timedelta(days=1)

    while arrival_time.weekday() >= 5:
        arrival_time += timedelta(days=1)

    return arrival_time.isoformat()


def parse_duration_minutes(
    duration_text: str,
) -> int:
    """Googleの秒表記を切り上げた分数へ変換する。"""

    normalized_duration = duration_text.strip()

    if not normalized_duration.endswith("s"):
        raise CommuteRouteError(
            "電車所要時間の形式を確認できませんでした。"
        )

    seconds_text = normalized_duration[:-1]

    try:
        duration_seconds = float(seconds_text)
    except ValueError as error:
        raise CommuteRouteError(
            "電車所要時間の形式を確認できませんでした。"
        ) from error

    return math.ceil(duration_seconds / 60)


def calculate_train_commute(
    origin_station_place_id: str,
    destination_station: str,
    destination_station_place_id: str = "",
) -> CommuteRouteResult:
    """現在の最寄駅から勤務地の最寄駅までの電車時間を取得する。"""

    normalized_origin_place_id = (
        origin_station_place_id.strip()
    )
    normalized_destination_station = (
        destination_station.strip()
    )
    normalized_destination_place_id = (
        destination_station_place_id.strip()
    )

    if not normalized_origin_place_id:
        raise CommuteRouteError(
            "現在の最寄駅が選択されていません。"
        )

    if not normalized_destination_station:
        raise CommuteRouteError(
            "求人の勤務地最寄駅が登録されていません。"
        )

    load_dotenv()

    api_key = os.getenv(
        "GOOGLE_MAPS_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise CommuteRouteError(
            "Google Maps APIキーが設定されていません。"
        )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "routes.duration,"
            "routes.distanceMeters"
        ),
    }

    if normalized_destination_place_id:
        destination_waypoint = {
            "placeId": normalized_destination_place_id,
        }
    else:
        destination_waypoint = {
            "address": normalized_destination_station,
        }

    request_body = {
        "origin": {
            "placeId": normalized_origin_place_id,
        },
        "destination": destination_waypoint,
        "travelMode": "TRANSIT",
        "arrivalTime": build_next_commute_arrival_time(),
        "computeAlternativeRoutes": False,
        "languageCode": "ja-JP",
        "units": "METRIC",
    }

    try:
        response = requests.post(
            ROUTES_API_URL,
            headers=headers,
            json=request_body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise CommuteRouteError(
            "電車所要時間を取得できませんでした。"
            "インターネット接続を確認して、"
            "もう一度お試しください。"
        ) from error

    if response.status_code == 403:
        raise CommuteRouteError(
            "経路検索APIを利用できません。"
            "APIキーとRoutes APIの設定を確認してください。"
        )

    if response.status_code == 429:
        raise CommuteRouteError(
            "経路検索の利用回数が上限に達しました。"
            "時間をおいて、もう一度お試しください。"
        )

    if not response.ok:
        raise CommuteRouteError(
            "電車所要時間の取得でエラーが発生しました。"
            f"エラーコード：{response.status_code}"
        )

    response_data = response.json()
    routes = response_data.get(
        "routes",
        [],
    )

    if not routes:
        raise CommuteRouteError(
            "指定された駅間の電車経路が見つかりませんでした。"
        )

    primary_route = routes[0]
    duration_text = primary_route.get(
        "duration",
        "",
    )
    distance_meters = primary_route.get(
        "distanceMeters",
        0,
    )

    if not duration_text:
        raise CommuteRouteError(
            "電車所要時間を取得できませんでした。"
        )

    return CommuteRouteResult(
        duration_minutes=parse_duration_minutes(
            duration_text,
        ),
        distance_meters=int(distance_meters),
    )