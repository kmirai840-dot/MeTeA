import streamlit as st
from services.operator_service import require_operator, list_users, read_user_data, export_user_data


def render_operator_page():
    require_operator()
    st.title('運営者：利用者データ')
    st.caption('保存内容の確認・出力専用です。利用者の入力をこの画面から変更することはできません。')
    if st.button('設定へ戻る'):
        st.query_params['page'] = 'settings'
        st.rerun()
    users = list_users()
    labels = {u['id']: f"ID {u['id']} ｜ {u['email'] or '未連携の既存データ'} ｜ {u['display_name'] or ''}" for u in users}
    uid = st.selectbox('確認する利用者', list(labels), format_func=labels.get, index=None, placeholder='利用者を選択')
    if uid is None:
        return
    data = read_user_data(uid)
    st.caption('論理削除済みの保存データも含みます。認証用の識別子は出力しません。')
    st.dataframe([{'保存先': t, '件数': len(rows)} for t, rows in data['tables'].items()], hide_index=True)
    table = st.selectbox('確認する保存内容', list(data['tables']))
    rows = data['tables'][table]
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.info('この保存先にはデータがありません。')
    # 毎回認可・再取得し、セッションや共有キャッシュに出力を蓄積しない。
    st.download_button('この利用者のデータをダウンロード（CSV・JSON）',
                       data=export_user_data(uid), file_name=f'metea_user_{uid}.zip',
                       mime='application/zip', on_click='rerun')
