"""AIを利用して求人票本文を構造化する処理。"""

import json

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


STRING_FIELDS = (
    "company_name",
    "job_title",
    "job_number",
    "industry",
    "business_description",
    "employee_count_min",
    "employee_count_max",
    "established_date",
    "capital",
    "listing_status",
    "occupation",
    "department",
    "planned_hires",
    "recruitment_reason",
    "job_summary",
    "responsibility_scope",
    "customers",
    "internal_stakeholders",
    "external_partners",
    "goals_kpi",
    "expected_results",
    "employment_type",
    "probation_period_status",
    "probation_period_months",
    "probation_period",
    "prefecture",
    "municipality",
    "nearest_station",
    "transfer_required",
    "work_style",
    "start_time",
    "end_time",
    "break_minutes",
    "scheduled_work_hours",
    "flextime",
    "overtime",
    "holidays",
    "annual_holidays",
    "wage_type",
    "monthly_salary_min",
    "monthly_salary_max",
    "base_salary_min",
    "base_salary_max",
    "expected_salary_min",
    "expected_salary_max",
    "fixed_overtime_system",
    "fixed_overtime_hours",
    "fixed_overtime_pay_min",
    "fixed_overtime_pay_max",
    "overtime_extra_pay",
    "bonus",
    "salary_increase",
    "incentive",
    "social_insurance",
    "commuting_allowance",
    "housing_allowance",
    "retirement_plan",
    "qualification_support",
    "training_program",
    "document_screening_status",
    "document_screening",
    "interview",
    "aptitude_test_status",
    "aptitude_test",
    "interview_count_min",
    "interview_count_max",
    "expected_join_date",
)

BOOLEAN_FIELDS = (
    "monthly_salary_is_explicit",
)

LIST_FIELDS = (
    "job_details",
    "required_experience",
    "required_skills",
    "required_qualifications",
    "preferred_experience",
    "preferred_skills",
    "desired_personality",
    "not_listed_fields",
)


def build_job_schema() -> dict:
    """求人抽出結果のJSON Schemaを作成する。"""

    properties = {
        field_name: {
            "type": "string",
        }
        for field_name in STRING_FIELDS
    }

    properties.update(
        {
            field_name: {
                "type": "boolean",
            }
            for field_name in BOOLEAN_FIELDS
        }
    )

    properties.update(
        {
            field_name: {
                "type": "array",
                "items": {
                    "type": "string",
                },
            }
            for field_name in LIST_FIELDS
        }
    )

    return {
        "type": "object",
        "properties": properties,
        "required": [
            *STRING_FIELDS,
            *BOOLEAN_FIELDS,
            *LIST_FIELDS,
        ],
        "additionalProperties": False,
    }


def normalize_presence_value(
    value: str,
) -> str:
    """有無を画面の選択肢へ統一する。"""

    normalized_value = value.strip()

    if not normalized_value:
        return ""

    if normalized_value in (
        "あり",
        "有り",
        "有",
        "有る",
    ):
        return "あり"

    if normalized_value in (
        "なし",
        "無し",
        "無",
        "無い",
    ):
        return "なし"

    if normalized_value in (
        "不明",
        "記載なし",
        "確認要",
    ):
        return "不明"

    return "不明"


def normalize_employment_type(
    value: str,
) -> str:
    """雇用形態を画面の選択肢へ統一する。"""

    if "正社員" in value:
        return "正社員"

    if "契約社員" in value:
        return "契約社員"

    if "派遣" in value:
        return "派遣社員"

    if (
        "パート" in value
        or "アルバイト" in value
    ):
        return "パート・アルバイト"

    if "業務委託" in value:
        return "業務委託"

    if value.strip():
        return "その他"

    return ""


def normalize_wage_type(
    value: str,
) -> str:
    """賃金形態を画面の選択肢へ統一する。"""

    if "月給" in value:
        return "月給制"

    if "年俸" in value:
        return "年俸制"

    if "時給" in value:
        return "時給制"

    if "日給" in value:
        return "日給制"

    if value.strip():
        return "その他"

    return ""


def normalize_work_style(
    value: str,
) -> str:
    """働き方を画面の選択肢へ統一する。"""

    normalized_value = value.strip()

    if not normalized_value:
        return ""

    if (
        "完全在宅" in normalized_value
        or "フルリモート" in normalized_value
    ):
        return "完全在宅"

    if (
        "一部在宅" in normalized_value
        or "ハイブリッド" in normalized_value
        or "テレワーク可" in normalized_value
        or "リモート可" in normalized_value
    ):
        return "一部在宅"

    if (
        "出社のみ" in normalized_value
        or "原則出社" in normalized_value
    ):
        return "出社のみ"

    if "相談" in normalized_value:
        return "相談可"

    return "不明"


def normalize_extracted_choices(
    extracted_data: dict,
) -> dict:
    """AI抽出結果の選択値を画面用に整える。"""

    extracted_data["employment_type"] = (
        normalize_employment_type(
            extracted_data.get(
                "employment_type",
                "",
            )
        )
    )

    extracted_data["wage_type"] = (
        normalize_wage_type(
            extracted_data.get(
                "wage_type",
                "",
            )
        )
    )

    extracted_data["work_style"] = (
        normalize_work_style(
            extracted_data.get(
                "work_style",
                "",
            )
        )
    )

    presence_fields = (
        "probation_period_status",
        "fixed_overtime_system",
        "overtime_extra_pay",
        "document_screening_status",
        "aptitude_test_status",
    )

    for field_name in presence_fields:
        extracted_data[field_name] = (
            normalize_presence_value(
                extracted_data.get(
                    field_name,
                    "",
                )
            )
        )

    return extracted_data


def extract_job_data(
    job_text: str,
) -> dict:
    """求人票本文をAIで共通の求人データへ変換する。"""

    if not job_text.strip():
        raise ValueError(
            "求人票本文が入力されていません。"
        )

    client = OpenAI()

    response = client.responses.create(
        model="gpt-5-mini",
        store=False,
        input=[
            {
                "role": "system",
                "content": (
                    "あなたは日本語の求人票を"
                    "構造化するアシスタントです。"
                    "求人媒体、見出し、項目順、改行位置に"
                    "依存せず、文章の意味から情報を"
                    "各項目へ整理してください。"
                    "求人票に書かれていない事実を"
                    "推測してはいけません。"
                    "記載がない文字列項目は空文字、"
                    "記載がない配列項目は空配列にしてください。"
                    "会社情報と求人情報を混同しないでください。"
                    "会社所在地ではなく実際の勤務地を"
                    "prefectureとmunicipalityへ設定してください。"
                    "job_titleは求人票に記載された求人名または"
                    "ポジション名を、省略や要約をせず"
                    "原文に近い形で設定してください。"
                    "occupationは仕事内容を基にした"
                    "一般的な職種分類としてください。"
                    "job_summaryは仕事内容全体の要約ではなく、"
                    "求人票に記載された主な仕事内容を"
                    "事実の範囲で整理してください。"
                    "job_details、応募要件などの配列は、"
                    "内容ごとに分けてください。"
                    "金額、人数、時間、日数、回数、月数は"
                    "単位とカンマを除いた数字だけを"
                    "文字列で返してください。"
                    "想定年収は万円単位、"
                    "月給・基本給・固定残業代は"
                    "円単位にしてください。"
                    "求人票に月給または月額給与の総額が"
                    "直接記載されている場合だけ、"
                    "monthly_salary_is_explicitをtrueにし、"
                    "monthly_salary_minと"
                    "monthly_salary_maxへ設定してください。"
                    "基本給だけが記載されている場合、"
                    "monthly_salary_is_explicitはfalseです。"
                    "年収・年俸・基本給から月給を計算したり、"
                    "基本給を月給として複製してはいけません。"
                    "start_timeとend_timeはHH:MM形式、"
                    "scheduled_work_hoursは1日あたりの実働時間です。"
                    "求人票に所定労働時間が明記されている場合は"
                    "その値を使用してください。"
                    "明記がなく、始業時刻・終業時刻・休憩時間が"
                    "すべて明確な場合に限り、"
                    "終了時刻から開始時刻と休憩時間を差し引いて"
                    "正確に計算してください。"
                    "break_minutesは分、"
                    "overtimeは月平均時間としてください。"
                    "従業員数はemployee_count_minと"
                    "employee_count_maxへ分けてください。"
                    "例えば51～100名なら下限を51、"
                    "上限を100としてください。"
                    "単一値なら下限と上限へ同じ値を"
                    "設定してください。"
                    "面接回数もinterview_count_minと"
                    "interview_count_maxへ分け、"
                    "1～2回なら下限を1、上限を2、"
                    "2回なら両方へ2を設定してください。"
                    "下限または上限だけが明らかな場合は、"
                    "明らかな側だけ設定してください。"
                    "probation_period_status、"
                    "fixed_overtime_system、"
                    "document_screening_status、"
                    "aptitude_test_statusは、"
                    "あり・なし・不明・空文字のいずれかに"
                    "してください。"
                    "employment_typeは正社員、契約社員、"
                    "派遣社員、パート・アルバイト、"
                    "業務委託、その他のいずれかへ"
                    "可能な範囲で整理してください。"
                    "transfer_requiredは"
                    "あり・なし・条件付き・不明・空文字、"
                    "flextimeも"
                    "あり・なし・条件付き・不明・空文字、"
                    "overtime_extra_payは"
                    "あり・なし・不明・空文字としてください。"
                    "不明な情報を補完せず、"
                    "確認が必要な項目名を"
                    "not_listed_fieldsへ入れてください。"
                ),
            },
            {
                "role": "user",
                "content": job_text,
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "job_document",
                "strict": True,
                "schema": build_job_schema(),
            }
        },
    )

    extracted_data = json.loads(
        response.output_text
    )

    if not extracted_data.get(
        "monthly_salary_is_explicit",
        False,
    ):
        extracted_data[
            "monthly_salary_min"
        ] = ""

        extracted_data[
            "monthly_salary_max"
        ] = ""

    return normalize_extracted_choices(
        extracted_data
    )