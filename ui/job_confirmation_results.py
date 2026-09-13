"""確認結果を求人の追加情報として保存・編集する。"""
import streamlit as st
from services.job_confirmation_service import save_confirmation_result, restore_confirmation_item
from services.confirmation_input_service import CHOICES, NUMBERS, OTHER, UNKNOWN, choices_for, input_kind, restore_input, format_input
from ui.job_evaluation_area import refresh_confirmation_area


def render_result_form(job_id, item):
    with st.expander('確認結果を入力・編集', expanded=False, key=f"confirmation_form_{job_id}_{item['item_key']}"):
        with st.form(f"confirmation_result_{job_id}_{item['item_key']}"):
            name = item['item_name']
            kind = input_kind(name)
            value, notes = restore_input(name, item.get('result_text', ''))
            if kind == 'choice':
                options = choices_for(name)
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
    st.markdown('#### 確認済み・許容した項目')
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


def render_batch_confirmation_form(job_id, items, dismissed, records, render_profile):
    """選択・入力・確認不要・復元を一回の送信にまとめる。"""
    from services.job_confirmation_service import save_confirmation_decisions
    confirmed = [r for r in records if r['status'] == 'confirmed' or r.get('accepted')]
    represented = {r['item_name'] for r in confirmed}
    items = [i for i in items if i['item_name'] not in represented]
    dismissed = [i for i in dismissed if i['item_name'] not in represented]
    with st.container(key=f'confirmation_batch_shell_{job_id}'), st.form(f'confirmation_batch_{job_id}', border=False):
        st.caption('入力内容は、最後の「確認結果をまとめて保存・評価を更新」を押すまで保存されません。未入力の項目は変更しません。')
        entries = []
        restores = []
        company_col, profile_col = st.columns(2, gap='medium')
        with company_col:
            with st.container(border=True, key=f'company_confirmation_card_{job_id}'):
                st.markdown('<div class="action-confirmation-heading company"><span>●</span><strong>企業・求人元へ確認</strong></div>', unsafe_allow_html=True)
                st.caption('面談や応募前に、企業へ確認したい内容です。')
                if not items:
                    st.success('現在、確認が必要な項目はありません。')
                for index, item in enumerate(items):
                    entries.append(_batch_fields(job_id, item, False))
                    if index < len(items) - 1:
                        st.divider()
        with profile_col:
            render_profile()
        if dismissed:
            with st.expander(f'以前に確認不要にした項目（{len(dismissed)}件）'):
                st.caption('以前の判断は保持しています。許容する場合は、本人判断を選んで保存してください。')
                for item in dismissed:
                    entries.append(_batch_fields(job_id, item, False))
        submitted = st.form_submit_button('確認結果をまとめて保存・評価を更新')
        if submitted:
            changes, errors = [], []
            for item, value, notes, remove_fact, accepted, adjustment in entries:
                name = item['item_name']
                change = dict(item_name=name, item_reason=item.get('reason', item.get('item_reason', '')),
                              accepted=accepted, score_adjustment=adjustment, remove_fact=remove_fact)
                if not remove_fact and (value is not None or notes.strip()):
                    try:
                        change['result_text'] = format_input(name, value, notes)
                        if not change['result_text'] or len(change['result_text']) > 2000:
                            raise ValueError('確認結果を1〜2000文字で入力してください。')
                    except ValueError as error:
                        errors.append(f'{name}：{error}')
                        continue
                changes.append(change)
            if errors:
                for error in errors:
                    st.error(error)
            elif not changes:
                st.info('保存する入力・変更がありません。')
            else:
                try:
                    count = save_confirmation_decisions(job_id, changes)
                except ValueError as error:
                    st.error(str(error))
                else:
                    from ui.job_evaluation_area import refresh_saved_confirmation_details
                    from services.job_confirmation_service import build_confirmation_item_key
                    reset_keys = []
                    for change in changes:
                        key = build_confirmation_item_key(change['item_name'], change['item_reason'])
                        if change.get('remove_fact'):
                            reset_keys.extend([f'batch_{job_id}_{key}_value', f'batch_{job_id}_{key}_notes'])
                        if not change.get('accepted'):
                            reset_keys.append(f'batch_{job_id}_{key}_adjustment')
                    st.session_state[f'confirmation_reset_keys_{job_id}'] = reset_keys
                    refresh_saved_confirmation_details(job_id, count)



def _batch_fields(job_id, item, confirmed):
    name = item['item_name']
    prefix = f"batch_{job_id}_{item['item_key']}"
    st.html("""<style>
    [class*="st-key-acceptance_item_"]:not(:has([class*="st-key-acceptance_control_"] input:checked)) [class*="st-key-acceptance_adjustment_"] { display: none; }
    </style>""")
    with st.container(border=confirmed, key='acceptance_item_'+prefix):
        st.markdown(f"**{name}**")
        st.caption(item.get('reason', item.get('item_reason', '')))
        if name == '老舗・安定企業':
            st.caption('確認できた設立からの年数を選択してください。経営状況などは補足に記載できます。年数だけで経営の安定性を判断するものではありません。')
        with st.expander('確認結果を入力・編集', key=f"confirmation_form_{job_id}_{item['item_key']}"):
            value, notes = restore_input(name, item.get('result_text', ''))
            kind = input_kind(name)
            if kind == 'choice':
                options = choices_for(name)
                value = st.selectbox('確認結果', options, index=options.index(value) if value in options else None,
                                     placeholder='確認した結果を選択してください', key=prefix+'_value')
            elif kind == 'number':
                unit, maximum = NUMBERS[name]
                value = st.number_input(f'{name}（{unit}）', min_value=0, max_value=maximum, value=value, step=1, key=prefix+'_value')
            elif kind == 'time':
                value = st.time_input(name, value=value, step=60, key=prefix+'_value')
            notes = st.text_area('確認した内容' if kind == 'text' else '補足（任意）', value=notes, max_chars=2000, key=prefix+'_notes')
        with st.container(key='acceptance_control_'+prefix):
            accepted = st.checkbox('許容', value=bool(item.get('accepted')), key=prefix+'_accepted')
        with st.container(key='acceptance_adjustment_'+prefix):
            options = ['そのまま', '加点', '減点']
            adjustment = st.selectbox('点数への反映', options,
                index={0:0, 1:1, -1:2}.get(item.get('score_adjustment', 0), 0), key=prefix+'_adjustment')
            st.caption('加点＋1点・減点−1点、合計±5点まで。')
        remove_fact = st.checkbox('保存済みの確認結果を取り消す', key=prefix+'_action') if item.get('status') == 'confirmed' else False
    return item, value, notes, remove_fact, accepted, {'そのまま':0, '加点':1, '減点':-1}[adjustment]
