"""求人関連画面で共通使用するレイアウト。"""

import base64
from pathlib import Path

import streamlit as st


ASSETS_DIR = (
    Path(__file__).resolve().parent.parent
    / "assets"
)


def svg_data_uri(
    filename: str,
) -> str:
    """SVGをHTML画像として表示できる形式に変換する。"""

    svg_path = ASSETS_DIR / filename

    svg_text = svg_path.read_text(
        encoding="utf-8"
    )

    encoded_svg = base64.b64encode(
        svg_text.encode("utf-8")
    ).decode("ascii")

    return (
        "data:image/svg+xml;base64,"
        f"{encoded_svg}"
    )


def render_job_navigation(
    active_page: str,
) -> None:
    """求人関連画面の左ナビゲーションを表示する。"""

    logo_uri = svg_data_uri(
        "logo.svg"
    )

    navigation_items = [
        (
            "home",
            "⌂",
            "ダッシュボード",
        ),
        (
            "job_list",
            "▣",
            "求人一覧",
        ),
        (
            "job_registration",
            "＋",
            "求人登録",
        ),
        (
            "application_list",
            "♡",
            "応募管理",
        ),
        (
            "application_dashboard",
            "▥",
            "活動分析",
        ),
        (
            "basic_info",
            "●",
            "基本情報",
        ),
        (
            "hope_conditions",
            "◎",
            "希望条件",
        ),
        (
            "job_hunting_axis",
            "◇",
            "就活の軸",
        ),
        (
            "work_values",
            "◉",
            "価値観",
        ),
        (
            "career",
            "▤",
            "職務経歴・スキル",
        ),
        (
            "settings",
            "⚙",
            "設定",
        ),
        (
            "help",
            "?",
            "ヘルプ",
        ),
    ]

    effective_active_page = active_page

    if active_page in (
        "job_detail",
        "job_comparison",
    ):
        effective_active_page = "job_list"
    if active_page in (
        "application_detail",
        "selection_preparation",
        "milestones",
        "activity_history",
    ):
        effective_active_page = "application_list"


    navigation_links = []

    for page_name, icon, label in navigation_items:
        navigation_href = f"?page={page_name}"
        if page_name == "application_list":
            navigation_href = (
                "?page=application_list&focus=all"
            )

        is_active = (
            page_name
            == effective_active_page
        )

        active_class = (
            " metea-side-link-active"
            if is_active
            else ""
        )

        active_style = (
            "background:#1268f3;"
            "color:#ffffff;"
            if is_active
            else ""
        )

        navigation_links.append(
            f'<a class="metea-side-link'
            f'{active_class}" '
            f'href="{navigation_href}" '
            f'target="_self" '
            f'style="{active_style}">'
            f'<span class="metea-side-icon">'
            f'{icon}</span>'
            f'<span>{label}</span>'
            f'</a>'
        )

    navigation_html = (
        '<nav class="metea-side-navigation">'
        '<div class="metea-side-logo-frame">'
        f'<img class="metea-side-logo" '
        f'src="{logo_uri}" '
        f'alt="MeTeA">'
        '</div>'
        '<div class="metea-side-group-label">'
        '求人管理'
        '</div>'
        + "".join(navigation_links)
        + '</nav>'
    )

    st.markdown(
        """
        <style>
        header[data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            width: calc(100% - 250px);
            max-width: 1380px;
            margin-left: 250px;
            margin-right: 0;
            padding-left: 32px;
            padding-right: 32px;
        }

        .metea-side-navigation,
        .metea-side-navigation * {
            box-sizing: border-box;
        }

        .metea-side-navigation {
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            z-index: 999;
            width: 240px;
            overflow-y: auto;
            padding: 24px 16px;
            background: #ffffff;
            border-right: 1px solid #e3e8f0;
            box-shadow: 2px 0 8px rgba(30, 56, 94, 0.04);
        }

        .metea-side-logo-frame {
            width: 160px;
            height: 64px;
            margin: 0 auto 20px;
            overflow: hidden;
            display: grid;
            place-items: center;
        }

        .metea-side-logo {
            display: block;
            width: 160px;
            height: 64px;
            object-fit: contain;
            transform: scale(2);
        }

        .metea-side-group-label {
            margin: 24px 12px 8px;
            color: #1268f3;
            font-size: 12px;
            font-weight: 700;
        }

        .metea-side-link {
            display: flex;
            align-items: center;
            gap: 12px;
            min-height: 44px;
            margin-bottom: 4px;
            padding: 10px 12px;
            color: #24344d !important;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none !important;
        }

        .metea-side-link:hover {
            background: #f1f6ff;
            color: #1268f3 !important;
        }

        .metea-side-navigation
        a.metea-side-link-active {
            background: #1268f3 !important;
            color: #ffffff !important;
        }

        .metea-side-navigation
        a.metea-side-link-active span {
            color: #ffffff !important;
        }

        .metea-side-navigation
        a.metea-side-link-active:hover {
            background: #0759d9 !important;
            color: #ffffff !important;
        }

        .metea-side-icon {
            width: 20px;
            flex: 0 0 20px;
            text-align: center;
            font-size: 17px;
        }

        @media (max-width: 900px) {
            .metea-side-navigation {
                display: none;
            }

            .block-container {
                width: 100%;
                max-width: none;
                margin-left: 0;
                padding-left: 20px;
                padding-right: 20px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        navigation_html,
        unsafe_allow_html=True,
    )
