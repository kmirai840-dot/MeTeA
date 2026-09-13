"""求人AIマッチングの構造化結果を検証・変換する。"""

import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from models import (
    AISemanticMatchItem,
    JobAISemanticEvaluation,
)
from services.job_matching_prompt_service import (
    build_ai_matching_messages,
)
from services.job_matching_rule_service import (
    MATCH,
    MISMATCH,
    NEEDS_CONFIRMATION,
    PARTIAL_MATCH,
)


load_dotenv()


PROMPT_VERSION = "job-matching-v9"
DEFAULT_AI_MODEL = "gpt-4.1-mini"

MAX_AI_ITEMS = 40
MAX_ITEM_NAME_LENGTH = 100
MAX_REASON_LENGTH = 240
MAX_EVIDENCE_LENGTH = 240
# 日本語の理由・根拠を含む全評価項目が途中で切れないよう余裕を確保する。
MAX_AI_OUTPUT_TOKENS = 12000
AI_REQUEST_TIMEOUT_SECONDS = 75.0

ALLOWED_CATEGORIES = {
    "hope_condition",
    "work_value",
    "career_skill",
    "required_condition",
}

ALLOWED_JUDGMENTS = {
    MATCH,
    PARTIAL_MATCH,
    MISMATCH,
    NEEDS_CONFIRMATION,
}

ALLOWED_HOPE_GROUPS = {
    "location_transfer",
    "salary_employment",
    "working_time_holiday",
    "work_style_environment",
    "other_condition",
}


class OpenAIMatchItem(BaseModel):
    """OpenAIから受け取る意味判定1件。"""

    category: Literal[
        "hope_condition",
        "work_value",
        "career_skill",
        "required_condition",
    ]
    evaluation_group: Literal[
        "",
        "confirmed_axis",
        "work_style",
        "direct_experience",
        "portable_skill",
        "achievement_reproducibility",
    ] = ""
    item_name: str = Field(
        min_length=1,
        max_length=MAX_ITEM_NAME_LENGTH,
    )
    judgment: Literal[
        "一致",
        "一部一致",
        "不一致",
        "要確認",
    ]
    reason: str = Field(
        min_length=1,
        max_length=MAX_REASON_LENGTH,
    )
    weight: int = Field(
        default=1,
        ge=1,
        le=3,
    )
    hope_group: Literal[
        "",
        "location_transfer",
        "salary_employment",
        "working_time_holiday",
        "work_style_environment",
        "other_condition",
    ] = ""
    evidence: str = Field(
        default="",
        max_length=MAX_EVIDENCE_LENGTH,
    )
    is_major_required_mismatch: bool = False


class OpenAIMatchResponse(BaseModel):
    """OpenAIから受け取る意味判定全体。"""

    items: list[OpenAIMatchItem] = Field(
        default_factory=list,
        max_length=MAX_AI_ITEMS,
    )


class JobMatchingAIResultError(ValueError):
    """AIの構造化結果が不正な場合のエラー。"""


def require_text(
    value: Any,
    field_name: str,
    max_length: int,
    allow_empty: bool = False,
) -> str:
    """AI結果の文字列項目を検証する。"""

    if not isinstance(value, str):
        raise JobMatchingAIResultError(
            f"{field_name}は文字列である必要があります"
        )

    normalized_value = value.strip()

    if not allow_empty and not normalized_value:
        raise JobMatchingAIResultError(
            f"{field_name}が入力されていません"
        )

    if len(normalized_value) > max_length:
        raise JobMatchingAIResultError(
            f"{field_name}は"
            f"{max_length}文字以内である必要があります"
        )

    return normalized_value


def parse_ai_item(
    raw_item: Any,
    item_index: int,
) -> AISemanticMatchItem:
    """AI項目1件を検証してモデルへ変換する。"""

    if not isinstance(raw_item, dict):
        raise JobMatchingAIResultError(
            f"items[{item_index}]は"
            "オブジェクトである必要があります"
        )

    category = require_text(
        raw_item.get("category"),
        f"items[{item_index}].category",
        50,
    )

    if category not in ALLOWED_CATEGORIES:
        raise JobMatchingAIResultError(
            f"items[{item_index}].categoryの"
            f"「{category}」は未対応です"
        )

    evaluation_group = require_text(
        raw_item.get("evaluation_group", ""),
        f"items[{item_index}].evaluation_group",
        50,
        allow_empty=True,
    )

    if category == "work_value":
        if evaluation_group not in {"confirmed_axis", "work_style"}:
            raise JobMatchingAIResultError(
                f"items[{item_index}]のwork_valueには"
                "evaluation_groupが必要です"
            )
    elif category == "career_skill":
        if evaluation_group not in {
            "direct_experience",
            "portable_skill",
            "achievement_reproducibility",
        }:
            raise JobMatchingAIResultError(
                f"items[{item_index}]のcareer_skillには"
                "evaluation_groupが必要です"
            )
    elif evaluation_group:
        raise JobMatchingAIResultError(
            f"items[{item_index}]の{category}には"
            "evaluation_groupを設定できません"
        )

    item_name = require_text(
        raw_item.get("item_name"),
        f"items[{item_index}].item_name",
        MAX_ITEM_NAME_LENGTH,
    )

    judgment = require_text(
        raw_item.get("judgment"),
        f"items[{item_index}].judgment",
        20,
    )

    if judgment not in ALLOWED_JUDGMENTS:
        raise JobMatchingAIResultError(
            f"items[{item_index}].judgmentの"
            f"「{judgment}」は未対応です"
        )

    reason = require_text(
        raw_item.get("reason"),
        f"items[{item_index}].reason",
        MAX_REASON_LENGTH,
    )

    evidence = require_text(
        raw_item.get(
            "evidence",
            "",
        ),
        f"items[{item_index}].evidence",
        MAX_EVIDENCE_LENGTH,
        allow_empty=True,
    )

    if (
        judgment != NEEDS_CONFIRMATION
        and not evidence
    ):
        raise JobMatchingAIResultError(
            f"items[{item_index}]の"
            "判定根拠となる原文がありません"
        )


    weight_value = raw_item.get(
        "weight",
        1,
    )

    if (
        not isinstance(weight_value, int)
        or isinstance(weight_value, bool)
    ):
        raise JobMatchingAIResultError(
            f"items[{item_index}].weightは"
            "整数である必要があります"
        )

    if weight_value not in {
        1,
        2,
        3,
    }:
        raise JobMatchingAIResultError(
            f"items[{item_index}].weightは"
            "1、2、3のいずれかである必要があります"
        )

    if (
        category in {
            "career_skill",
            "required_condition",
        }
        and weight_value != 1
    ):
        raise JobMatchingAIResultError(
            f"items[{item_index}]の"
            f"{category}の重みは"
            "1である必要があります"
        )

    hope_group = require_text(
        raw_item.get(
            "hope_group",
            "",
        ),
        f"items[{item_index}].hope_group",
        50,
        allow_empty=True,
    )

    if (
        category == "hope_condition"
        and hope_group
        not in ALLOWED_HOPE_GROUPS
    ):
        raise JobMatchingAIResultError(
            f"items[{item_index}]の"
            "hope_conditionには"
            "希望条件グループが必要です"
        )

    if (
        category != "hope_condition"
        and hope_group
    ):
        raise JobMatchingAIResultError(
            f"items[{item_index}]の"
            f"{category}には"
            "希望条件グループを設定できません"
        )

    major_mismatch_value = raw_item.get(
        "is_major_required_mismatch",
        False,
    )

    if not isinstance(
        major_mismatch_value,
        bool,
    ):
        raise JobMatchingAIResultError(
            f"items[{item_index}]."
            "is_major_required_mismatchは"
            "trueまたはfalseである必要があります"
        )

    is_major_required_mismatch = (
        major_mismatch_value
    )

    if (
        is_major_required_mismatch
        and (
            category != "required_condition"
            or judgment != MISMATCH
        )
    ):
        raise JobMatchingAIResultError(
            "重大必須条件不一致は、"
            "求人側応募必須条件の"
            "不一致にだけ設定できます"
        )

    return AISemanticMatchItem(
        category=category,
        evaluation_group=evaluation_group,
        item_name=item_name,
        judgment=judgment,
        reason=reason,
        weight=weight_value,
        hope_group=hope_group,
        evidence=evidence,
        is_major_required_mismatch=(
            is_major_required_mismatch
        ),
    )


def parse_ai_result_payload(
    payload: Any,
) -> list[AISemanticMatchItem]:
    """AIレスポンス全体を検証する。"""

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)

        except json.JSONDecodeError as error:
            raise JobMatchingAIResultError(
                "AIレスポンスをJSONとして"
                "読み取れませんでした"
            ) from error

    if not isinstance(payload, dict):
        raise JobMatchingAIResultError(
            "AIレスポンスは"
            "オブジェクトである必要があります"
        )

    raw_items = payload.get("items")

    if not isinstance(raw_items, list):
        raise JobMatchingAIResultError(
            "AIレスポンスのitemsは"
            "配列である必要があります"
        )

    if len(raw_items) > MAX_AI_ITEMS:
        raise JobMatchingAIResultError(
            f"AI判定項目は"
            f"{MAX_AI_ITEMS}件以内である必要があります"
        )

    return [
        parse_ai_item(
            raw_item=raw_item,
            item_index=item_index,
        )
        for item_index, raw_item
        in enumerate(raw_items)
    ]


def build_ai_semantic_evaluation(
    job_id: int,
    payload: Any,
    model_name: str,
) -> JobAISemanticEvaluation:
    """検証済みAI意味判定結果を作成する。"""

    if job_id <= 0:
        raise JobMatchingAIResultError(
            "求人IDが正しくありません"
        )

    normalized_model_name = model_name.strip()

    if not normalized_model_name:
        raise JobMatchingAIResultError(
            "使用したAIモデル名がありません"
        )

    items = parse_ai_result_payload(
        payload
    )

    return JobAISemanticEvaluation(
        job_id=job_id,
        items=items,
        model_name=normalized_model_name,
        prompt_version=PROMPT_VERSION,
        evaluated_at=(
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),
    )


def filter_unavailable_categories(
    payload: dict[str, Any],
    matching_context: dict[str, Any],
) -> dict[str, Any]:
    """未登録の利用者情報に対応するAI項目を除外する。"""

    user_information = matching_context.get(
        "user_matching_information",
        {},
    )

    if not isinstance(
        user_information,
        dict,
    ):
        user_information = {}

    allowed_categories = {
        "required_condition",
    }

    if user_information.get(
        "hope_conditions"
    ):
        allowed_categories.add(
            "hope_condition"
        )

    if (
        user_information.get("job_hunting_axes")
        or user_information.get("work_style_answers")
    ):
        allowed_categories.add(
            "work_value"
        )

    if user_information.get(
        "career"
    ):
        allowed_categories.add(
            "career_skill"
        )

    raw_items = payload.get(
        "items",
        [],
    )

    if not isinstance(
        raw_items,
        list,
    ):
        return payload

    filtered_items = [
        item
        for item in raw_items
        if (
            isinstance(item, dict)
            and item.get("category")
            in allowed_categories
            and not (
                item.get("category") == "work_value"
                and item.get("evaluation_group") == "confirmed_axis"
                and not user_information.get("job_hunting_axes")
            )
            and not (
                item.get("category") == "work_value"
                and item.get("evaluation_group") == "work_style"
                and not user_information.get("work_style_answers")
            )
        )
    ]

    return {
        "items": filtered_items,
    }


def required_targets(matching_context):
    conditions = (matching_context or {}).get("job", {}).get("required_conditions", {})
    result = []
    for field in ("required_experience", "required_skills", "required_qualifications"):
        values = conditions.get(field, [])
        if isinstance(values, str):
            values = [values]
        for value in values:
            if isinstance(value, str) and value.strip() and value.strip() not in result:
                result.append(value.strip())
    return result


def matching_response_schema(matching_context=None) -> dict:
    """Pydanticの検証条件を保ったままstrict JSON Schemaへ変換する。"""
    schema = OpenAIMatchResponse.model_json_schema()
    def strict(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                strict(value)
        elif isinstance(node, list):
            for value in node:
                strict(value)
    strict(schema)
    # 既存の採点検証と同じ制約を生成時にも適用する。
    item = schema["$defs"]["OpenAIMatchItem"]
    ordinary = deepcopy(item)
    ordinary["properties"]["is_major_required_mismatch"] = {"type": "boolean", "enum": [False]}
    unknown = deepcopy(ordinary)
    unknown["properties"]["judgment"] = {"type": "string", "enum": [NEEDS_CONFIRMATION]}
    ordinary["properties"]["judgment"] = {"type": "string", "enum": ["一致", "一部一致", MISMATCH]}
    ordinary["properties"]["evidence"]["minLength"] = 1
    ordinary["properties"]["evidence"]["pattern"] = r"[\s\S]*\S[\s\S]*"
    major = deepcopy(item)
    major["properties"]["is_major_required_mismatch"] = {"type": "boolean", "enum": [True]}
    major["properties"]["category"] = {"type": "string", "enum": ["required_condition"]}
    major["properties"]["judgment"] = {"type": "string", "enum": [MISMATCH]}
    major["properties"]["weight"] = {"type": "integer", "enum": [1]}
    major["properties"]["evidence"]["minLength"] = 1
    major["properties"]["evidence"]["pattern"] = r"[\s\S]*\S[\s\S]*"
    schema["$defs"]["OpenAIMatchItem"] = {"anyOf": [ordinary, major, unknown]}
    targets = required_targets(matching_context)
    if targets:
        if len(targets) > MAX_AI_ITEMS:
            raise JobMatchingAIResultError("求人の応募必須条件が評価可能な項目数を超えています。")
        # 必須条件は自由配列から分離し、求人側の各条件を必須プロパティとして要求する。
        general = deepcopy(ordinary)
        general_unknown = deepcopy(unknown)
        for branch in (general, general_unknown):
            branch["properties"]["category"] = {"type": "string", "enum": ["hope_condition", "work_value", "career_skill"]}
        schema["$defs"]["OpenAIMatchItem"] = {"anyOf": [general, general_unknown]}
        properties = {}
        for index, target in enumerate(targets):
            branches = deepcopy([ordinary, major, unknown])
            for branch in branches:
                branch["properties"]["category"] = {"type": "string", "enum": ["required_condition"]}
                branch["properties"]["item_name"] = {"type": "string", "enum": [target[:MAX_ITEM_NAME_LENGTH]]}
                branch["properties"]["evaluation_group"] = {"type": "string", "enum": [""]}
                branch["properties"]["weight"] = {"type": "integer", "enum": [1]}
            properties[f"condition_{index}"] = {"anyOf": branches, "description": target}
        schema["properties"]["required_conditions"] = {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}
        schema["required"].append("required_conditions")
        schema["properties"]["items"]["maxItems"] = MAX_AI_ITEMS - len(targets)
    # カテゴリごとの制約も生成時に指定し、別カテゴリのグループ混入を防ぐ。
    def specialize(branches):
        result = []
        for branch in branches:
            for category in branch['properties']['category']['enum']:
                variant = deepcopy(branch)
                props = variant['properties']
                props['category'] = {'type': 'string', 'enum': [category]}
                props['hope_group'] = {'type': 'string', 'enum': sorted(ALLOWED_HOPE_GROUPS) if category == 'hope_condition' else ['']}
                groups = {'hope_condition': [''], 'required_condition': [''],
                          'work_value': ['', 'confirmed_axis', 'work_style'],
                          'career_skill': ['', 'direct_experience', 'portable_skill', 'achievement_reproducibility']}
                props['evaluation_group'] = {'type': 'string', 'enum': groups[category]}
                if category in {'career_skill', 'required_condition'}:
                    props['weight'] = {'type': 'integer', 'enum': [1]}
                result.append(variant)
        return result
    definition = schema['$defs']['OpenAIMatchItem']
    definition['anyOf'] = specialize(definition['anyOf'])
    for condition in schema['properties'].get('required_conditions', {}).get('properties', {}).values():
        condition['anyOf'] = specialize(condition['anyOf'])
    return schema


def request_ai_semantic_evaluation(
    job_id: int,
    matching_context: dict[str, Any],
    model_name: str = DEFAULT_AI_MODEL,
    client: OpenAI | None = None,
) -> JobAISemanticEvaluation:
    """OpenAIへ意味判定を依頼して検証済み結果を返す。"""

    if job_id <= 0:
        raise JobMatchingAIResultError(
            "求人IDが正しくありません"
        )

    normalized_model_name = model_name.strip()

    if not normalized_model_name:
        raise JobMatchingAIResultError(
            "使用するAIモデル名がありません"
        )

    messages = build_ai_matching_messages(
        matching_context
    )

    openai_client = (
        client
        if client is not None
        else OpenAI(
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )
    )

    try:
        response = openai_client.responses.create(
            model=normalized_model_name,
            input=messages,
            text={"format": {"type": "json_schema", "name": "OpenAIMatchResponse",
                             "strict": True, "schema": matching_response_schema(matching_context)}},
            max_output_tokens=(
                MAX_AI_OUTPUT_TOKENS
            ),
            store=False,
        )

    except Exception as error:
        raise JobMatchingAIResultError(
            "AIマッチングの判定を"
            "取得できませんでした。"
            f"（{type(error).__name__}）"
        ) from error

    # SDKの自動parseより先に完了状態を見る。途中のJSONは採点・保存しない。
    if response.status != "completed":
        reason = getattr(response.incomplete_details, "reason", None)
        if reason == "max_output_tokens":
            raise JobMatchingAIResultError("AI評価の回答が出力上限に達し、途中で終了しました。")
        raise JobMatchingAIResultError("AI評価の回答が完了しませんでした。")
    if not response.output_text:
        raise JobMatchingAIResultError("AIマッチングの構造化結果を取得できませんでした")
    try:
        payload = json.loads(response.output_text)
        targets = required_targets(matching_context)
        if targets:
            required = payload.get("required_conditions", {})
            keys = [f"condition_{index}" for index in range(len(targets))]
            if not isinstance(required, dict) or set(required) != set(keys):
                raise ValueError("Missing required condition")
            checks = [required[key] for key in keys]
            for target, check in zip(targets, checks):
                if check.get("category") != "required_condition" or check.get("item_name") != target[:MAX_ITEM_NAME_LENGTH]:
                    raise ValueError("Invalid required condition")
            payload = {"items": [*payload.get("items", []), *checks]}
        parsed_response = OpenAIMatchResponse.model_validate(payload)
    except (ValueError, TypeError, AttributeError):
        # 入力・生成本文を例外ログに含めない。
        raise JobMatchingAIResultError("AI評価の回答形式を検証できませんでした。") from None
    payload = parsed_response.model_dump()
    from services.selected_skill_rules import apply_selected_skill_rules
    payload = apply_selected_skill_rules(payload, matching_context)

    filtered_payload = (
        filter_unavailable_categories(
            payload=payload,
            matching_context=(
                matching_context
            ),
        )
    )

    return build_ai_semantic_evaluation(
        job_id=job_id,
        payload=filtered_payload,
        model_name=normalized_model_name,
    )
