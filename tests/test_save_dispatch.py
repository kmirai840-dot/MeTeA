"""保存クリック時に旧画面を描き直さず、保存成功後だけ遷移する。"""
from contextlib import ExitStack
from datetime import date
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from pages import basic_info as b,hope_conditions as h,work_values as w,job_hunting_axis as a
from models import BasicInfo,JobHuntingAxis
from data.master_data import OCCUPATION_OPTIONS,EMPLOYMENT_TYPE_OPTIONS

class SaveDispatchTest(unittest.TestCase):
    def test_one_click_saves_before_redrawing_old_page(self):
        hope=dict(hope_occupations=[OCCUPATION_OPTIONS[0]],hope_prefectures=['福岡県'],hope_location_priority_1_福岡県='want',hope_minimum_salary=300,hope_desired_salary=400,hope_employment_types=[EMPLOYMENT_TYPE_OPTIONS[0]])
        values={}
        for key,options in [('important_value',w.IMPORTANT_VALUE_OPTIONS),('rewarding_scene',w.REWARDING_SCENE_OPTIONS),('strength_environment',w.STRENGTH_ENVIRONMENT_OPTIONS)]:
            values.update({f'{key}_{i}':v for i,v in enumerate(options[:3],1)})
        values.update({'work_style_'+q['question_type']:3 for q in w.WORK_STYLE_QUESTIONS})
        cases=[
            (b,'render_basic_info_page','basic_next','hope_conditions','save_basic_info',dict(load_basic_info_draft=None,load_basic_info=BasicInfo('試験','利用者','female',date(1994,9,16),'福岡県','福岡市','駅','id'),save_basic_info_draft=None)),
            (h,'render_hope_conditions_page','hope_conditions_save','work_values','save_hope_conditions_data',dict(load_hope_conditions_draft=hope,save_hope_conditions_draft=None)),
            (w,'show_page','work_values_save','job_hunting_axis','save_work_values_data',dict(load_work_values_draft=values,save_work_values_draft=None)),
            (a,'render_job_hunting_axis_page','job_hunting_axis_save','career','save_job_hunting_axis_data',dict(load_job_hunting_axis_draft=None,load_job_hunting_axis_data=[JobHuntingAxis('テスト軸','判断基準',1,'manual')])),
        ]
        for module,entry,button,target,save_name,mocks in cases:
            with self.subTest(page=module.__name__),ExitStack() as stack:
                stack.enter_context(patch('ui.job_form_visibility.install_visibility'))
                for name,value in mocks.items():stack.enter_context(patch.object(module,name,return_value=value))
                if module is b:stack.enter_context(patch.object(b,'format_station_candidate',side_effect=lambda value:value))
                theme=stack.enter_context(patch.object(module,'apply_self_discovery_theme'))
                save=stack.enter_context(patch.object(module,save_name,return_value=[] if module in (w,a) else None))
                app=AppTest.from_string(f"import streamlit as st\nimport {module.__name__} as page\nif st.query_params.get('page') == '{target}': st.title('NEXT')\nelse: page.{entry}()\n").run(timeout=20)
                self.assertFalse(app.exception)
                before=theme.call_count
                app.button(key=button).click().run(timeout=20)
                self.assertFalse(app.exception)
                self.assertEqual(app.title[0].value,'NEXT')
                self.assertEqual(save.call_count,1)
                self.assertEqual(theme.call_count,before,'old page was redrawn before save')

    def test_invalid_basic_submission_keeps_latest_other_fields(self):
        profile=BasicInfo('試験','利用者','female',date(1994,9,16),'福岡県','福岡市','駅','id')
        with patch.object(b,'load_basic_info_draft',return_value=None),patch.object(b,'load_basic_info',return_value=profile),patch.object(b,'save_basic_info_draft'),patch.object(b,'save_basic_info') as save,patch.object(b,'format_station_candidate',side_effect=lambda value:value):
            app=AppTest.from_string('from pages.basic_info import render_basic_info_page\nrender_basic_info_page()').run(timeout=20)
            app.text_input(key=b.FAMILY_NAME_KEY).set_value('')
            app.text_input(key=b.MUNICIPALITY_KEY).set_value('入力中の市区町村')
            app.button(key='basic_next').click().run(timeout=20)
            self.assertFalse(app.exception);save.assert_not_called()
            self.assertEqual(app.text_input(key=b.FAMILY_NAME_KEY).value,'')
            self.assertEqual(app.text_input(key=b.MUNICIPALITY_KEY).value,'入力中の市区町村')
            self.assertNotIn('page',app.query_params)

if __name__=='__main__':unittest.main()
