"""保存済み評価のメタデータから、グラフと明細の対応を表示する。"""
import json

CATEGORIES = {
    "hope_condition": ("希望条件", "#146cff", "勤務地・給与・働き方など、あなたの希望との一致度"),
    "work_value": ("就活の軸", "#10a773", "確定した就活の軸と、仕事の進め方との一致度"),
    "career_skill": ("職務経歴・スキル", "#f59b00", "業務経験・活かせるスキル・実績の再現性"),
    "required_condition": ("求人側の応募必須条件", "#7954eb", "求人が応募者に求める経験・スキル・資格"),
    "unknown": ("分類情報のない過去の項目", "#64748b", "保存済み情報から分類を特定できない項目"),
}
GROUPS = {
    "confirmed_axis": "確定軸", "work_style": "仕事の進め方",
    "direct_experience": "業務経験の接続度", "portable_skill": "ポータブルスキル",
    "achievement_reproducibility": "実績・再現性",
}


def categorize_details(details, result_json):
    try:
        payload = json.loads(result_json)
        semantic = payload.get("items") if isinstance(payload, dict) else None
    except (ValueError, TypeError):
        semantic = None
    valid = isinstance(semantic, list) and all(isinstance(item, dict) for item in semantic)
    grouped = {key: [] for key in CATEGORIES}
    for detail in details:
        matches = [item for item in semantic if item.get("item_name") == detail.get("item_name")] if valid else []
        exact = [item for item in matches if item.get("reason", "").strip() == detail.get("reason", "").strip()]
        candidates = exact or matches
        labels = {(item.get("category"), item.get("evaluation_group", "")) for item in candidates}
        if len(labels) == 1:
            category, group = next(iter(labels))
        elif not candidates and valid:
            # 現行評価の生成元：保存JSONはAI項目。表示文章にだけある項目は希望条件のルール判定。
            category, group = "hope_condition", ""
        else:
            category, group = "unknown", ""
        category = category if category in CATEGORIES else "unknown"
        grouped[category].append(dict(detail, subgroup=GROUPS.get(group, "")))
    return grouped
