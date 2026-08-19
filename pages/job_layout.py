"""求人関連画面で共通使用するレイアウト。"""

import base64
from pathlib import Path

import streamlit as st

from ui.design_system import apply_common_design_system


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

    apply_common_design_system()

    logo_uri = svg_data_uri(
        "logo.svg"
    )

    groups = (
        ("self_discovery", "user.svg", "① 自分を知る", (
            ("basic_info", "自分の情報を登録する"),
            ("profile_review", "登録した内容を見直す"),
        )),
        ("job_list", "compare.svg", "② 求人を比較する", (
            ("job_list", "求人一覧"),
            ("job_registration", "求人を登録する"),
        )),
        ("application_list", "flag.svg", "③ 応募後を管理する", (
            ("application_list", "応募管理"),
            ("selection_preparation", "選考準備"),
        )),
        ("application_dashboard", "analytics.svg", "④ 活動を振り返る", (
        ("application_dashboard", "選考通過率レポート"),
        )),
    )

    effective_active_page = active_page

    if active_page in (
        "job_detail",
        "job_comparison",
    ):
        effective_active_page = "job_list"
    if active_page in (
        "application_detail",
        "activity_history",
    ):
        effective_active_page = "application_list"
    if active_page == "milestones":
        effective_active_page = "application_list"


    def href(page_name: str) -> str:
        if page_name == "application_list":
            return "?page=application_list&focus=all"
        return f"?page={page_name}"

    navigation_groups = []
    for parent_page, icon_file, parent_label, children in groups:
        child_pages = {page for page, _ in children}
        is_group_active = effective_active_page in child_pages or effective_active_page == parent_page
        icon_uri = svg_data_uri(icon_file)
        child_links = []
        for child_page, child_label in children:
            active_class = " metea-side-child-active" if effective_active_page == child_page else ""
            child_links.append(
                f'<a class="metea-side-child{active_class}" href="{href(child_page)}" target="_self">'
                f'<span></span>{child_label}</a>'
            )
        group_class = " metea-side-group-active" if is_group_active else ""
        navigation_groups.append(
            f'<section class="metea-side-section{group_class}">'
            f'<a class="metea-side-parent" href="{href(parent_page)}" target="_self">'
            f'<img src="{icon_uri}" alt=""><strong>{parent_label}</strong></a>'
            f'<div class="metea-side-children">{"".join(child_links)}</div></section>'
        )

    settings_icon = svg_data_uri("nav-settings.svg")
    help_icon = svg_data_uri("help.svg")

    home_active = " metea-side-home-active" if effective_active_page == "home" else ""
    settings_active = " metea-side-utility-active" if effective_active_page == "settings" else ""
    help_active = " metea-side-utility-active" if effective_active_page == "help" else ""
    navigation_html = (
        '<nav class="metea-side-navigation">'
        '<div class="metea-side-logo-frame">'
        f'<img class="metea-side-logo" '
        f'src="{logo_uri}" '
        f'alt="MeTeA">'
        '</div>'
        f'<a class="metea-side-home{home_active}" href="?page=home" target="_self"><span>ホーム</span></a>'
        + "".join(navigation_groups)
        + '<div class="metea-side-utilities">'
        + f'<a class="{settings_active.strip()}" href="?page=settings" target="_self"><img src="{settings_icon}" alt="">設定</a>'
        + f'<a class="{help_active.strip()}" href="?page=help" target="_self"><img src="{help_icon}" alt="">ヘルプ</a>'
        + '</div>'
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

        .metea-side-home,
        .metea-side-parent,
        .metea-side-child,
        .metea-side-utilities a {
            display: flex;
            align-items: center;
            text-decoration: none !important;
            color: var(--metea-ink) !important;
        }
        .metea-side-home { min-height:40px; padding:9px 12px; margin-bottom:10px; border-radius:9px; font-size:13px; font-weight:800; }
        .metea-side-section { margin: 0 0 7px; padding:5px; border-radius:12px; }
        .metea-side-parent { gap:10px; min-height:40px; padding:8px; border-radius:9px; font-size:13px; }
        .metea-side-parent img, .metea-side-utilities img { width:20px; height:20px; object-fit:contain; }
        .metea-side-children { margin:1px 0 3px 27px; padding-left:10px; border-left:1px solid #dce6f3; }
        .metea-side-child { gap:7px; min-height:31px; padding:5px 7px; border-radius:7px; font-size:12px; font-weight:600; }
        .metea-side-child > span { width:4px; height:4px; border-radius:50%; background:#b5c2d3; }
        .metea-side-home:hover, .metea-side-parent:hover, .metea-side-child:hover, .metea-side-utilities a:hover {
            background: #f1f6ff;
            color: #1268f3 !important;
        }
        .metea-side-group-active { background:#f7faff; }
        .metea-side-group-active .metea-side-parent { color:#0759df !important; }
        .metea-side-child-active { background:#eaf2ff !important; color:#0759df !important; font-weight:800; }
        .metea-side-child-active > span { background:#146cff; }
        .metea-side-home-active,.metea-side-utility-active { background:#eaf2ff !important; color:#0759df !important; font-weight:800 !important; }
        .metea-side-utilities { margin-top:14px; padding-top:12px; border-top:1px solid #e4eaf2; }
        .metea-side-utilities a { gap:10px; min-height:36px; padding:7px 11px; border-radius:8px; font-size:12px; font-weight:700; }

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
