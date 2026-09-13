import json
import unittest
from services.evaluation_categories import categorize_details


class CategoryTest(unittest.TestCase):
    def test_semantic_subgroups_and_rule_rows(self):
        semantic = [dict(item_name="課題解決", reason="経験", category="career_skill", evaluation_group="portable_skill"), dict(item_name="Excel", reason="使用", category="required_condition", evaluation_group=""), dict(item_name="自律性", reason="合致", category="work_value", evaluation_group="confirmed_axis")]
        details = [dict(item_name=item["item_name"], reason=item["reason"], judgment="一致") for item in semantic]
        details.append(dict(item_name="電車移動時間", reason="42分", judgment="一致"))
        result = categorize_details(details, json.dumps({"items":semantic}))
        self.assertEqual(result["career_skill"][0]["subgroup"], "ポータブルスキル")
        self.assertEqual(result["work_value"][0]["subgroup"], "確定軸")
        self.assertEqual(result["required_condition"][0]["item_name"], "Excel")
        self.assertEqual(result["hope_condition"][0]["item_name"], "電車移動時間")
        self.assertEqual(sum(map(len,result.values())), len(details))

    def test_missing_or_ambiguous_metadata_is_not_guessed(self):
        details = [dict(item_name="経験", reason="理由")]
        self.assertEqual(len(categorize_details(details, "")["unknown"]), 1)
        items = [dict(item_name="経験",category=category) for category in ("career_skill","required_condition")]
        self.assertEqual(len(categorize_details(details, json.dumps({"items":items}))["unknown"]), 1)

    def test_subgroup_is_html_escaped(self):
        from unittest.mock import patch
        from pages.job_detail import render_evaluation_detail_table
        with patch("pages.job_detail.st.markdown") as render:
            render_evaluation_detail_table([dict(item_name="Excel",judgment="一致",reason="確認",subgroup="<script>",category="required_condition")])
        self.assertIn("&lt;script&gt;",render.call_args.args[0])
        self.assertIn('<div>分類</div>', render.call_args.args[0])
        self.assertIn('求人側の応募必須条件', render.call_args.args[0])
