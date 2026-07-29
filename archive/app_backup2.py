import base64
from pathlib import Path
from textwrap import dedent

import streamlit as st


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
# 画像ファイルの場所
# ========================================

ASSETS_DIR = Path(__file__).parent / "assets"


# ========================================
# SVG画像をHTMLで表示する関数
# ========================================

def svg_image(filename, width):
    """
    assetsフォルダ内のSVGファイルを読み込み、
    HTMLで表示できるimgタグへ変換する関数
    """

    file_path = ASSETS_DIR / filename

    if not file_path.exists():
        return f"""
        <div style="
            color: #D92D20;
            font-size: 13px;
        ">
            {filename} が見つかりません
        </div>
        """

    svg = file_path.read_text(
        encoding="utf-8"
    )

    encoded_svg = base64.b64encode(
        svg.encode("utf-8")
    ).decode("utf-8")

    return f"""
    <img
        src="data:image/svg+xml;base64,{encoded_svg}"
        width="{width}"
        alt=""
        style="
            display: block;
            max-width: 100%;
        "
    >
    """


# ========================================
# 丸背景付きメニューアイコン
# ========================================

def menu_icon(filename, background_color):
    return f"""
    <div style="
        width: 82px;
        height: 82px;
        border-radius: 50%;
        background-color: {background_color};
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 4px;
        flex-shrink: 0;
    ">
        {svg_image(filename, 48)}
    </div>
    """


# ========================================
# CSS
# ========================================

st.html(
    dedent(
        """
        <style>

        /* ページ全体 */
        .stApp {
            background-color: #FBFCFE;
        }

        /* 中央の表示領域 */
        .block-container {
            max-width: 1280px;
            padding-top: 5rem;
            padding-bottom: 4rem;
        }

        /* Streamlit上部ヘッダー */
        header[data-testid="stHeader"] {
            background-color: rgba(255, 255, 255, 0.96);
        }

        /* サイドバーの開閉ボタン周辺 */
        [data-testid="stSidebarCollapsedControl"] {
            color: #253550;
        }

        /* 見出し */
        h1,
        h2,
        h3,
        h4 {
            color: #16233A;
            letter-spacing: -0.03em;
        }

        /* 本文 */
        p {
            color: #344054;
            line-height: 1.8;
        }

        /* カード */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E7EE;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(31, 42, 55, 0.045);
        }

        /* カード内の余白 */
        div[data-testid="stVerticalBlockBorderWrapper"]
        > div {
            padding-top: 0.15rem;
            padding-bottom: 0.15rem;
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

        /* 通常ボタンにマウスを乗せたとき */
        .stButton > button:hover {
            border-color: #246BFD;
            color: #246BFD;
            background-color: #F5F8FF;
        }

        /* 青いボタン */
        .stButton > button[kind="primary"] {
            background-color: #246BFD;
            border-color: #246BFD;
            color: #FFFFFF;
        }

        /* 青いボタンにマウスを乗せたとき */
        .stButton > button[kind="primary"]:hover {
            background-color: #1858D8;
            border-color: #1858D8;
            color: #FFFFFF;
        }

        /* 区切り線 */
        hr {
            border: none;
            border-top: 1px solid #E8ECF2;
            margin-top: 0.4rem;
            margin-bottom: 1.5rem;
        }

        /* caption */
        [data-testid="stCaptionContainer"] {
            color: #8A94A6;
        }

        </style>
        """
    )
)


# ========================================
# ヘッダー
# ========================================

header_logo, header_menu = st.columns(
    [2, 1]
)

with header_logo:
    st.html(
        dedent(
            f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 34px;
                padding: 3px 0 18px 0;
            ">

                <!--
                    logo.svgには下部にキャッチコピーも含まれるため、
                    高さを制限してロゴ部分だけ表示しています
                -->
                <div style="
                    width: 190px;
                    height: 65px;
                    overflow: hidden;
                    display: flex;
                    align-items: flex-start;
                    flex-shrink: 0;
                ">
                    <div style="
                        width: 190px;
                        transform: translateY(-2px);
                    ">
                        {svg_image("logo.svg", 190)}
                    </div>
                </div>

                <div style="
                    font-size: 16px;
                    font-weight: 600;
                    color: #253550;
                    white-space: nowrap;
                ">
                    自分が見えた、道が見えた。
                </div>

            </div>
            """
        )
    )

with header_menu:
    st.html(
        dedent(
            """
            <div style="
                display: flex;
                justify-content: flex-end;
                align-items: center;
                gap: 27px;
                padding-top: 18px;
                font-size: 15px;
                font-weight: 600;
                color: #344054;
                white-space: nowrap;
            ">

                <div style="
                    display: flex;
                    align-items: center;
                    gap: 7px;
                ">
                    <span style="
                        width: 22px;
                        height: 22px;
                        border: 1.8px solid #263246;
                        border-radius: 50%;
                        display: inline-flex;
                        justify-content: center;
                        align-items: center;
                        font-size: 14px;
                        line-height: 1;
                    ">
                        ?
                    </span>

                    <span>使い方</span>
                </div>

                <div style="
                    display: flex;
                    align-items: center;
                    gap: 7px;
                ">
                    <span style="
                        font-size: 21px;
                        line-height: 1;
                    ">
                        ⚙
                    </span>

                    <span>設定</span>
                </div>

                <div style="
                    display: flex;
                    align-items: center;
                    gap: 7px;
                ">
                    <span style="
                        font-size: 21px;
                        line-height: 1;
                    ">
                        ⇥
                    </span>

                    <span>ログアウト</span>
                </div>

            </div>
            """
        )
    )

st.divider()


# ========================================
# メイン画面
# ========================================

left_column, right_column = st.columns(
    [1, 1.1],
    gap="large"
)


# ========================================
# 左側
# ========================================

with left_column:

    # キャッチコピー
    st.html(
        dedent(
            """
            <div style="
                padding: 20px 8px 28px 8px;
            ">

                <div style="
                    font-size: 46px;
                    font-weight: 800;
                    line-height: 1.3;
                    color: #10203A;
                    letter-spacing: -0.05em;
                ">
                    納得できる一歩を。
                </div>

                <div style="
                    margin-top: 22px;
                    font-size: 17px;
                    line-height: 1.9;
                    color: #344054;
                ">
                    あなたの価値観や経験を整理し、<br>
                    求人との相性を見える化することで、<br>
                    納得できる応募判断をサポートします。
                </div>

            </div>
            """
        )
    )

    # ------------------------------------
    # ① 自分を知る
    # ------------------------------------

    with st.container(border=True):
        icon_column, text_column = st.columns(
            [1, 4],
            gap="medium"
        )

        with icon_column:
            st.html(
                menu_icon(
                    "user.svg",
                    "#EEF4FF"
                )
            )

        with text_column:
            st.markdown("### ① 自分を知る")

            st.write(
                "あなたの情報や価値観を整理しましょう"
            )

            if st.button(
                "自分を知るページを開く →",
                key="open_profile"
            ):
                st.info(
                    "自分を知るページへ移動します。"
                )

    st.write("")

    # ------------------------------------
    # ② 求人を比較する
    # ------------------------------------

    with st.container(border=True):
        icon_column, text_column = st.columns(
            [1, 4],
            gap="medium"
        )

        with icon_column:
            st.html(
                menu_icon(
                    "compare.svg",
                    "#EAF9F4"
                )
            )

        with text_column:
            st.markdown("### ② 求人を比較する")

            st.write(
                "求人を比較・分析して、相性を見える化します"
            )

            if st.button(
                "求人比較ページを開く →",
                key="open_compare"
            ):
                st.info(
                    "求人比較ページへ移動します。"
                )

    st.write("")

    # ------------------------------------
    # ③ 応募後を管理する
    # ------------------------------------

    with st.container(border=True):
        icon_column, text_column = st.columns(
            [1, 4],
            gap="medium"
        )

        with icon_column:
            st.html(
                menu_icon(
                    "flag.svg",
                    "#FFF4E8"
                )
            )

        with text_column:
            st.markdown("### ③ 応募後を管理する")

            st.write(
                "応募状況やマイルストーンを管理しましょう"
            )

            if st.button(
                "応募管理ページを開く →",
                key="open_application"
            ):
                st.info(
                    "応募管理ページへ移動します。"
                )

    st.write("")

    # ------------------------------------
    # 設定
    # ------------------------------------

    with st.container(border=True):
        icon_column, text_column = st.columns(
            [1, 4],
            gap="medium"
        )

        with icon_column:
            st.html(
                menu_icon(
                    "settings.svg",
                    "#F4EFFF"
                )
            )

        with text_column:
            st.markdown("### 設定")

            st.write(
                "アカウント情報や各種設定を行います"
            )

            if st.button(
                "設定を開く →",
                key="open_settings"
            ):
                st.info(
                    "設定ページへ移動します。"
                )


# ========================================
# 右側
# ========================================

with right_column:

    # ------------------------------------
    # 次の一歩
    # ------------------------------------

    with st.container(border=True):
        next_icon, next_text = st.columns(
            [1, 4],
            gap="medium"
        )

        with next_icon:
            st.html(
                f"""
                <div style="
                    width: 92px;
                    height: 92px;
                    border-radius: 50%;
                    background-color: #EEF4FF;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin-top: 8px;
                ">
                    {svg_image("sparkle.svg", 58)}
                </div>
                """
            )

        with next_text:
            st.markdown("### 次の一歩")

            st.write(
                "まだ入力が完了していない項目があります。"
            )

            st.write(
                "まずは「基本情報」から始めてみましょう。"
            )

        if st.button(
            "基本情報を入力する　→",
            type="primary",
            use_container_width=False,
            key="start_basic_information"
        ):
            st.success(
                "基本情報の入力画面を開きます。"
            )

    st.write("")

    # ------------------------------------
    # 期限が近いタスク
    # ------------------------------------

    with st.container(border=True):

        task_title, task_link = st.columns(
            [3, 1]
        )

        with task_title:
            st.markdown(
                "### 期限が近いタスク"
            )

        with task_link:
            st.caption(
                "すべてのタスクを見る"
            )

        task_data = [
            (
                "🔴",
                "7/24（水）",
                "A社",
                "履歴書を提出",
                "あと1日"
            ),
            (
                "🟠",
                "7/25（木）",
                "B社",
                "面接準備",
                "あと2日"
            ),
            (
                "🟡",
                "7/26（金）",
                "C社",
                "企業研究を深める",
                "あと3日"
            )
        ]

        for (
            color,
            date,
            company,
            task,
            remaining
        ) in task_data:

            task_columns = st.columns(
                [0.4, 1.25, 0.9, 2.4, 0.9]
            )

            task_columns[0].write(color)
            task_columns[1].write(date)
            task_columns[2].write(company)
            task_columns[3].write(task)
            task_columns[4].caption(remaining)

    st.write("")

    # ------------------------------------
    # 最近の活動
    # ------------------------------------

    with st.container(border=True):

        activity_title, activity_link = st.columns(
            [3, 1]
        )

        with activity_title:
            st.markdown(
                "### 最近の活動"
            )

        with activity_link:
            st.caption(
                "すべて見る"
            )

        activity_data = [
            (
                "👤",
                "プロフィールを更新しました",
                "7/22 14:30"
            ),
            (
                "📄",
                "A社の求人を登録しました",
                "7/22 10:15"
            ),
            (
                "⚖️",
                "比較結果を保存しました",
                "7/21 16:45"
            )
        ]

        for (
            icon,
            activity,
            time
        ) in activity_data:

            activity_columns = st.columns(
                [0.5, 3.5, 1.2]
            )

            activity_columns[0].write(icon)
            activity_columns[1].write(activity)
            activity_columns[2].caption(time)

    st.write("")

    # ------------------------------------
    # 今日のひとこと
    # ------------------------------------

    st.html(
        dedent(
            """
            <div style="
                padding: 20px 24px;
                border-radius: 16px;
                border: 1px solid #DCE7FC;
                background:
                    linear-gradient(
                        135deg,
                        #F3F7FF 0%,
                        #EDF4FF 100%
                    );
            ">

                <div style="
                    font-size: 15px;
                    font-weight: 700;
                    color: #246BFD;
                    margin-bottom: 10px;
                ">
                    🌱 今日のひとこと
                </div>

                <div style="
                    font-size: 15px;
                    line-height: 1.8;
                    color: #263246;
                ">
                    焦らなくても大丈夫です。<br>
                    納得できる一歩は、
                    きっと未来につながります。
                </div>

            </div>
            """
        )
    )