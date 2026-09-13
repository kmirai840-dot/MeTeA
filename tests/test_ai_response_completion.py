import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from services import job_matching_ai_service as ai

class ResponseCompletionTest(unittest.TestCase):
    def request(self, response):
        client=Mock(); client.responses.create.return_value=response
        with patch.object(ai, 'build_ai_matching_messages', return_value=[]), patch.object(ai,'filter_unavailable_categories',side_effect=lambda **kw:kw['payload']), patch.object(ai,'build_ai_semantic_evaluation',return_value='validated') as build:
            result=ai.request_ai_semantic_evaluation(156,{},client=client)
        return result,client,build

    def test_completed_response_is_validated(self):
        result,client,build=self.request(SimpleNamespace(status='completed',output_text='{"items": []}'))
        self.assertEqual(result,'validated')
        self.assertEqual(client.responses.create.call_args.kwargs['max_output_tokens'],12000)
        self.assertFalse(client.responses.create.call_args.kwargs['store'])
        build.assert_called_once()

    def test_incomplete_json_rejected_before_parsing(self):
        for text in ('{"items": [', '{"items": []}'):
            with self.subTest(text=text), self.assertRaisesRegex(ai.JobMatchingAIResultError,'出力上限'):
                self.request(SimpleNamespace(status='incomplete',incomplete_details=SimpleNamespace(reason='max_output_tokens'),output_text=text))

    def test_invalid_or_refused_response_is_not_accepted(self):
        for text in ('', '{"items": [', '{"items": [{"category":"invalid"}]}'):
            with self.subTest(text=text), self.assertRaises(ai.JobMatchingAIResultError):
                self.request(SimpleNamespace(status='completed',output_text=text))

    def test_strict_schema_retains_all_fields_and_bounds(self):
        schema=ai.matching_response_schema()
        item=schema['$defs']['OpenAIMatchItem']['anyOf'][0]
        self.assertFalse(item['additionalProperties'])
        self.assertEqual(set(item['required']),set(ai.OpenAIMatchItem.model_fields))
        self.assertEqual(item['properties']['reason']['maxLength'],ai.MAX_REASON_LENGTH)
        self.assertEqual(schema['properties']['items']['maxItems'],40)
        import jsonschema
        valid=dict(category='work_value',evaluation_group='confirmed_axis',item_name='test',judgment='一致',reason='reason',weight=1,hope_group='',evidence='求人と本人の根拠',is_major_required_mismatch=False)
        jsonschema.validate({'items':[valid]},schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({'items':[dict(valid, hope_group='salary_employment')]}, schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({'items':[dict(valid,is_major_required_mismatch=True)]},schema)
        jsonschema.validate({'items':[dict(valid,category='required_condition',evaluation_group='',judgment='不一致',is_major_required_mismatch=True)]},schema)
        for evidence in ('', '  \n\t'):
            for judgment in ('一致', '一部一致', '不一致'):
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate({'items':[dict(valid,evidence=evidence,judgment=judgment)]},schema)
            jsonschema.validate({'items':[dict(valid,evidence=evidence,judgment='要確認')]},schema)

if __name__=='__main__': unittest.main()
