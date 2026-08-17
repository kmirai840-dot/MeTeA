"""AIマッチングで共通利用するルール判定と点数計算。"""

from dataclasses import dataclass

from models import HopeConditionItem, Job


MATCH = "一致"
PARTIAL_MATCH = "一部一致"
MISMATCH = "不一致"
NEEDS_CONFIRMATION = "要確認"

JUDGMENT_SCORES = {
    MATCH: 100,
    PARTIAL_MATCH: 60,
    MISMATCH: 0,
    NEEDS_CONFIRMATION: None,
}

PRIORITY_WEIGHTS = {
    # 画面から保存される内部値
    "must": 3,
    "want": 2,
    "acceptable": 1,
    "no_preference": 0,

    # 単体テストや表示値との互換用
    "必須": 3,
    "希望": 2,
    "許容": 1,
    "こだわらない": 0,
}

RANK_WEIGHTS = {
    1: 3,
    2: 2,
    3: 1,
}

CATEGORY_WEIGHTS = {
    "hope_condition": 30,
    "work_value": 35,
    "career_skill": 25,
    "required_condition": 10,
}

HOPE_CONDITION_GROUP_WEIGHTS = {
    "location_transfer": 25,
    "salary_employment": 25,
    "working_time_holiday": 25,
    "work_style_environment": 15,
    "other_condition": 10,
}


@dataclass(frozen=True)
class MatchItemResult:
    """マッチング項目1件分の判定結果。"""

    item_name: str
    judgment: str
    weight: int = 1
    reason: str = ""


def round_score(
    numerator: int,
    denominator: int,
) -> int:
    """0以上の割り算結果を四捨五入する。"""

    if denominator <= 0:
        raise ValueError(
            "点数計算の分母は1以上である必要があります"
        )

    return (
        (numerator * 2 + denominator)
        // (denominator * 2)
    )


def validate_match_item(
    item: MatchItemResult,
) -> None:
    """項目の判定ラベルと重みを確認する。"""

    if item.judgment not in JUDGMENT_SCORES:
        raise ValueError(
            f"未対応の判定です：{item.judgment}"
        )

    if item.weight < 0:
        raise ValueError(
            "項目の重みは0以上である必要があります"
        )


def calculate_weighted_match_rate(
    items: list[MatchItemResult],
) -> int | None:
    """項目一覧から0～100のカテゴリ一致率を計算する。"""

    weighted_score_total = 0
    available_weight_total = 0

    for item in items:
        validate_match_item(item)

        judgment_score = JUDGMENT_SCORES[
            item.judgment
        ]

        if item.weight == 0:
            continue

        if judgment_score is None:
            continue

        weighted_score_total += (
            judgment_score * item.weight
        )

        available_weight_total += item.weight

    if available_weight_total == 0:
        return None

    return round_score(
        numerator=weighted_score_total,
        denominator=available_weight_total,
    )


def calculate_grouped_match_rate(
    group_scores: dict[str, int | None],
    group_weights: dict[str, int],
) -> int | None:
    """採点可能なグループだけでカテゴリ一致率を計算する。"""

    weighted_score_total = 0
    available_weight_total = 0

    for group_name, group_weight in (
        group_weights.items()
    ):
        if group_weight < 0:
            raise ValueError(
                "グループの重みは0以上である必要があります"
            )

        group_score = group_scores.get(
            group_name
        )

        if group_score is None:
            continue

        if group_score < 0 or group_score > 100:
            raise ValueError(
                f"{group_name}の点数は"
                "0から100の範囲で指定してください"
            )

        weighted_score_total += (
            group_score * group_weight
        )

        available_weight_total += group_weight

    if available_weight_total == 0:
        return None

    return round_score(
        numerator=weighted_score_total,
        denominator=available_weight_total,
    )


def calculate_overall_score(
    category_scores: dict[str, int | None],
) -> int | None:
    """採点可能なカテゴリだけで総合点を100点満点へ再配分する。"""

    return calculate_grouped_match_rate(
        group_scores=category_scores,
        group_weights=CATEGORY_WEIGHTS,
    )


def get_priority_weight(
    priority: str,
) -> int:
    """利用者が設定した希望条件の優先度を重みへ変換する。"""

    if priority not in PRIORITY_WEIGHTS:
        raise ValueError(
            f"未対応の優先度です：{priority}"
        )

    return PRIORITY_WEIGHTS[priority]


def get_rank_weight(
    rank: int,
) -> int:
    """確定した就活の軸の順位を重みへ変換する。"""

    if rank not in RANK_WEIGHTS:
        raise ValueError(
            f"未対応の順位です：{rank}"
        )

    return RANK_WEIGHTS[rank]


def collect_confirmation_items(
    items: list[MatchItemResult],
) -> list[MatchItemResult]:
    """評価対象の要確認項目だけを取得する。"""

    return [
        item
        for item in items
        if (
            item.weight > 0
            and item.judgment
            == NEEDS_CONFIRMATION
        )
    ]


def collect_matching_items(
    items: list[MatchItemResult],
) -> list[MatchItemResult]:
    """評価対象の一致・一部一致項目だけを取得する。"""

    return [
        item
        for item in items
        if (
            item.weight > 0
            and item.judgment in {
                MATCH,
                PARTIAL_MATCH,
            }
        )
    ]


def collect_mismatch_items(
    items: list[MatchItemResult],
) -> list[MatchItemResult]:
    """評価対象の不一致項目だけを取得する。"""

    return [
        item
        for item in items
        if (
            item.weight > 0
            and item.judgment == MISMATCH
        )
    ]


def parse_positive_integer(
    value: str | int | None,
) -> int | None:
    """保存値を0より大きい整数へ変換する。"""

    if value is None:
        return None

    if isinstance(value, int):
        return value if value > 0 else None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    normalized_value = (
        normalized_value
        .replace(",", "")
        .replace("，", "")
        .replace("円", "")
        .replace("万円", "")
        .strip()
    )

    try:
        parsed_value = int(normalized_value)

    except ValueError:
        return None

    return (
        parsed_value
        if parsed_value > 0
        else None
    )


def get_job_minimum_annual_salary(
    job: Job,
) -> tuple[int | None, str]:
    """求人から保証される最低年収を万円単位で取得する。"""

    expected_salary_min = parse_positive_integer(
        job.expected_salary_min
    )

    if expected_salary_min is not None:
        return (
            expected_salary_min,
            "求人票の想定年収最低額",
        )

    monthly_salary_min = parse_positive_integer(
        job.monthly_salary_min
    )

    if monthly_salary_min is not None:
        annual_salary_yen = (
            monthly_salary_min * 12
        )

        annual_salary_man_yen = (
            annual_salary_yen // 10_000
        )

        return (
            annual_salary_man_yen,
            "月給最低額の12か月分",
        )

    return (
        None,
        "求人票に判定可能な年収下限がありません",
    )


def evaluate_salary_values(
    job_annual_salary_min: int | None,
    minimum_salary: int,
    desired_salary: int,
    ideal_salary: int,
) -> MatchItemResult:
    """求人年収と利用者の希望年収を比較する。"""

    if (
        minimum_salary <= 0
        or desired_salary <= 0
        or ideal_salary <= 0
    ):
        return MatchItemResult(
            item_name="年収",
            judgment=NEEDS_CONFIRMATION,
            weight=0,
            reason=(
                "希望年収の設定が完了していません"
            ),
        )

    if not (
        minimum_salary
        <= desired_salary
        <= ideal_salary
    ):
        return MatchItemResult(
            item_name="年収",
            judgment=NEEDS_CONFIRMATION,
            reason=(
                "最低許容年収、希望年収、"
                "理想年収の順序を確認してください"
            ),
        )

    if job_annual_salary_min is None:
        return MatchItemResult(
            item_name="年収",
            judgment=NEEDS_CONFIRMATION,
            reason=(
                "求人票に判定可能な"
                "年収下限がありません"
            ),
        )

    if job_annual_salary_min < minimum_salary:
        return MatchItemResult(
            item_name="年収",
            judgment=MISMATCH,
            reason=(
                f"求人年収下限"
                f"{job_annual_salary_min}万円は、"
                f"最低許容年収"
                f"{minimum_salary}万円を"
                "下回っています"
            ),
        )

    if job_annual_salary_min < desired_salary:
        return MatchItemResult(
            item_name="年収",
            judgment=PARTIAL_MATCH,
            reason=(
                f"求人年収下限"
                f"{job_annual_salary_min}万円は、"
                f"最低許容年収"
                f"{minimum_salary}万円以上ですが、"
                f"希望年収"
                f"{desired_salary}万円未満です"
            ),
        )

    if job_annual_salary_min >= ideal_salary:
        return MatchItemResult(
            item_name="年収",
            judgment=MATCH,
            reason=(
                f"求人年収下限"
                f"{job_annual_salary_min}万円は、"
                f"理想年収"
                f"{ideal_salary}万円以上です"
            ),
        )

    return MatchItemResult(
        item_name="年収",
        judgment=MATCH,
        reason=(
            f"求人年収下限"
            f"{job_annual_salary_min}万円は、"
            f"希望年収"
            f"{desired_salary}万円以上です"
        ),
    )


def evaluate_salary_condition(
    job: Job,
    minimum_salary: int,
    desired_salary: int,
    ideal_salary: int,
) -> MatchItemResult:
    """求人データから最低年収を取得して判定する。"""

    (
        job_annual_salary_min,
        salary_source,
    ) = get_job_minimum_annual_salary(job)

    result = evaluate_salary_values(
        job_annual_salary_min=(
            job_annual_salary_min
        ),
        minimum_salary=minimum_salary,
        desired_salary=desired_salary,
        ideal_salary=ideal_salary,
    )

    if job_annual_salary_min is None:
        return result

    return MatchItemResult(
        item_name=result.item_name,
        judgment=result.judgment,
        weight=result.weight,
        reason=(
            f"{result.reason}"
            f"（算出元：{salary_source}）"
        ),
    )


def evaluate_commute_time(
    duration_minutes: int | None,
    commute_limit_minutes: int,
    priority: str,
) -> MatchItemResult:
    """電車移動時間を利用者の希望上限と比較する。"""

    priority_weight = get_priority_weight(
        priority
    )

    if priority_weight == 0:
        return MatchItemResult(
            item_name="電車移動時間",
            judgment=MATCH,
            weight=0,
            reason=(
                "利用者が「こだわらない」を"
                "選択しているため評価対象外です"
            ),
        )

    if commute_limit_minutes <= 0:
        return MatchItemResult(
            item_name="電車移動時間",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "希望する電車移動時間の"
                "上限が設定されていません"
            ),
        )

    if duration_minutes is None:
        return MatchItemResult(
            item_name="電車移動時間",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "この求人の電車移動時間は"
                "まだ確認されていません"
            ),
        )

    if duration_minutes < 0:
        return MatchItemResult(
            item_name="電車移動時間",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "電車移動時間の保存値が"
                "正しくありません"
            ),
        )

    if duration_minutes <= commute_limit_minutes:
        return MatchItemResult(
            item_name="電車移動時間",
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"片道{duration_minutes}分で、"
                f"希望上限{commute_limit_minutes}分"
                "以内です"
            ),
        )

    if (
        duration_minutes
        <= commute_limit_minutes + 5
    ):
        return MatchItemResult(
            item_name="電車移動時間",
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"片道{duration_minutes}分で、"
                f"希望上限{commute_limit_minutes}分に"
                "近い時間です"
            ),
        )

    return MatchItemResult(
        item_name="電車移動時間",
        judgment=MISMATCH,
        weight=priority_weight,
        reason=(
            f"片道{duration_minutes}分で、"
            f"希望上限{commute_limit_minutes}分を"
            "6分以上超えています"
        ),
    )


def parse_non_negative_integer(
    value: str | int | None,
) -> int | None:
    """保存値を0以上の整数へ変換する。"""

    if value is None:
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    normalized_value = (
        normalized_value
        .replace(",", "")
        .replace("，", "")
        .replace("時間／月", "")
        .replace("時間/月", "")
        .replace("時間", "")
        .strip()
    )

    try:
        parsed_value = int(normalized_value)

    except ValueError:
        return None

    return (
        parsed_value
        if parsed_value >= 0
        else None
    )


def evaluate_overtime_condition(
    job_overtime: str | int | None,
    overtime_limit: int,
    priority: str,
) -> MatchItemResult:
    """求人の月平均残業時間を希望上限と比較する。"""

    priority_weight = get_priority_weight(
        priority
    )

    if priority_weight == 0:
        return MatchItemResult(
            item_name="残業時間",
            judgment=MATCH,
            weight=0,
            reason=(
                "利用者が「こだわらない」を"
                "選択しているため評価対象外です"
            ),
        )

    if overtime_limit <= 0:
        return MatchItemResult(
            item_name="残業時間",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "希望する残業時間の"
                "上限が設定されていません"
            ),
        )

    job_overtime_hours = (
        parse_non_negative_integer(
            job_overtime
        )
    )

    if job_overtime_hours is None:
        return MatchItemResult(
            item_name="残業時間",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "求人票に月平均残業時間の"
                "明確な記載がありません"
            ),
        )

    if job_overtime_hours <= overtime_limit:
        return MatchItemResult(
            item_name="残業時間",
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"月平均残業時間"
                f"{job_overtime_hours}時間は、"
                f"希望上限{overtime_limit}時間"
                "以内です"
            ),
        )

    return MatchItemResult(
        item_name="残業時間",
        judgment=MISMATCH,
        weight=priority_weight,
        reason=(
            f"月平均残業時間"
            f"{job_overtime_hours}時間は、"
            f"希望上限{overtime_limit}時間を"
            "超えています"
        ),
    )


def parse_time_to_minutes(
    value: str | None,
) -> int | None:
    """時刻文字列を0時からの経過分へ変換する。"""

    if value is None:
        return None

    normalized_value = (
        value.strip()
        .replace("以降", "")
        .replace("まで", "")
        .strip()
    )

    if not normalized_value:
        return None

    time_parts = normalized_value.split(":")

    if len(time_parts) != 2:
        return None

    try:
        hour = int(time_parts[0])
        minute = int(time_parts[1])

    except ValueError:
        return None

    if hour < 0 or hour > 23:
        return None

    if minute < 0 or minute > 59:
        return None

    return hour * 60 + minute


def is_flextime_enabled(
    flextime: str | None,
) -> bool:
    """求人がフレックスタイム制かを判定する。"""

    if flextime is None:
        return False

    return flextime.strip() in {
        "あり",
        "有",
        "有り",
    }


def evaluate_start_time_condition(
    job_start_time: str | None,
    desired_start_time: str,
    priority: str,
    job_flextime: str = "",
) -> MatchItemResult:
    """求人の始業時刻が希望時刻以降かを判定する。"""

    priority_weight = get_priority_weight(
        priority
    )

    if (
        priority_weight == 0
        or desired_start_time == "こだわらない"
    ):
        return MatchItemResult(
            item_name="始業時刻",
            judgment=MATCH,
            weight=0,
            reason=(
                "利用者が始業時刻を"
                "評価対象にしていません"
            ),
        )

    if is_flextime_enabled(job_flextime):
        return MatchItemResult(
            item_name="始業時刻",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "フレックスタイム制のため、"
                "コアタイムと実際に選択できる"
                "始業時刻の確認が必要です"
            ),
        )

    desired_minutes = parse_time_to_minutes(
        desired_start_time
    )

    if desired_minutes is None:
        return MatchItemResult(
            item_name="始業時刻",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "希望始業時刻の設定を"
                "確認してください"
            ),
        )

    job_minutes = parse_time_to_minutes(
        job_start_time
    )

    if job_minutes is None:
        return MatchItemResult(
            item_name="始業時刻",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "求人票に始業時刻の"
                "明確な記載がありません"
            ),
        )

    if job_minutes >= desired_minutes:
        return MatchItemResult(
            item_name="始業時刻",
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"求人の始業時刻"
                f"{job_start_time}は、"
                f"希望する"
                f"{desired_start_time}を"
                "満たしています"
            ),
        )

    return MatchItemResult(
        item_name="始業時刻",
        judgment=MISMATCH,
        weight=priority_weight,
        reason=(
            f"求人の始業時刻"
            f"{job_start_time}は、"
            f"希望する"
            f"{desired_start_time}より早い時刻です"
        ),
    )


def evaluate_end_time_condition(
    job_end_time: str | None,
    desired_end_time: str,
    priority: str,
    job_flextime: str = "",
) -> MatchItemResult:
    """求人の終業時刻が希望時刻以内かを判定する。"""

    priority_weight = get_priority_weight(
        priority
    )

    if (
        priority_weight == 0
        or desired_end_time == "こだわらない"
    ):
        return MatchItemResult(
            item_name="終業時刻",
            judgment=MATCH,
            weight=0,
            reason=(
                "利用者が終業時刻を"
                "評価対象にしていません"
            ),
        )

    if is_flextime_enabled(job_flextime):
        return MatchItemResult(
            item_name="終業時刻",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "フレックスタイム制のため、"
                "コアタイムと実際に選択できる"
                "終業時刻の確認が必要です"
            ),
        )

    desired_minutes = parse_time_to_minutes(
        desired_end_time
    )

    if desired_minutes is None:
        return MatchItemResult(
            item_name="終業時刻",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "希望終業時刻の設定を"
                "確認してください"
            ),
        )

    job_minutes = parse_time_to_minutes(
        job_end_time
    )

    if job_minutes is None:
        return MatchItemResult(
            item_name="終業時刻",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "求人票に終業時刻の"
                "明確な記載がありません"
            ),
        )

    if job_minutes <= desired_minutes:
        return MatchItemResult(
            item_name="終業時刻",
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"求人の終業時刻"
                f"{job_end_time}は、"
                f"希望する"
                f"{desired_end_time}を"
                "満たしています"
            ),
        )

    return MatchItemResult(
        item_name="終業時刻",
        judgment=MISMATCH,
        weight=priority_weight,
        reason=(
            f"求人の終業時刻"
            f"{job_end_time}は、"
            f"希望する"
            f"{desired_end_time}より遅い時刻です"
        ),
    )


def evaluate_annual_holidays_condition(
    job_annual_holidays: str | int | None,
    desired_annual_holidays: int,
    priority: str,
) -> MatchItemResult:
    """求人の年間休日数を希望日数と比較する。"""

    priority_weight = get_priority_weight(
        priority
    )

    if priority_weight == 0:
        return MatchItemResult(
            item_name="年間休日数",
            judgment=MATCH,
            weight=0,
            reason=(
                "利用者が「こだわらない」を"
                "選択しているため評価対象外です"
            ),
        )

    if desired_annual_holidays <= 0:
        return MatchItemResult(
            item_name="年間休日数",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "希望する年間休日数が"
                "設定されていません"
            ),
        )

    job_annual_holidays_value = (
        parse_positive_integer(
            job_annual_holidays
        )
    )

    if job_annual_holidays_value is None:
        return MatchItemResult(
            item_name="年間休日数",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "求人票に年間休日数の"
                "明確な記載がありません"
            ),
        )

    if (
        job_annual_holidays_value
        >= desired_annual_holidays
    ):
        return MatchItemResult(
            item_name="年間休日数",
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"年間休日"
                f"{job_annual_holidays_value}日は、"
                f"希望する"
                f"{desired_annual_holidays}日以上です"
            ),
        )

    return MatchItemResult(
        item_name="年間休日数",
        judgment=MISMATCH,
        weight=priority_weight,
        reason=(
            f"年間休日"
            f"{job_annual_holidays_value}日は、"
            f"希望する"
            f"{desired_annual_holidays}日を"
            "下回っています"
        ),
    )


def evaluate_transfer_condition(
    job_transfer_required: str | None,
    desired_transfer_condition: str,
    priority: str,
) -> MatchItemResult:
    """求人の転勤条件を利用者の希望と比較する。"""

    priority_weight = get_priority_weight(
        priority
    )

    if (
        priority_weight == 0
        or desired_transfer_condition
        == "こだわらない"
    ):
        return MatchItemResult(
            item_name="転勤条件",
            judgment=MATCH,
            weight=0,
            reason=(
                "利用者が転勤条件を"
                "評価対象にしていません"
            ),
        )

    normalized_job_transfer = (
        job_transfer_required.strip()
        if job_transfer_required
        else ""
    )

    if normalized_job_transfer in {
        "",
        "不明",
    }:
        return MatchItemResult(
            item_name="転勤条件",
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                "求人票から転勤の有無を"
                "確認できません"
            ),
        )

    if desired_transfer_condition == "転勤不可":
        if normalized_job_transfer == "なし":
            return MatchItemResult(
                item_name="転勤条件",
                judgment=MATCH,
                weight=priority_weight,
                reason=(
                    "利用者は転勤不可を希望しており、"
                    "求人は転勤なしです"
                ),
            )

        if normalized_job_transfer == "あり":
            return MatchItemResult(
                item_name="転勤条件",
                judgment=MISMATCH,
                weight=priority_weight,
                reason=(
                    "利用者は転勤不可を希望していますが、"
                    "求人には転勤があります"
                ),
            )

        if normalized_job_transfer == "条件付き":
            return MatchItemResult(
                item_name="転勤条件",
                judgment=NEEDS_CONFIRMATION,
                weight=priority_weight,
                reason=(
                    "求人の転勤が条件付きのため、"
                    "転勤範囲と頻度の確認が必要です"
                ),
            )

    if (
        desired_transfer_condition
        == "条件次第で可"
    ):
        if normalized_job_transfer == "なし":
            return MatchItemResult(
                item_name="転勤条件",
                judgment=MATCH,
                weight=priority_weight,
                reason=(
                    "求人は転勤なしのため、"
                    "希望条件を満たしています"
                ),
            )

        if normalized_job_transfer in {
            "あり",
            "条件付き",
        }:
            return MatchItemResult(
                item_name="転勤条件",
                judgment=NEEDS_CONFIRMATION,
                weight=priority_weight,
                reason=(
                    "転勤範囲、頻度、"
                    "転勤を求められる条件の"
                    "確認が必要です"
                ),
            )

    if desired_transfer_condition == "転勤可":
        if normalized_job_transfer in {
            "あり",
            "なし",
            "条件付き",
        }:
            return MatchItemResult(
                item_name="転勤条件",
                judgment=MATCH,
                weight=priority_weight,
                reason=(
                    "利用者は転勤可能と"
                    "回答しています"
                ),
            )

    return MatchItemResult(
        item_name="転勤条件",
        judgment=NEEDS_CONFIRMATION,
        weight=priority_weight,
        reason=(
            "転勤条件の組み合わせを"
            "自動判定できません"
        ),
    )


def evaluate_employment_type_condition(
    job_employment_type: str | None,
    hope_condition_items: list[
        HopeConditionItem
    ],
) -> MatchItemResult:
    """求人の雇用形態を希望雇用形態と比較する。"""

    employment_items = [
        item
        for item in hope_condition_items
        if (
            item.condition_type
            == "employment_type"
            and get_priority_weight(
                item.priority
            ) > 0
        )
    ]

    if not employment_items:
        return MatchItemResult(
            item_name="雇用形態",
            judgment=MATCH,
            weight=0,
            reason=(
                "希望する雇用形態が"
                "設定されていないため評価対象外です"
            ),
        )

    strongest_weight = max(
        get_priority_weight(item.priority)
        for item in employment_items
    )

    normalized_job_employment_type = (
        job_employment_type.strip()
        if job_employment_type
        else ""
    )

    if not normalized_job_employment_type:
        return MatchItemResult(
            item_name="雇用形態",
            judgment=NEEDS_CONFIRMATION,
            weight=strongest_weight,
            reason=(
                "求人票に雇用形態の"
                "明確な記載がありません"
            ),
        )

    matched_item = next(
        (
            item
            for item in employment_items
            if (
                item.condition_value.strip()
                == normalized_job_employment_type
            )
        ),
        None,
    )

    if matched_item is not None:
        return MatchItemResult(
            item_name="雇用形態",
            judgment=MATCH,
            weight=get_priority_weight(
                matched_item.priority
            ),
            reason=(
                f"求人の雇用形態"
                f"「{normalized_job_employment_type}」は、"
                "希望する雇用形態に含まれています"
            ),
        )

    desired_values = "、".join(
        item.condition_value
        for item in employment_items
    )

    return MatchItemResult(
        item_name="雇用形態",
        judgment=MISMATCH,
        weight=strongest_weight,
        reason=(
            f"求人の雇用形態は"
            f"「{normalized_job_employment_type}」ですが、"
            f"希望する雇用形態は"
            f"「{desired_values}」です"
        ),
    )


def normalize_location_text(
    value: str | None,
) -> str:
    """勤務地比較用に空白を除去する。"""

    if value is None:
        return ""

    return (
        value.strip()
        .replace(" ", "")
        .replace("　", "")
    )


def evaluate_location_condition(
    job_prefecture: str | None,
    job_municipality: str | None,
    hope_condition_items: list[
        HopeConditionItem
    ],
) -> MatchItemResult:
    """求人の勤務地を希望勤務地と比較する。"""

    location_items = [
        item
        for item in hope_condition_items
        if (
            item.condition_type == "location"
            and get_priority_weight(
                item.priority
            ) > 0
        )
    ]

    if not location_items:
        return MatchItemResult(
            item_name="勤務地",
            judgment=MATCH,
            weight=0,
            reason=(
                "希望勤務地が設定されていないため"
                "評価対象外です"
            ),
        )

    strongest_weight = max(
        get_priority_weight(item.priority)
        for item in location_items
    )

    normalized_job_prefecture = (
        normalize_location_text(
            job_prefecture
        )
    )

    normalized_job_municipality = (
        normalize_location_text(
            job_municipality
        )
    )

    if not normalized_job_prefecture:
        return MatchItemResult(
            item_name="勤務地",
            judgment=NEEDS_CONFIRMATION,
            weight=strongest_weight,
            reason=(
                "求人票に勤務地の都道府県が"
                "記載されていません"
            ),
        )

    same_prefecture_items = [
        item
        for item in location_items
        if (
            normalize_location_text(
                item.condition_value
            )
            == normalized_job_prefecture
        )
    ]

    if not same_prefecture_items:
        desired_prefectures = "、".join(
            item.condition_value
            for item in location_items
        )

        return MatchItemResult(
            item_name="勤務地",
            judgment=MISMATCH,
            weight=strongest_weight,
            reason=(
                f"求人の勤務地は"
                f"「{job_prefecture}」ですが、"
                f"希望する都道府県は"
                f"「{desired_prefectures}」です"
            ),
        )

    prefecture_only_items = [
        item
        for item in same_prefecture_items
        if not normalize_location_text(
            item.detail_value
        )
    ]

    if prefecture_only_items:
        matched_item = max(
            prefecture_only_items,
            key=lambda item: get_priority_weight(
                item.priority
            ),
        )

        return MatchItemResult(
            item_name="勤務地",
            judgment=MATCH,
            weight=get_priority_weight(
                matched_item.priority
            ),
            reason=(
                f"求人の勤務地"
                f"「{job_prefecture}」は、"
                "希望する都道府県と一致しています"
            ),
        )

    if not normalized_job_municipality:
        strongest_same_prefecture_item = max(
            same_prefecture_items,
            key=lambda item: get_priority_weight(
                item.priority
            ),
        )

        return MatchItemResult(
            item_name="勤務地",
            judgment=NEEDS_CONFIRMATION,
            weight=get_priority_weight(
                strongest_same_prefecture_item.priority
            ),
            reason=(
                "求人の都道府県は希望と"
                "一致していますが、"
                "市区町村が記載されていません"
            ),
        )

    exact_match_items = [
        item
        for item in same_prefecture_items
        if (
            normalize_location_text(
                item.detail_value
            )
            == normalized_job_municipality
        )
    ]

    if exact_match_items:
        matched_item = max(
            exact_match_items,
            key=lambda item: get_priority_weight(
                item.priority
            ),
        )

        return MatchItemResult(
            item_name="勤務地",
            judgment=MATCH,
            weight=get_priority_weight(
                matched_item.priority
            ),
            reason=(
                f"求人の勤務地"
                f"「{job_prefecture}"
                f"{job_municipality}」は、"
                "希望勤務地と一致しています"
            ),
        )

    strongest_same_prefecture_item = max(
        same_prefecture_items,
        key=lambda item: get_priority_weight(
            item.priority
        ),
    )

    desired_municipalities = "、".join(
        item.detail_value or ""
        for item in same_prefecture_items
    )

    return MatchItemResult(
        item_name="勤務地",
        judgment=PARTIAL_MATCH,
        weight=get_priority_weight(
            strongest_same_prefecture_item.priority
        ),
        reason=(
            f"都道府県は"
            f"「{job_prefecture}」で一致していますが、"
            f"求人の市区町村"
            f"「{job_municipality}」は、"
            f"希望する市区町村"
            f"「{desired_municipalities}」と"
            "異なります"
        ),
    )


def extract_holiday_patterns(
    job_holidays: str | None,
) -> tuple[set[str], bool]:
    """求人の休日記述から明確な休日形態を取得する。"""

    if job_holidays is None:
        return set(), False

    normalized_text = (
        job_holidays.strip()
        .replace(" ", "")
        .replace("　", "")
    )

    if not normalized_text:
        return set(), False

    is_shift_based = (
        "シフト" in normalized_text
    )

    holiday_patterns: set[str] = set()

    if (
        "土日" in normalized_text
        or "土・日" in normalized_text
        or "土曜・日曜" in normalized_text
    ):
        holiday_patterns.add("土曜日")
        holiday_patterns.add("日曜日")

    if (
        "土曜日" in normalized_text
        or "土曜" in normalized_text
    ):
        holiday_patterns.add("土曜日")

    if (
        "日曜日" in normalized_text
        or "日曜" in normalized_text
    ):
        holiday_patterns.add("日曜日")

    if (
        "祝日" in normalized_text
        or "土日祝" in normalized_text
    ):
        holiday_patterns.add("祝日")

    if (
        "平日休" in normalized_text
        or "平日休日" in normalized_text
    ):
        holiday_patterns.add("平日")

    return holiday_patterns, is_shift_based


def evaluate_holiday_pattern_condition(
    job_holidays: str | None,
    hope_condition_items: list[
        HopeConditionItem
    ],
) -> MatchItemResult:
    """求人の休日形態を利用者の希望と比較する。"""

    holiday_items = [
        item
        for item in hope_condition_items
        if (
            item.condition_type == "holiday"
            and get_priority_weight(
                item.priority
            ) > 0
        )
    ]

    if not holiday_items:
        return MatchItemResult(
            item_name="休日形態",
            judgment=MATCH,
            weight=0,
            reason=(
                "希望する休日形態が"
                "設定されていないため評価対象外です"
            ),
        )

    strongest_weight = max(
        get_priority_weight(item.priority)
        for item in holiday_items
    )

    desired_patterns = {
        item.condition_value.strip()
        for item in holiday_items
        if item.condition_value.strip()
    }

    (
        job_patterns,
        is_shift_based,
    ) = extract_holiday_patterns(
        job_holidays
    )

    if "シフト制" in desired_patterns:
        if is_shift_based:
            return MatchItemResult(
                item_name="休日形態",
                judgment=MATCH,
                weight=strongest_weight,
                reason=(
                    "利用者はシフト制を希望しており、"
                    "求人もシフト制です"
                ),
            )

        return MatchItemResult(
            item_name="休日形態",
            judgment=MISMATCH,
            weight=strongest_weight,
            reason=(
                "利用者はシフト制を希望していますが、"
                "求人票からシフト制を確認できません"
            ),
        )

    if is_shift_based:
        desired_text = "、".join(
            sorted(desired_patterns)
        )

        return MatchItemResult(
            item_name="休日形態",
            judgment=NEEDS_CONFIRMATION,
            weight=strongest_weight,
            reason=(
                "求人はシフト制のため、"
                f"希望する休日"
                f"「{desired_text}」を"
                "取得できるか確認が必要です"
            ),
        )

    if not job_patterns:
        return MatchItemResult(
            item_name="休日形態",
            judgment=NEEDS_CONFIRMATION,
            weight=strongest_weight,
            reason=(
                "求人票から固定の休日形態を"
                "確認できません"
            ),
        )

    fixed_desired_patterns = (
        desired_patterns - {"シフト制"}
    )

    if fixed_desired_patterns.issubset(
        job_patterns
    ):
        desired_text = "、".join(
            sorted(fixed_desired_patterns)
        )

        return MatchItemResult(
            item_name="休日形態",
            judgment=MATCH,
            weight=strongest_weight,
            reason=(
                f"求人の休日は、希望する"
                f"「{desired_text}」を"
                "すべて満たしています"
            ),
        )

    missing_patterns = (
        fixed_desired_patterns - job_patterns
    )

    missing_text = "、".join(
        sorted(missing_patterns)
    )

    return MatchItemResult(
        item_name="休日形態",
        judgment=MISMATCH,
        weight=strongest_weight,
        reason=(
            f"希望する休日のうち"
            f"「{missing_text}」を"
            "求人票から確認できません"
        ),
    )


def evaluate_work_schedule_condition(
    item_name: str,
    job_description: str | None,
    desired_condition: str,
    priority: str,
    positive_keywords: tuple[str, ...],
    negative_keywords: tuple[str, ...],
) -> MatchItemResult:
    """シフト勤務・夜勤の有無を求人記載から判定する。"""

    priority_weight = get_priority_weight(
        priority
    )

    if (
        priority_weight == 0
        or desired_condition
        == "こだわらない"
    ):
        return MatchItemResult(
            item_name=item_name,
            judgment=MATCH,
            weight=0,
            reason=(
                "利用者が「こだわらない」を"
                "選択しているため評価対象外です"
            ),
        )

    normalized_description = (
        job_description or ""
    ).strip()

    if not normalized_description:
        return MatchItemResult(
            item_name=item_name,
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                f"求人票から{item_name}の"
                "有無を確認できません"
            ),
        )

    has_negative_statement = any(
        keyword in normalized_description
        for keyword in negative_keywords
    )

    has_positive_statement = any(
        keyword in normalized_description
        for keyword in positive_keywords
    )

    if has_negative_statement:
        job_has_condition = False

    elif has_positive_statement:
        job_has_condition = True

    else:
        return MatchItemResult(
            item_name=item_name,
            judgment=NEEDS_CONFIRMATION,
            weight=priority_weight,
            reason=(
                f"求人票から{item_name}の"
                "有無を確認できません"
            ),
        )

    if desired_condition == "不可":
        if job_has_condition:
            return MatchItemResult(
                item_name=item_name,
                judgment=MISMATCH,
                weight=priority_weight,
                reason=(
                    f"利用者は{item_name}不可を"
                    f"希望していますが、求人には"
                    f"{item_name}があります"
                ),
            )

        return MatchItemResult(
            item_name=item_name,
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"利用者は{item_name}不可を"
                f"希望しており、求人には"
                f"{item_name}がありません"
            ),
        )

    if desired_condition == "条件次第で可":
        if job_has_condition:
            return MatchItemResult(
                item_name=item_name,
                judgment=NEEDS_CONFIRMATION,
                weight=priority_weight,
                reason=(
                    f"求人には{item_name}があるため、"
                    "実施条件、頻度、時間帯の"
                    "確認が必要です"
                ),
            )

        return MatchItemResult(
            item_name=item_name,
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"求人には{item_name}がありません"
            ),
        )

    if desired_condition == "可":
        return MatchItemResult(
            item_name=item_name,
            judgment=MATCH,
            weight=priority_weight,
            reason=(
                f"利用者は{item_name}可と"
                "回答しています"
            ),
        )

    return MatchItemResult(
        item_name=item_name,
        judgment=NEEDS_CONFIRMATION,
        weight=priority_weight,
        reason=(
            f"利用者の{item_name}に関する"
            "希望を自動判定できません"
        ),
    )


def evaluate_shift_work_condition(
    job_description: str | None,
    desired_condition: str,
    priority: str,
) -> MatchItemResult:
    """求人のシフト勤務を利用者希望と比較する。"""

    return evaluate_work_schedule_condition(
        item_name="シフト勤務",
        job_description=job_description,
        desired_condition=desired_condition,
        priority=priority,
        positive_keywords=(
            "シフト勤務あり",
            "シフト制",
            "交替制",
            "交代制",
        ),
        negative_keywords=(
            "シフト勤務なし",
            "シフトなし",
            "交替勤務なし",
            "交代勤務なし",
        ),
    )


def evaluate_night_work_condition(
    job_description: str | None,
    desired_condition: str,
    priority: str,
) -> MatchItemResult:
    """求人の夜勤を利用者希望と比較する。"""

    return evaluate_work_schedule_condition(
        item_name="夜勤",
        job_description=job_description,
        desired_condition=desired_condition,
        priority=priority,
        positive_keywords=(
            "夜勤あり",
            "夜間勤務あり",
            "深夜勤務あり",
            "夜勤を含む",
            "深夜勤務を含む",
        ),
        negative_keywords=(
            "夜勤なし",
            "夜間勤務なし",
            "深夜勤務なし",
            "日勤のみ",
            "夜勤はありません",
        ),
    )