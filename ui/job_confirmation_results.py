"""確認結果を求人の追加情報として保存・編集する。"""
import streamlit as st
from services.job_confirmation_service import save_confirmation_result, restore_confirmation_item
from services.confirmation_input_service import CHOICES, NUMBERS, OTHER, UNKNOWN, input_kind, restore_input, format_input
from ui.job_evaluation_area import refresh_confirmation_area


def render_result_form(job_id, item):
    with st.expander('確認結果を入力・編集', expanded=False, key=f"confirmation_form_{job_id}_{item['item_key']}"):
        with st.form(f"confirmation_result_{job_id}_{item['item_key']}"):
            name = item['item_name']
            kind = input_kind(name)
            value, notes = restore_input(name, item.get('result_text', ''))
            if kind == 'choice':
                options = CHOICES[name] + [UNKNOWN, OTHER]
                value = st.selectbox('確認結果', options, index=options.index(value) if value in options else None,
                                     placeholder='確認した結果を選択してください')
            elif kind == 'number':
                unit, maximum = NUMBERS[name]
                value = st.number_input(f'{name}（{unit}）', min_value=0, max_value=maximum, value=value, step=1)
            elif kind == 'time':
                value = st.time_input(name, value=value, step=60)
            notes = st.text_area('確認した内容' if kind == 'text' else '補足（任意）', value=notes, max_chars=2000,
                                 placeholder='確認先・条件など、必要な補足を入力できます。')
            st.caption('求人の追加情報として保存し、AI評価に反映します。確認した事実を入力してください。')
            if st.form_submit_button('確認結果を保存する'):
                try:
                    text = format_input(name, value, notes)
                    save_confirmation_result(job_id, item['item_name'], item['reason'] if 'reason' in item else item['item_reason'], text)
                except ValueError as error:
                    st.error(str(error))
                else:
                    refresh_confirmation_area(job_id)


def render_confirmed_results(job_id, records):
    confirmed = [row for row in records if row['status'] == 'confirmed']
    if not confirmed:
        return
    st.markdown('#### 確認済みの追加情報')
    st.caption('求人票とは別に、あなたが企業・求人元へ確認した情報です。AI評価にも使用します。')
    for row in confirmed:
        with st.container(border=True):
            st.write(f"確認済み：{row['item_name']}")
            st.write(row['result_text'])
            st.caption(f"更新日時（UTC）：{row['updated_at']}")
            render_result_form(job_id, row)
            if st.button('確認結果を取り消す', key=f"undo_confirmed_{job_id}_{row['item_key']}"):
                restore_confirmation_item(job_id, row['item_key'])
                refresh_confirmation_area(job_id)
