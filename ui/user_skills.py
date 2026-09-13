import streamlit as st
from services.user_skill_service import load_skills, save_skills
from services.user_skill_choices import SKILL_OPTIONS, parse_skill_choices, format_skill_choices


@st.fragment
def render_user_skills():
    with st.expander("使用できるツール・スキル", expanded=True):
        st.caption("職歴の有無にかかわらず、仕事・学習・個人活動で身につけたスキルを登録できます（任意）。求人の応募必須条件やスキルの評価に使用します。")
        work, learning, notes = parse_skill_choices(load_skills())
        with st.form("user_skills_form"):
            selected_work = st.multiselect("仕事で使用したスキル（複数選択）", SKILL_OPTIONS, default=work)
            selected_learning = st.multiselect("学習・個人活動で使用したスキル（複数選択）", SKILL_OPTIONS, default=learning)
            st.caption("実際にできることを選択してください。選択しなかった項目を「できない」とは判定しません。")
            text = st.text_area(
                "その他のスキル・補足（任意）",
                value=notes, max_chars=3000, height=100,
                placeholder="選択肢にないスキルや、使用期間・できることの詳細を入力できます。",
            )
            submitted = st.form_submit_button("ツール・スキルを保存する")
        if submitted:
            try:
                changed = save_skills(format_skill_choices(selected_work, selected_learning, text))
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("保存しました。変更内容は次の求人評価に反映されます。" if changed else "保存済みの内容と同じです。")
