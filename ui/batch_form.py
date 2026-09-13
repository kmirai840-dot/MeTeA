"""既存の操作ボタンを、入力フォーム内では一括送信として扱う。"""
import streamlit as st
from streamlit.elements.lib.form_utils import is_in_form


def batch_button(label, **kwargs):
    if is_in_form(st._main):
        return st.form_submit_button(label, **kwargs)
    return st.button(label, **kwargs)
