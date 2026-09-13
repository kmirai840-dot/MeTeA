"""選択式スキルは利用者と合意した粒度で照合する。"""
import re
from services.user_skill_choices import parse_skill_choices


def apply_selected_skill_rules(payload, context):
    information = context.get("user_matching_information", {})
    work, learning, _ = parse_skill_choices(information.get("self_reported_tools_and_skills", ""))
    if "Excel関数" not in work + learning:
        return payload
    requirements = context.get("job", {}).get("required_conditions", {}).get("required_skills", [])
    if isinstance(requirements, str):
        requirements = [requirements]
    covered = set()
    for text in requirements:
        if not isinstance(text, str):
            continue
        # 関数の例示はまとめて合致。別言語・資格・経験年数等の追加要件は対象外。
        if (re.search(r"excel", text, re.I) and re.search(r"関数|SUM|IF|LOOKUP", text, re.I)
            and not re.search(r"VBA|マクロ|Power\s*Query|SQL|Python|Java|GAS|資格|[0-9０-９]+\s*年", text, re.I)
            and ("実務" not in text or "Excel関数" in work)):
            covered.add(text[:100])
    items = []
    for item in payload.get("items", []):
        if item.get("category") == "required_condition" and item.get("item_name") in covered:
            item = dict(item, judgment="一致", weight=1, is_major_required_mismatch=False,
                reason="求人のExcel関数の要件は、登録した「Excel関数」と一致しています。関数名ごとの確認は行いません。",
                evidence=f"求人：{item['item_name']}／本人の選択：Excel関数")
        items.append(item)
    return dict(payload, items=items)
