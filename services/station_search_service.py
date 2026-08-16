"""Google Places APIを使用して駅候補を検索する。"""

from dataclasses import dataclass
import os

from dotenv import load_dotenv
import requests


PLACES_AUTOCOMPLETE_URL = (
    "https://places.googleapis.com/v1/places:autocomplete"
)
REQUEST_TIMEOUT_SECONDS = 10
MAX_STATION_CANDIDATES = 5


@dataclass(frozen=True)
class StationCandidate:
    """駅検索で取得した候補を保持するクラス。"""

    place_id: str
    station_name: str
    address_text: str

    @property
    def display_name(self) -> str:
        """選択肢に表示する文字列を返す。"""

        if self.address_text:
            return f"{self.station_name}（{self.address_text}）"

        return self.station_name


class StationSearchError(Exception):
    """駅検索を正常に完了できなかった場合のエラー。"""


def search_station_candidates(
    search_text: str,
) -> list[StationCandidate]:
    """入力された駅名から、日本国内の駅候補を検索する。"""

    normalized_search_text = search_text.strip()

    if not normalized_search_text:
        return []

    load_dotenv()

    api_key = os.getenv(
        "GOOGLE_MAPS_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise StationSearchError(
            "Google Maps APIキーが設定されていません。"
        )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "suggestions.placePrediction.placeId,"
            "suggestions.placePrediction.structuredFormat."
            "mainText.text,"
            "suggestions.placePrediction.structuredFormat."
            "secondaryText.text"
        ),
    }

    request_body = {
        "input": normalized_search_text,
        "includedRegionCodes": ["jp"],
        "includedPrimaryTypes": [
            "train_station",
            "subway_station",
            "transit_station",
        ],
        "languageCode": "ja",
    }

    try:
        response = requests.post(
            PLACES_AUTOCOMPLETE_URL,
            headers=headers,
            json=request_body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise StationSearchError(
            "駅を検索できませんでした。"
            "インターネット接続を確認して、もう一度お試しください。"
        ) from error

    if response.status_code == 403:
        raise StationSearchError(
            "駅検索APIを利用できません。"
            "APIキーの設定と制限を確認してください。"
        )

    if response.status_code == 429:
        raise StationSearchError(
            "駅検索の利用回数が上限に達しました。"
            "時間をおいて、もう一度お試しください。"
        )

    if not response.ok:
        raise StationSearchError(
            "駅検索でエラーが発生しました。"
            f"エラーコード：{response.status_code}"
        )

    response_data = response.json()
    candidates: list[StationCandidate] = []

    for suggestion in response_data.get("suggestions", []):
        prediction = suggestion.get(
            "placePrediction",
            {},
        )
        structured_format = prediction.get(
            "structuredFormat",
            {},
        )

        place_id = prediction.get(
            "placeId",
            "",
        ).strip()
        station_name = structured_format.get(
            "mainText",
            {},
        ).get(
            "text",
            "",
        ).strip()
        address_text = structured_format.get(
            "secondaryText",
            {},
        ).get(
            "text",
            "",
        ).strip()

        if not place_id or not station_name:
            continue

        candidates.append(
            StationCandidate(
                place_id=place_id,
                station_name=station_name,
                address_text=address_text,
            )
        )

        if len(candidates) >= MAX_STATION_CANDIDATES:
            break

    return candidates