"""「自分を知る」の入力・確認を選ぶ入口画面。"""

import base64
from pathlib import Path

import streamlit as st

from pages.self_discovery_theme import apply_self_discovery_theme
from pages.job_layout import render_job_navigation


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def _asset_data_uri(filename: str) -> str:
    encoded = base64.b64encode(
        (ASSETS_DIR / filename).read_bytes()
    ).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def show_page() -> None:
    apply_self_discovery_theme(1, render_stepper=False)
    render_job_navigation("self_discovery")
    input_icon = _asset_data_uri("user.svg")
    review_icon = _asset_data_uri("review-basic.svg")
    st.markdown(
        f"""
        <span class="metea-self-hub-marker"></span>
        <style>
        .metea-input-stepper{{display:none!important}}
        [data-testid="stMainBlockContainer"]:has(.metea-self-hub-marker){{
          width:calc(100% - 290px)!important;max-width:1180px!important;
          margin:92px 24px 48px 266px!important;padding:38px 42px 46px!important;
          box-sizing:border-box;
          font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
        }}
        [data-testid="stMainBlockContainer"]:has(.metea-self-hub-marker) .metea-self-hub-head,
        [data-testid="stMainBlockContainer"]:has(.metea-self-hub-marker) .metea-self-hub-head *,
        [data-testid="stMainBlockContainer"]:has(.metea-self-hub-marker) .metea-self-hub-guide,
        [data-testid="stMainBlockContainer"]:has(.metea-self-hub-marker) .metea-self-hub-card,
        [data-testid="stMainBlockContainer"]:has(.metea-self-hub-marker) .metea-self-hub-card *{{
          font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif!important;
        }}
        .metea-self-hub-back{{display:inline-flex;padding:8px 14px;border:1px solid #a9c9ff;
          border-radius:10px;background:#fff;color:#146cff!important;font-size:13px;font-weight:700;
          line-height:1.4;text-decoration:none!important}}
        .metea-self-hub-head{{margin:30px 0 24px}}
        .metea-self-hub-head h1{{margin:0 0 8px;color:#071a36;font-size:clamp(1.9rem,2.3vw,2.35rem);
          line-height:1.3;letter-spacing:.015em;font-weight:800}}
        .metea-self-hub-head p{{margin:0;color:#52647d;font-size:15px;line-height:1.75}}
        .metea-self-hub-guide{{display:flex;align-items:center;gap:14px;margin:0 0 18px;
          color:#17365f;font-size:15px;font-weight:800;line-height:1.5}}
        .metea-self-hub-guide::after{{content:"";height:1px;flex:1;background:#dbe6f4}}
        .metea-self-hub-grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
        .metea-self-hub-card{{display:flex;min-height:290px;flex-direction:column;padding:27px;
          border:1px solid #cbdaf0;border-radius:15px;background:#fff;
          box-shadow:0 7px 22px rgba(31,65,114,.065);text-decoration:none!important}}
        .metea-self-hub-card--input{{border-color:#8db8ff;background:#f4f8ff}}
        .metea-self-hub-card--review{{border-color:#b8cae4;background:#fff}}
        .metea-self-hub-icon{{width:62px;height:62px;display:grid;place-items:center;border-radius:50%;
          background:#e9f2ff;margin-bottom:19px}}
        .metea-self-hub-card--review .metea-self-hub-icon{{background:#f0f4fa}}
        .metea-self-hub-icon img{{display:block;width:40px;height:40px}}
        .metea-self-hub-card h2{{margin:0 0 8px!important;color:#071a36!important;font-size:20px!important;
          line-height:1.35!important;font-weight:800!important}}
        .metea-self-hub-card p{{margin:0;color:#405673;font-size:14px;line-height:1.7}}
        .metea-self-hub-card ul{{margin:16px 0 22px;padding-left:1.2rem;color:#52647d;
          font-size:13px;line-height:1.75;flex:1}}
        .metea-self-hub-action{{display:flex;align-items:center;justify-content:center;min-height:43px;
          border-radius:9px;font-size:14px;font-weight:700;text-decoration:none!important}}
        .metea-self-hub-card--input .metea-self-hub-action{{background:#146cff;color:#fff!important}}
        .metea-self-hub-card--review .metea-self-hub-action{{border:1px solid #8db8ff;
          background:#fff;color:#146cff!important}}
        .metea-self-hub-card--input:hover .metea-self-hub-action{{background:#0759df}}
        .metea-self-hub-card--review:hover .metea-self-hub-action{{background:#eef5ff}}
        .metea-self-hub-card,.metea-self-hub-card *{{text-decoration:none!important}}
        @media(max-width:760px){{
          [data-testid="stMainBlockContainer"]:has(.metea-self-hub-marker){{width:100%!important;
            margin:0!important;padding:26px 18px 36px!important;border-radius:0!important}}
          .metea-self-hub-grid{{grid-template-columns:1fr}}
          .metea-self-hub-card{{min-height:260px}}
        }}
        </style>
        <a class="metea-self-hub-back" href="?page=home">← トップへ戻る</a>
        <div class="metea-self-hub-head">
          <h1>自分を知る</h1>
          <p>あなたのことを教えてください。新しく登録することも、これまでの内容を振り返って整えることもできます。</p>
        </div>
        <div class="metea-self-hub-guide">今のあなたに合うところから、一緒に始めましょう</div>
        <div class="metea-self-hub-grid">
          <a class="metea-self-hub-card metea-self-hub-card--input" href="?page=basic_info">
            <span class="metea-self-hub-icon"><img src="{input_icon}" alt=""></span>
            <h2>① 自分の情報を登録する</h2>
            <p>基本情報から職務経歴・スキルまで、順番に新しい情報を登録します。</p>
            <ul><li>途中になっている入力を再開できます</li><li>5つのステップに沿って登録できます</li></ul>
            <span class="metea-self-hub-action">登録を始める →</span>
          </a>
          <a class="metea-self-hub-card metea-self-hub-card--review" href="?page=profile_review">
            <span class="metea-self-hub-icon"><img src="{review_icon}" alt=""></span>
            <h2>② 登録した内容を見直す</h2>
            <p>登録済みの情報をカテゴリごとに確認し、必要な内容を編集します。</p>
            <ul><li>登録状況を一覧で確認できます</li><li>各カードからその場で編集できます</li></ul>
            <span class="metea-self-hub-action">内容を見直す →</span>
          </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
