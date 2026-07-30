from pathlib import Path
import base64
from textwrap import dedent
import streamlit as st

ASSETS_DIR = Path(__file__).parent / "assets"


# ========================================
# ページ設定
# ========================================

st.set_page_config(
    page_title="MeTeA",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========================================
# assets
# ========================================

ASSETS_DIR = Path(__file__).parent / "assets"


# ========================================
# SVG表示
# ========================================

def svg_image(filename, width=48):

    path = ASSETS_DIR / filename

    if not path.exists():
        return f"""
        <div style="color:red;">
        {filename} が見つかりません
        </div>
        """

    svg = path.read_text(
        encoding="utf-8"
    )

    svg = base64.b64encode(
        svg.encode("utf-8")
    ).decode()

    return f"""
    <img
        src="data:image/svg+xml;base64,{svg}"
        width="{width}"
        style="
            display:block;
        "
    >
    """


# ========================================
# 丸アイコン
# ========================================

def circle_icon(filename, color):

    return f"""
<div style="
width:82px;
height:82px;
background:{color};
border-radius:50%;
display:flex;
justify-content:center;
align-items:center;
">
    {svg_image(filename)}
</div>
"""


# ========================================
# CSS
# ========================================

st.markdown(
    """
<style>

.stApp{
background:#F8FAFC;
}

.block-container{

max-width:1360px;

padding-top:3rem;

padding-bottom:3rem;

}

h1, h2, h3 {
    color: #1E293B;
    margin-top: 0;
}

h1 {
    margin-bottom: 1rem;
}

h2, h3 {
    margin-bottom: 0.4rem;
}

p {
    color: #475569;
    margin-top: 0;
    margin-bottom: 0.4rem;
    line-height: 1.55;
}

div[data-testid="stVerticalBlockBorderWrapper"]{

border-radius:18px;

border:1px solid #E2E8F0;

box-shadow:
0 8px 24px rgba(0,0,0,.04);

background:white;

}

/* 通常ボタン */
.stButton > button {
    width: 100%;
    min-height: 46px;
    border-radius: 10px;
    border: 1px solid #D9E0EA;
    background-color: #FFFFFF;
    color: #253550;
    font-size: 15px;
    font-weight: 600;
    transition: 0.2s;
}

/* ボタン内の文字 */
.stButton > button p {
    color: inherit;
    white-space: nowrap;
}

/* 通常ボタンにマウスを乗せたとき */
.stButton > button:hover {
    border-color: #246BFD;
    color: #246BFD;
    background-color: #F5F8FF;
}

/* 強調ボタン */
.stButton > button[kind="primary"] {
    background-color: #246BFD;
    border-color: #246BFD;
    color: #FFFFFF;
}

/* 強調ボタンにマウスを乗せたとき */
.stButton > button[kind="primary"]:hover {
    background-color: #1858D8;
    border-color: #1858D8;
    color: #FFFFFF;
}

</style>
""",
    unsafe_allow_html=True
)

# ========================================
# ヘッダー
# ========================================

logo_col, menu_col = st.columns([1.65, 1.35])

with logo_col:

    left, right = st.columns([1, 2])

    with left:
        st.image(
            ASSETS_DIR / "logo.svg",
            width=190
        )

    with right:

        st.html(
            """
            <div style="
                padding-top:28px;
                font-size:17px;
                font-weight:600;
                color:#334155;
            ">
            自分が見えた、道が見えた。
            </div>
            """
        )

with menu_col:

    col1, col2, col3 = st.columns([1.3, 1.3, 1.6])

    with col1:
        st.button(
            "❓ 使い方",
            use_container_width=True
        )

    with col2:
        st.button(
            "⚙ 設定",
            use_container_width=True
        )

    with col3:
        st.button(
            "⇥ ログアウト",
            use_container_width=True
        )

st.divider()




# ========================================
# メインレイアウト
# ========================================

left_column, right_column = st.columns(
    [1, 1.1],
    gap="large"
)

with left_column:

    st.markdown(
        dedent(
            """
            # 納得できる一歩を。

            あなたの価値観や経験を整理し、  
            求人との相性を見える化することで、  
            納得できる応募判断をサポートします。
            """
        )
    )


    # ========================================
    # 自分を知る
    # ========================================

    with st.container(border=True):

        icon, text = st.columns(
            [0.9, 4.8],
            gap="medium"
            )

        with icon:

            st.html(
                circle_icon(
                    "user.svg",
                    "#EEF4FF"
                 )
            )

        with text:

            st.subheader("① 自分を知る")

            st.write(
                "あなたの情報や価値観を整理しましょう。"
            )

            st.button(
                "自分を知るページを開く →",
                key="profile"
            )

    # ========================================
    # 求人を比較する
    # ========================================

    with st.container(border=True):

        icon, text = st.columns([1, 4])

        with icon:
            st.html(
                circle_icon(
                    "compare.svg",
                    "#EAF9F4"
                )
            )

        with text:

            st.subheader("② 求人を比較する")

            st.write(
                "求人を比較・分析して、相性を見える化します。"
            )

            st.button(
                "求人比較ページを開く →",
                key="compare"
            )


    # ========================================
    # 応募後を管理する
    # ========================================

    with st.container(border=True):

        icon, text = st.columns([1, 4])

        with icon:
            st.html(
                circle_icon(
                    "flag.svg",
                    "#FFF4E8"
                )
            )

        with text:

            st.subheader("③ 応募後を管理する")

            st.write(
                "応募状況やマイルストーンを管理します。"
            )

            st.button(
                "応募管理ページを開く →",
                key="application"
            )

    # ========================================
    # 設定
    # ========================================

    with st.container(border=True):

        icon, text = st.columns([1, 4])

        with icon:
            st.html(
                circle_icon(
                    "settings.svg",
                    "#F4EFFF"
                )
            )

        with text:

            st.subheader("設定")

            st.write(
                "アカウント情報や各種設定を変更できます。"
            )

            st.button(
                "設定を開く →",
                key="settings"
            )


with right_column:

    # ========================================
    # 次の一歩
    # ========================================

    with st.container(border=True):

        icon, text = st.columns([1,4])

        with icon:

            st.html(
                circle_icon(
                    "sparkle.svg",
                    "#EEF4FF"
                )
            )

        with text:

            st.subheader("次の一歩")

            st.write(
                "まだ入力が完了していない項目があります。"
            )

            st.write(
                "まずは基本情報から入力してみましょう。"
            )

        st.button(
            "基本情報を入力する →",
            type="primary",
            key="next_action"
            )


    # ========================================
    # 期限が近いタスク
    # ========================================

    with st.container(border=True):

        st.subheader("📅 期限が近いタスク")

        task_list = [

            ("🔴","7/24","A社","履歴書提出","あと1日"),

            ("🟠","7/25","B社","面接準備","あと2日"),

            ("🟡","7/26","C社","企業研究","あと3日"),

        ]

        for color,date,company,task,remain in task_list:

            c1,c2,c3,c4,c5 = st.columns(
                [0.5,1.2,1,2.4,1]
            )

            c1.write(color)

            c2.write(date)

            c3.write(company)

            c4.write(task)

            c5.caption(remain)


    # ========================================
    # 最近の活動
    # ========================================

    with st.container(border=True):

        st.subheader("📝 最近の活動")

        activity = [

            ("👤","プロフィールを更新しました","7/22"),

            ("📄","A社の求人を登録しました","7/22"),

            ("⚖","比較結果を保存しました","7/21"),

        ]

        for icon,text,time in activity:

            c1,c2,c3 = st.columns(
                [0.5,3.5,1]
            )

            c1.write(icon)

            c2.write(text)

            c3.caption(time)


    # ========================================
    # 今日のひとこと
    # ========================================

    with st.container(border=True):

        st.html(
            """
### 🌱 今日のひとこと

焦らなくても大丈夫。

納得できる一歩は、

きっと未来につながります。
"""
        )
