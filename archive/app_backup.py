import streamlit as st
from textwrap import dedent

# ページ全体の設定
st.set_page_config(
    page_title="MeTeA",
    page_icon='🧭',
    layout="wide"
)

# デザイン設定
st.html(
    dedent(
        """
        <style>
    }

        /*ページ全体*/
        .stApp{
            background-color: #F7F8FA;
        }

        /*中央の表示領域*/
        .block-container{
            max-width: 1200px;
            padding-top: 3rem;
            padding-bottom: 4rem;
        }

        /*見出し*/
        h1,h2,h3{
            color:#202938;
            letter-spacing: -0.03em;
        }

        /*デフォルトの文字*/
        p{
            color: #46505F;
            line-height: 1.8;
            }

        /*デフォルトのボタン*/
        .stButton > button{
            width:100%;
            min-height:52px;
            border-radius:12px;
            border:1px solid #D9DFE8;
            background-color:#FFFFFF;
            color:#263246;
            font-size:16px;
            font-weight:600;
            transition: 0.2s;
        }

        /* ボタンにマウスを乗せたとき */
        .stButton > button:hover{
            border-color:#246BFD;
            color: #246BFD;
            background-color: #F4F7FF;
        }

        /* カード*/
        div[data-testid="stVerticalBlockBorderWrapper"]{
            background-color: #FFFFFF;
            border: 1px solid #E3E7ED;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(31, 42, 55, 0.05);
        }

        /* 上部メニューを少し目立たなくする*/
        header[data-testid="stHeader"]{
            background-color: transparent;
        }

        </style>
        """
    ),
)


# ヘッダー
header_left,header_right=st.columns([3,1])

with header_left:
    st.html(
        dedent(
            """
            <div style="margin-bottom: 35px;">
                <div style="
                    font-size: 42px;
                    font-weight: 800;
                    color: #202938;
                    letter-spacing: -0.04em;
                ">

                    MeTeA

                </div>

                <div style="
                    font-size: 16px;
                    color: #6B7480;
                    margin-top: 4px;
                ">

                    自分が見えた、道が見えた。
                </div>
            </div>
            """
        ),
    )

with header_right:
    st.html(
        dedent(
            """
            <div style="
                text-align: right;
                padding-top: 15px;
                color: #667085;
                font-size: 14px;
            ">

                ヘルプ　　設定　　ログアウト

            </div>
            """
        ),
    )


# メイン画面
left_column,right_column = st.columns([1.15,1],gap="large")


# 左側
with left_column:
    st.html(
        dedent(
            """
            <div style="padding: 15px 0 25px 0;">
                <div style="
                font-size: 44px;
                font-weight: 800;
                line-height: 1.25;
                color: #202938;
                letter-spacing: -0.04em;
            ">

                納得できる一歩を。
            </div>

            <div style="
                font-size: 17px;
                line-height: 1.9;
                color: #5A6573;
                margin-top: 18px;
                max-width: 520px;
            ">

                自分を知り、求人を比較し、<br>
                納得できる選択を支える就職活動サポートサービスです。

            </div>
        </div>
        """
        ),
    )


    st.subheader("メニュー")

    if  st.button(
            "利用を開始する",type="primary",use_container_width=True):
        st.write("利用開始ボタンが押されました")

    if st.button("下書きから再開する",use_container_width=True):
        st.write("下書きを開きます。")

    if st.button("就活状況を確認する",use_container_width=True):
        st.write("就活状況を確認します。")

    if st.button("初めての方へ",use_container_width=True):
        st.write("使い方を表示します。")

# 右側
with right_column:
    st.subheader("次の一歩")

    with st.container(border=True):
        st.markdown("#### 🧭 今日のおすすめ")
        st.write("履歴書は完成しています。")
        st.write("今日は志望動機を見直してみませんか？")

        if st.button(
            "続きを開く",
            use_container_width=True,
            key="next_step"
        ):
            st.success("志望動機の編集画面を開きます。")


    st.subheader("期限が近いタスク")

    with st.container(border=True):
        task_left,task_right = st.columns([3,1])

        with task_left:
            st.markdown("#### A社")
            st.write("応募書類の提出")
            st.caption("期限：2026年7月26日")

        with task_right:
            st.warning("残り3日")

    st.subheader("最近の活動")

    with st.container(border=True):
        st.write("✓ プロフィールを更新しました")
        st.caption("本日 18:30")

        st.write("✓ A社の求人を登録しました")
        st.caption("昨日 20:15")

        st.write("✓ 比較結果を保存しました")
        st.caption("7月21日 14:10")

    st.subheader("今日のひとこと")

    with st.container(border=True):
        st.markdown(
            """
            **比較できたことも、大きな一歩です。**

            迷いながら考えた時間も、
            納得できる選択につながっています。
            """
        )
        
