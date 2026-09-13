import streamlit as st
from services.user_skill_service import load_skills, save_skills


@st.fragment
def render_user_skills():
    with st.expander("使用できるツール・スキル", expanded=True):
        st.caption("職歴の有無にかかわらず、仕事・学習・個人活動で身につけたスキルを登録できます（任意）。求人の応募必須条件やスキルの評価に使用します。")
        with st.form("user_skills_form"):
            text = st.text_area(
                "使用できるツール・スキル（できること・使用経験）",
                value=load_skills(), max_chars=3000, height=130,
                placeholder="例：ExcelのSUMIF・VLOOKUPを使って集計できる。ピボットテーブルは講座で学習し、練習課題で使用した。",
            )
            submitted = st.form_submit_button("ツール・スキルを保存する")
        if submitted:
            try:
                changed = save_skills(text)
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("保存しました。変更内容は次の求人評価に反映されます。" if changed else "保存済みの内容と同じです。")
