import unittest
import jsonschema
from services.job_matching_ai_service import matching_response_schema
from services.selected_skill_rules import apply_selected_skill_rules
from services.user_skill_choices import format_skill_choices


class RequiredOutputTest(unittest.TestCase):
    def test_required_condition_cannot_be_omitted(self):
        context = {"job":{"required_conditions":{"required_skills":["Excel関数"]}}}
        schema = matching_response_schema(context)
        with self.assertRaises(jsonschema.ValidationError): jsonschema.validate({"items":[]},schema)
        with self.assertRaises(jsonschema.ValidationError): jsonschema.validate({"items":[],"required_conditions":{}},schema)
        item = dict(category="required_condition",evaluation_group="",item_name="Excel関数",judgment="要確認",reason="不明",weight=1,hope_group="",evidence="",is_major_required_mismatch=False)
        jsonschema.validate({"items":[],"required_conditions":{"condition_0":item}},schema)

    def test_excel_matches_at_selected_granularity(self):
        target = "PCスキル（Excel関数：SUMIF、VLOOKUP、ピボット等が扱えるレベル）"
        context = {"job":{"required_conditions":{"required_skills":[target]}}, "user_matching_information":{"self_reported_tools_and_skills":format_skill_choices(["Excel関数"],[],"")}}
        payload={"items":[dict(category="required_condition",item_name=target,judgment="要確認")]}
        self.assertEqual(apply_selected_skill_rules(payload,context)["items"][0]["judgment"],"一致")
        context["job"]["required_conditions"]["required_skills"]=[target+"・VBA必須"]
        self.assertEqual(apply_selected_skill_rules(payload,context)["items"][0]["judgment"],"要確認")
