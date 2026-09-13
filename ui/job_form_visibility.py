"""フォームの条件付き欄をブラウザー内だけで開閉する。"""
from pathlib import Path
import streamlit as st
from streamlit.components.v2 import component

_visibility = component('metea_job_form_visibility', js=Path(__file__).with_suffix('.js').read_text(encoding='utf-8'))
RULES = [{'control': 'job_form_has_interview_count', 'target': 'job_conditional_has_interview_count', 'value': None}, {'control': 'job_form_fixed_overtime_system', 'target': 'job_conditional_fixed_overtime_system', 'value': 'あり'}, {'control': 'job_form_has_annual_holidays', 'target': 'job_conditional_has_annual_holidays', 'value': None}, {'control': 'job_form_has_scheduled_work_hours', 'target': 'job_conditional_has_scheduled_work_hours', 'value': None}, {'control': 'job_form_has_break_minutes', 'target': 'job_conditional_has_break_minutes', 'value': None}, {'control': 'job_form_has_overtime', 'target': 'job_conditional_has_overtime', 'value': None}, {'control': 'job_form_probation_period_status', 'target': 'job_conditional_probation_period_status', 'value': 'あり'}, {'control': 'job_form_has_planned_hires', 'target': 'job_conditional_has_planned_hires', 'value': None}, {'control': 'job_form_has_employee_count', 'target': 'job_conditional_has_employee_count', 'value': None}]


def install_job_form_visibility():
    install_visibility(RULES,key='job_form_visibility')


def install_visibility(rules, key):
    selectors=','.join('.st-key-'+r['target'] for r in rules)
    if selectors:
        st.html('<style>'+selectors+'{display:none}</style>')
    _visibility(key=key,data={'rules':rules},height=0)
