"""「自分を知る」各画面で共有するMeTeA UIテーマ。"""

from html import escape

import streamlit as st

from ui.design_system import apply_common_design_system


SELF_DISCOVERY_STEPS = (
    ("基本情報", "あなたについて"),
    ("希望条件", "これからのこと"),
    ("価値観", "あなたの特徴"),
    ("就活の軸", "こだわること"),
    ("職務経歴・スキル", "経験を整理"),
)


def _render_input_stepper(current_step: int) -> None:
    """現在地が分かる入力ステップを左側へ表示する。"""

    items = []
    for index, (title, description) in enumerate(SELF_DISCOVERY_STEPS, start=1):
        if index < current_step:
            state_class, marker = "is-complete", "✓"
        elif index == current_step:
            state_class, marker = "is-current", str(index)
        else:
            state_class, marker = "is-upcoming", str(index)

        items.append(
            f"""<li class="metea-step {state_class}">
            <span class="metea-step-marker">{marker}</span>
            <span class="metea-step-copy"><strong>{escape(title)}</strong>
            <small>{escape(description)}</small></span></li>"""
        )

    progress = int(current_step / len(SELF_DISCOVERY_STEPS) * 100)
    st.markdown(
        f"""<aside class="metea-input-stepper">
        <p class="metea-stepper-title">入力ステップ</p>
        <ol>{''.join(items)}</ol>
        <div class="metea-stepper-progress"><span>入力の進捗</span>
        <strong>{current_step} / {len(SELF_DISCOVERY_STEPS)}</strong>
        <div><i style="width:{progress}%"></i></div></div>
        <div class="metea-stepper-tip"><strong>入力のポイント</strong>
        <p>正解はありません。今の自分に近い内容を選んでください。あとから何度でも変更できます。</p></div>
        </aside>""",
        unsafe_allow_html=True,
    )


def apply_self_discovery_theme(
    current_step: int,
    *,
    render_stepper: bool = True,
) -> None:
    """TOP画面を基準にした共通スタイルを現在の画面へ適用する。"""

    apply_common_design_system()

    st.markdown(
        """
        <style>
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: var(--metea-page);
        }

        [data-testid="stMainBlockContainer"],
        section.main > div.block-container {
            max-width: 1440px;
            margin: 108px 28px 48px 244px;
            padding: 36px 44px 48px;
            background: var(--metea-panel);
            border: 1px solid var(--metea-line);
            border-radius: 18px;
            box-shadow: var(--metea-shadow);
        }

        [data-testid="stMainBlockContainer"] h1 {
            color: var(--metea-ink);
            font-size: clamp(2rem, 3vw, 2.75rem);
            line-height: 1.25;
            letter-spacing: 0.02em;
            margin-bottom: 0.35rem;
        }

        [data-testid="stMainBlockContainer"] h2,
        [data-testid="stMainBlockContainer"] h3 {
            color: var(--metea-ink);
            letter-spacing: 0.01em;
        }

        [data-testid="stCaptionContainer"],
        [data-testid="stMainBlockContainer"] .stCaption,
        [data-testid="stMainBlockContainer"] small {
            color: var(--metea-muted) !important;
            font-size: 0.93rem !important;
            line-height: 1.7;
        }

        [data-testid="stProgress"] {
            margin: 14px 0 22px;
        }

        [data-testid="stProgress"] > div > div {
            border-radius: 999px;
            overflow: hidden;
        }

        [data-testid="stProgressBarTrack"] {
            background: #e5edf7 !important;
        }

        [data-testid="stProgressBarTrack"] > div {
            background: linear-gradient(90deg, var(--metea-blue), #3f8cff);
        }

        [data-testid="stAlert"] {
            border-radius: 12px;
            padding: 14px 16px;
        }

        /* Streamlit既定の内側背景を消し、色付き案内が二重に見えるのを防ぐ。 */
        [data-testid="stAlert"] > div,
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
            background: transparent !important;
        }

        [data-testid="stWidgetLabel"] [aria-hidden="true"] {
            color: #e5484d !important;
        }

        .metea-priority-guide {
            margin: 22px 0 18px;
            padding: 18px;
            border: 1px solid #cfe0fa;
            border-radius: 14px;
            background: #f7fbff;
        }
        .metea-priority-guide__intro { display:flex; gap:12px; align-items:flex-start; }
        .metea-priority-guide__intro p { margin:4px 0 0; color:var(--metea-muted); }
        .metea-priority-guide__icon {
            display:grid; place-items:center; width:28px; height:28px; border-radius:50%;
            color:#fff; background:var(--metea-blue); font-weight:800;
        }
        .metea-priority-guide__items {
            display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px; margin-top:16px;
        }
        .metea-priority-guide__items > div {
            padding:12px; border:1px solid #dbe5f2; border-radius:10px; background:#fff;
        }
        .metea-priority-guide__items span {
            display:inline-flex; padding:3px 9px; border-radius:999px; font-size:.82rem; font-weight:800;
        }
        .metea-priority-guide__items p { margin:8px 0 0; color:#40516a; font-size:.88rem; }
        .metea-priority-guide .is-required { color:#b42318; background:#fff0ef; }
        .metea-priority-guide .is-desired { color:#075fdc; background:#eaf3ff; }
        .metea-priority-guide .is-acceptable { color:#08745d; background:#eaf9f4; }
        .metea-priority-guide .is-neutral { color:#405168; background:#e8edf3; }

        .metea-selected-rank { min-height:58px; display:flex; gap:10px; align-items:center; }
        .metea-selected-rank span {
            display:grid; place-items:center; min-width:34px; height:34px; border-radius:50%;
            background:#eaf3ff; color:var(--metea-blue); font-weight:800;
        }
        .metea-scale-end { display:flex; gap:10px; align-items:center; color:var(--metea-ink); }
        .metea-scale-end span { color:var(--metea-blue); font-weight:800; }
        .metea-scale-end--right { justify-content:flex-end; text-align:right; }
        .metea-scale-caption { margin:8px 0 0; text-align:center; color:var(--metea-muted); font-size:.9rem; }

        .metea-method-illustration {
            display:grid; place-items:center; width:62px; height:62px; margin-bottom:14px;
            border-radius:16px; font-size:2.15rem; line-height:1; font-weight:500;
        }
        .metea-method-illustration--upload { background:#eaf3ff; color:#146cff; }
        .metea-method-illustration--manual { background:#fff4e8; color:#e97812; }
        .metea-career-guide {
            display:flex; gap:14px; height:100%; margin-top:14px; padding:18px;
            border:1px solid #dbe5f2; border-radius:14px; background:#fff; color:#40516a;
        }
        .metea-career-guide--ai { background:#f3f8ff; border-color:#cfe0fa; }
        .metea-career-guide__icon {
            display:grid; place-items:center; flex:0 0 34px; width:34px; height:34px;
            border-radius:50%; background:#eaf8f2; color:#0b8f68; font-weight:900;
        }
        .metea-career-guide--ai .metea-career-guide__icon { background:#e7f1ff; color:var(--metea-blue); }
        .metea-career-guide strong { color:var(--metea-ink); font-size:1rem; }
        .metea-career-guide ul { margin:10px 0 0; padding-left:1.15rem; }
        .metea-career-guide li { margin:5px 0; }
        .metea-career-guide p { margin:10px 0 0; line-height:1.75; }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-method-illustration--upload) {
            background:#f7fbff; border-color:#bed8ff !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-method-illustration--manual) {
            background:#fffaf4; border-color:#f3d3aa !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-method-illustration--manual) button {
            border-color:#eda24d; color:#c96500;
        }

        [data-testid="stHorizontalBlock"] [data-testid="stRadio"] > div {
            justify-content: center;
            gap: 0.9rem;
        }

        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stForm"],
        [data-testid="stExpander"] {
            background: #ffffff;
            border-color: var(--metea-line) !important;
            border-radius: 14px !important;
            box-shadow: 0 5px 16px rgba(31, 65, 114, 0.045);
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 4px;
        }

        [data-testid="stExpander"] {
            margin-bottom: 12px;
            overflow: hidden;
        }

        [data-testid="stExpander"] summary {
            min-height: 64px;
            color: var(--metea-ink);
            font-weight: 700;
            font-size: 1rem;
        }

        [data-testid="stExpander"] summary:hover {
            background: #f8fbff;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-baseweb="select"] > div,
        [data-testid="stDateInput"] input {
            min-height: 44px;
            background: #f8fafc !important;
            border-color: #d8e1ed !important;
            border-radius: 9px !important;
            color: var(--metea-ink) !important;
        }

        [data-testid="stTextArea"] textarea {
            min-height: 108px;
            line-height: 1.65;
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stMainBlockContainer"] label p {
            color: #152843;
            font-weight: 650;
            font-size: 0.94rem;
        }

        [data-testid="stButton"] > button,
        [data-testid="stFormSubmitButton"] > button,
        [data-testid="stDownloadButton"] > button {
            min-height: 42px;
            border: 1px solid #9dc1ff;
            border-radius: 9px;
            background: #ffffff;
            color: #075fdc;
            font-weight: 700;
            box-shadow: none;
            transition: transform 0.15s ease, box-shadow 0.15s ease,
                background 0.15s ease;
        }

        [data-testid="stButton"] > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover,
        [data-testid="stDownloadButton"] > button:hover {
            border-color: var(--metea-blue);
            background: #f2f7ff;
            color: var(--metea-blue-dark);
            transform: translateY(-1px);
        }

        [data-testid="stButton"] > button[kind="primary"],
        [data-testid="stFormSubmitButton"] > button[kind="primary"],
        [data-testid="stButton"] button[data-testid="stBaseButton-primary"],
        [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"] {
            border-color: var(--metea-blue);
            background: linear-gradient(180deg, #2878ff, #0862f1);
            color: #ffffff;
            box-shadow: 0 7px 16px rgba(20, 108, 255, 0.22);
        }

        [data-testid="stButton"] button[data-testid="stBaseButton-primary"] p,
        [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"] p {
            color: #ffffff !important;
        }

        [data-testid="stButton"] > button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover,
        [data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover,
        [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"]:hover {
            border-color: var(--metea-blue-dark);
            background: linear-gradient(180deg, #1e70f5, #0759df);
            color: #ffffff;
        }

        [data-testid="stFileUploader"] {
            padding: 18px;
            border: 1px dashed #a9c8f8;
            border-radius: 12px;
            background: #f8fbff;
        }

        [data-testid="stDivider"] {
            margin: 1.4rem 0;
        }

        hr {
            border-color: #e7edf5 !important;
        }

        .metea-input-stepper {
            position: fixed; z-index: 20; top: 108px; left: 24px;
            width: 188px; color: var(--metea-ink);
        }
        .metea-stepper-title { margin: 0 0 18px; font-size: .88rem; font-weight: 800; }
        .metea-input-stepper ol { list-style: none; margin: 0; padding: 0; }
        .metea-step { position: relative; display: flex; gap: 12px; min-height: 62px; }
        .metea-step:not(:last-child)::after {
            content: ""; position: absolute; left: 15px; top: 32px; bottom: 0;
            width: 2px; background: #dbe4f0;
        }
        .metea-step-marker {
            position: relative; z-index: 1; display: grid; place-items: center;
            width: 32px; height: 32px; flex: 0 0 32px; border-radius: 50%;
            border: 1px solid #cbd7e6; background: #fff; color: #7b899c;
            font-size: .8rem; font-weight: 800;
        }
        .metea-step.is-complete .metea-step-marker,
        .metea-step.is-current .metea-step-marker {
            border-color: var(--metea-blue); background: var(--metea-blue); color: #fff;
        }
        .metea-step.is-current .metea-step-copy strong { color: var(--metea-blue-dark); }
        .metea-step-copy { padding-top: 2px; }
        .metea-step-copy strong { display: block; font-size: .87rem; line-height: 1.35; }
        .metea-step-copy small { display: block; margin-top: 3px; color: #8491a4; font-size: .69rem; line-height: 1.35; }
        .metea-stepper-progress, .metea-stepper-tip {
            margin-top: 18px; padding: 14px; border: 1px solid #d7e5f8;
            border-radius: 12px; background: #f7fbff;
        }
        .metea-stepper-progress { font-size: .75rem; }
        .metea-stepper-progress strong { float: right; color: var(--metea-blue); }
        .metea-stepper-progress div { height: 5px; margin-top: 10px; overflow: hidden; border-radius: 99px; background: #e4ebf4; }
        .metea-stepper-progress i { display: block; height: 100%; background: var(--metea-blue); }
        .metea-stepper-tip strong { color: #1764c7; font-size: .76rem; }
        .metea-stepper-tip p { margin: 7px 0 0; color: #61728a; font-size: .69rem; line-height: 1.65; }

        @media (max-width: 1100px) {
            .metea-input-stepper { display: none; }
            [data-testid="stMainBlockContainer"], section.main > div.block-container {
                margin: 18px; max-width: none;
            }
        }
        @media (max-width: 900px) {
            .metea-priority-guide__items { grid-template-columns:1fr 1fr; }

            [data-testid="stMainBlockContainer"],
            section.main > div.block-container {
                margin: 0;
                padding: 24px 18px 36px;
                border-left: 0;
                border-right: 0;
                border-radius: 0;
            }

            [data-testid="stMainBlockContainer"] h1 {
                font-size: 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if render_stepper:
        _render_input_stepper(
            max(1, min(current_step, len(SELF_DISCOVERY_STEPS)))
        )
