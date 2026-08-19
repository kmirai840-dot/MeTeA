"""「自分を知る」で正式保存した内容の確認・カード内編集画面。"""

from dataclasses import replace
from datetime import date, datetime
from html import escape
from pathlib import Path
import base64
from textwrap import dedent

import streamlit as st

from data.master_data import GENDER_LABELS, PRIORITY_LABELS, CAREER_PRIORITY_LABELS
from constants.work_values import MAX_RANKING_SELECTIONS, WORK_STYLE_QUESTIONS, WORK_STYLE_SCORE_LABELS
from services.work_values_service import DETAIL_LABELS, RANKING_QUESTION_LABELS
from models import Career, CareerHistory, HopeConditionItem, JobHuntingAxis, WorkStyleAnswer, WorkValueDetail, WorkValueRanking
from pages.self_discovery_theme import apply_self_discovery_theme
from services.basic_info_service import load_basic_info, load_basic_info_updated_at, save_basic_info, validate_basic_info
from services.career_service import load_career_data, save_career_data
from services.hope_condition_service import load_hope_conditions_data, save_hope_conditions_data
from services.job_hunting_axis_service import load_job_hunting_axis_data, save_job_hunting_axis_data
from services.work_values_service import load_work_values_data, save_work_values_data


CATEGORIES = (
    ("basic", "基本情報", "あなたについて", "氏名・居住地・生年月日・最寄駅", "review-basic.svg"),
    ("hope", "希望条件", "これからのこと", "希望する仕事・勤務地・働き方・入社条件", "review-hope.svg"),
    ("values", "価値観", "あなたの特徴", "大切にしたいこと・やりがい・仕事の進め方", "review-values.svg"),
    ("axis", "就活の軸", "こだわること", "仕事選びで大切にしたい判断基準", "review-axis.svg"),
    ("career", "職務経歴・スキル", "経験を整理", "会社・部署・役割・実績", "review-career.svg"),
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

PRIORITY_OPTIONS = {**PRIORITY_LABELS, **CAREER_PRIORITY_LABELS}


def _styles() -> None:
    st.markdown(
        """
        <span class="metea-profile-review-marker"></span>
        <style>
        [data-testid="stMainBlockContainer"]:has(.metea-profile-review-marker){width:auto!important;max-width:none!important;margin-top:78px!important;margin-right:28px!important;margin-bottom:34px!important;box-sizing:border-box;padding:28px 36px 32px!important;font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}
        .metea-profile-review-marker{display:none!important}
        [data-testid="stMainBlockContainer"]:has(.metea-profile-review-marker) button,
        [data-testid="stMainBlockContainer"]:has(.metea-profile-review-marker) input,
        [data-testid="stMainBlockContainer"]:has(.metea-profile-review-marker) textarea,
        [data-testid="stMainBlockContainer"]:has(.metea-profile-review-marker) select{font-family:inherit!important}
        .metea-review-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin:.35rem 0 1.15rem}
        .metea-input-stepper{display:none!important}
        .metea-review-nav{position:fixed;z-index:20;top:108px;left:24px;width:188px;color:#071a36}.metea-review-nav>strong{display:block;margin-bottom:14px;color:#071a36;font-family:inherit!important;font-size:.9rem;line-height:1.45;font-weight:800;letter-spacing:.01em}.metea-review-nav a{display:block;text-decoration:none!important;color:#52647d!important;border-radius:9px;padding:9px 10px;margin:3px 0;font-size:.78rem;font-weight:700}.metea-review-nav a:hover,.metea-review-nav a.is-active{background:#eaf2ff;color:#0759df!important;text-decoration:none!important}.metea-review-nav small{display:block;margin-top:18px;color:#75839a;line-height:1.55}
        .metea-review-head h1,.metea-basic-title h1{color:#071a36!important;font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif!important;font-size:clamp(1.9rem,2.3vw,2.35rem)!important;line-height:1.3!important;letter-spacing:.015em!important;font-weight:700!important;margin:0 0 8px!important}.metea-review-head p{color:#52647d;font-size:15px;line-height:1.75;font-weight:500;margin:0}
        .metea-review-back{display:inline-flex;align-items:center;color:#146cff!important;text-decoration:none!important;border:1px solid #a9c9ff;border-radius:9px;padding:8px 14px;margin-bottom:24px;background:#fff;font-size:13px;line-height:1.4;font-weight:700;box-shadow:0 2px 7px rgba(20,108,255,.04);transition:background .16s ease,border-color .16s ease,transform .16s ease}.metea-review-back:hover{background:#eef5ff;border-color:#72a6ff;color:#0759df!important;text-decoration:none!important;transform:translateY(-1px)}
        .metea-category-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:18px 0 28px}
        .metea-category-card{display:grid;grid-template-columns:62px minmax(0,1fr) 18px;gap:16px;
          min-height:148px;align-items:center;padding:18px 20px 18px 17px;border:1px solid #e4e9f1;
          border-radius:12px;background:#fff;box-shadow:0 3px 10px rgba(17,42,82,.055);
          text-decoration:none!important;color:#071a36!important;transition:border-color .16s ease,box-shadow .16s ease,transform .16s ease}
        [data-testid="stMarkdownContainer"] a.metea-category-card,
        [data-testid="stMarkdownContainer"] a.metea-category-card:link,
        [data-testid="stMarkdownContainer"] a.metea-category-card:visited,
        [data-testid="stMarkdownContainer"] a.metea-category-card:hover,
        [data-testid="stMarkdownContainer"] a.metea-category-card:active,
        [data-testid="stMarkdownContainer"] a.metea-category-card strong,
        [data-testid="stMarkdownContainer"] a.metea-category-card small,
        [data-testid="stMarkdownContainer"] a.metea-category-card span,
        [data-testid="stMarkdownContainer"] a.metea-category-card p{
          text-decoration:none!important;text-decoration-line:none!important;
          border-bottom:0!important;
        }
        .metea-category-card,.metea-category-card *{font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif!important}
        .metea-category-card:hover{border-color:#8db8ff;transform:translateY(-2px);box-shadow:0 10px 24px rgba(20,108,255,.1)}
        .metea-category-icon{width:62px;height:62px;display:grid;place-items:center;border-radius:50%;background:#eef5ff}.metea-category-icon img{width:40px;height:40px;display:block}
        .metea-category-body{display:flex;min-width:0;flex-direction:column;align-items:flex-start}
        .metea-category-card strong{font-size:20px;line-height:1.3;font-weight:800;letter-spacing:.01em;color:#071a36}.metea-category-card small{color:#66758c;font-size:12px;line-height:1.45;font-weight:600;margin-top:3px}.metea-category-card p{font-size:13px;line-height:1.55;font-weight:500;color:#405673;margin:9px 0 10px;overflow-wrap:anywhere}
        .metea-category-state{display:inline-flex;align-items:center;min-height:24px;padding:3px 9px;border-radius:999px;background:#eef5ff;color:#146cff;font-size:11px;line-height:1.35;font-weight:800}.metea-category-state--empty{background:#f1f4f8;color:#75839a}
        .metea-category-chevron{width:11px;height:11px;border-top:2px solid #17365f;border-right:2px solid #17365f;transform:rotate(45deg);transition:transform .16s ease}
        .metea-category-card:hover .metea-category-chevron{transform:translateX(3px) rotate(45deg);border-color:#146cff}
        .metea-summary-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:10px 0 20px}
        .metea-summary-strip>div{border:1px solid #dce5f2;border-radius:12px;background:#fff;padding:13px 15px}.metea-summary-strip span{display:block;color:#66758c;font-size:.76rem}.metea-summary-strip b{display:block;color:#0b2b55;font-size:1rem;margin-top:3px}
        .metea-section-title{display:flex;align-items:center;justify-content:space-between;margin:18px 0 10px}.metea-section-title h2{font-size:1.35rem!important;margin:0!important;color:#071a36}.metea-section-title span{color:#66758c;font-size:.82rem}
        .metea-data-card{border:1px solid #dce5f2;border-radius:14px;background:#fff;padding:17px 18px;margin:0 0 12px;box-shadow:0 6px 18px rgba(31,65,114,.045)}
        .metea-data-card__head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:13px}.metea-data-card__head strong{color:#0b2b55;font-size:1rem}.metea-edit-link{display:inline-flex;padding:6px 12px;border:1px solid #9fc2ff;border-radius:9px;color:#146cff;font-size:.82rem;font-weight:700;text-decoration:none;background:#fff}
        .metea-data-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.metea-data-field{padding:10px 12px;border-radius:10px;background:#f7f9fc;min-height:62px}.metea-data-field span{display:block;color:#75839a;font-size:.73rem;margin-bottom:3px}.metea-data-field b,.metea-data-field p{color:#102a4e;font-size:.88rem;margin:0;line-height:1.55;overflow-wrap:anywhere}
        .metea-notice{border:1px solid #b9d3ff;background:#f3f7ff;border-radius:12px;padding:12px 15px;color:#174b91;margin:10px 0 16px;font-size:.88rem}.metea-notice--error{border-color:#ffc5c9;background:#fff7f7;color:#c92d39}
        .metea-basic-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin:0 0 20px}.metea-basic-title{display:flex;align-items:flex-start;gap:14px}.metea-basic-title__icon{width:48px;height:48px;display:grid;place-items:center;flex:0 0 48px;margin-top:18px;border:1px solid #d8e7ff;border-radius:13px;background:linear-gradient(145deg,#f5f9ff,#e8f1ff)}.metea-basic-title__icon img{width:30px;height:30px}.metea-basic-title h1{margin:0 0 8px;color:#071a36;font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif!important;font-size:clamp(1.9rem,2.3vw,2.35rem);line-height:48px!important;letter-spacing:.015em;font-weight:700}.metea-basic-title p{margin:0;color:#52647d;font-size:14px;line-height:1.65}.metea-basic-updated{display:inline-flex;align-items:center;gap:6px;margin-top:5px;padding:6px 10px;border-radius:999px;background:#f5f8fc;color:#66758c;font-size:11px;white-space:nowrap}.metea-basic-updated::before{content:"";width:6px;height:6px;border-radius:50%;background:#8eb7f7}
        .metea-basic-overview{display:grid;grid-template-columns:minmax(0,1fr) 245px;gap:16px;margin-bottom:18px}.metea-basic-facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));margin-bottom:18px;border:1px solid #d7e2f0;border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 16px rgba(31,65,114,.035)}.metea-basic-fact{padding:17px 18px}.metea-basic-fact:first-child{background:#f7faff}.metea-basic-fact+.metea-basic-fact{border-left:1px solid #e5ebf3}.metea-basic-fact span{display:block;color:#75839a;font-size:11px;font-weight:700}.metea-basic-fact b{display:block;margin-top:6px;color:#0b2b55;font-size:15px;line-height:1.45;overflow-wrap:anywhere}.metea-basic-completion{display:flex;align-items:center;gap:13px;border:1px solid #bed6ff;border-radius:14px;background:linear-gradient(145deg,#f8fbff,#f0f6ff);padding:13px 15px;box-shadow:0 5px 16px rgba(20,108,255,.045)}.metea-basic-ring{--rate:100;width:70px;height:70px;flex:0 0 70px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#146cff calc(var(--rate)*1%),#e1e9f4 0);position:relative;box-shadow:0 0 0 4px rgba(20,108,255,.06)}.metea-basic-ring::before{content:"";position:absolute;inset:8px;border-radius:50%;background:#fff}.metea-basic-ring b{position:relative;color:#0759df;font-size:17px}.metea-basic-completion span{display:block;color:#17365f;font-size:12px;font-weight:800;white-space:nowrap}.metea-basic-completion small{display:block;margin-top:4px;color:#66758c;font-size:11px;line-height:1.5}
        .metea-basic-section-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:0 0 18px}.metea-basic-card{min-width:0;border:1px solid #d7e2f0;border-radius:14px;background:#fff;padding:18px 20px;box-shadow:0 7px 20px rgba(31,65,114,.045);transition:border-color .16s ease,box-shadow .16s ease,transform .16s ease}.metea-basic-card--wide{grid-column:1/-1}.metea-basic-card--wide .metea-basic-row{display:block}.metea-basic-card--wide .metea-basic-row span{margin-bottom:7px}.metea-basic-card--wide .metea-basic-row b{display:block;white-space:pre-wrap;font-weight:600;line-height:1.8}.metea-basic-card:hover{border-color:#bcd3f5;box-shadow:0 10px 24px rgba(31,65,114,.07);transform:translateY(-1px)}.metea-basic-card__head{display:flex;align-items:center;justify-content:space-between;gap:14px;padding-bottom:13px;margin-bottom:4px;border-bottom:1px solid #e8edf4}.metea-basic-card__title{display:flex;align-items:center;gap:10px;min-width:0}.metea-basic-card__title img{width:24px;height:24px;flex:0 0 24px}.metea-basic-card__title strong{color:#0b2b55;font-size:16px;overflow-wrap:anywhere}.metea-basic-edit{display:inline-flex;align-items:center;border:1px solid #a9c9ff;border-radius:8px;background:#fff;padding:6px 12px;color:#146cff!important;font-size:12px;font-weight:800;text-decoration:none!important;transition:background .16s ease,border-color .16s ease}.metea-basic-edit:hover{background:#eef5ff;border-color:#72a6ff;text-decoration:none!important}.metea-basic-row{display:grid;grid-template-columns:120px minmax(0,1fr);gap:12px;padding:12px 2px;border-bottom:1px solid #edf1f6}.metea-basic-row:last-child{border-bottom:0}.metea-basic-row span{color:#75839a;font-size:12px;font-weight:700}.metea-basic-row b{color:#102a4e;font-size:14px;line-height:1.5;font-weight:700;overflow-wrap:anywhere}.metea-basic-next{display:flex;align-items:center;justify-content:space-between;gap:18px;border:1px solid #bed6ff;border-radius:13px;background:linear-gradient(90deg,#f5f9ff,#eef5ff);padding:14px 17px;margin-top:3px}.metea-basic-next strong{display:block;color:#0b2b55;font-size:14px}.metea-basic-next span{display:block;margin-top:3px;color:#52647d;font-size:12px}.metea-basic-next a{display:inline-flex;align-items:center;min-height:35px;white-space:nowrap;border-radius:8px;background:#146cff;color:#fff!important;padding:0 15px;font-size:12px;font-weight:800;text-decoration:none!important;box-shadow:0 4px 10px rgba(20,108,255,.18);transition:background .16s ease,transform .16s ease}.metea-basic-next a:hover{background:#0759df;transform:translateY(-1px)}
        .metea-axis-list{grid-template-columns:1fr}.metea-axis-list .metea-basic-card{width:100%}
        .metea-career-list{display:grid;gap:18px;margin-bottom:18px}.metea-career-group{padding:15px;border:1px solid #c8d9ef;border-radius:16px;background:#f7faff;box-shadow:0 7px 20px rgba(31,65,114,.04)}.metea-career-group>.metea-basic-card{border-color:#9fc2f4;background:#fff;box-shadow:0 5px 15px rgba(20,108,255,.055)}.metea-career-children{position:relative;display:grid;grid-template-columns:minmax(0,1fr);gap:13px;margin:13px 0 0 30px;padding-left:18px}.metea-career-children::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;border-radius:3px;background:#b9d3ff}.metea-career-children::after{content:"部署・役割";position:absolute;left:-7px;top:16px;transform:translateX(-100%);color:#66758c;font-size:10px;font-weight:800;writing-mode:vertical-rl;letter-spacing:.08em}.metea-career-children .metea-basic-card{width:100%;background:#fff}.metea-career-empty{margin:13px 0 0 30px;padding:12px 16px;border-left:3px solid #b9d3ff;color:#66758c;font-size:12px}
        .metea-career-import{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:0 0 18px;padding:15px 17px;border:1px solid #b9d3ff;border-radius:13px;background:#f5f9ff}.metea-career-import__text{display:flex;align-items:center;gap:12px}.metea-career-import__icon{display:grid;place-items:center;width:38px;height:38px;flex:0 0 38px;border-radius:10px;background:#e7f1ff;color:#146cff;font-size:21px;font-weight:800}.metea-career-import strong{display:block;color:#0b2b55;font-size:14px}.metea-career-import span{display:block;margin-top:3px;color:#52647d;font-size:12px;line-height:1.5}.metea-career-import a{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:0 15px;border:1px solid #146cff;border-radius:8px;background:#fff;color:#146cff!important;font-size:12px;font-weight:800;text-decoration:none!important;white-space:nowrap}.metea-career-import a:hover{background:#eaf3ff;text-decoration:none!important}
        .metea-value-scale{padding:13px 2px 2px}.metea-value-scale__ends{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;margin-bottom:12px}.metea-value-scale__end{min-width:0;padding:9px 10px;border:1px solid #dce5f2;border-radius:9px;background:#f8fafc;color:#52647d;font-size:11px;line-height:1.5;font-weight:700;overflow-wrap:anywhere}.metea-value-scale__end:last-child{text-align:right}.metea-value-scale__end.is-near{border-color:#9fc2ff;background:#eef5ff;color:#0759df}.metea-value-scale__track{position:relative;display:grid;grid-template-columns:repeat(5,1fr);align-items:center;margin:0 17px}.metea-value-scale__track::before{content:"";position:absolute;left:10%;right:10%;top:50%;height:3px;border-radius:3px;background:#dce6f3;transform:translateY(-50%)}.metea-value-scale__point{position:relative;z-index:1;display:grid;place-items:center;width:27px;height:27px;margin:auto;border:2px solid #c8d7e9;border-radius:50%;background:#fff;color:#75839a;font-size:10px;font-weight:800}.metea-value-scale__point.is-selected{width:31px;height:31px;border-color:#146cff;background:#146cff;color:#fff;box-shadow:0 0 0 5px #e9f2ff}.metea-value-scale__result{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:13px;padding:9px 11px;border-radius:9px;background:#f4f7fb;color:#52647d;font-size:11px}.metea-value-scale__result b{color:#0759df;font-size:12px}
        .metea-basic-release-grid{display:grid;grid-template-columns:minmax(0,1fr) 238px;gap:18px;align-items:start}.metea-basic-release-main .metea-basic-facts{margin-bottom:18px}.metea-basic-sidebar{display:grid;gap:12px}.metea-basic-sidebar-card{border:1px solid #d7e2f0;border-radius:14px;background:#fff;padding:16px;box-shadow:0 7px 20px rgba(31,65,114,.045)}.metea-basic-sidebar .metea-basic-completion{display:block;border:0;border-radius:0;background:transparent;padding:1px 0 15px;box-shadow:none;text-align:center}.metea-basic-sidebar .metea-basic-ring{margin:0 auto 11px}.metea-basic-sidebar .metea-basic-completion span{font-size:13px}.metea-basic-status-list{display:grid;gap:9px;padding:14px 1px;border-top:1px solid #e6edf6}.metea-basic-status{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;font-size:11px}.metea-basic-status span{color:#405673;font-weight:700}.metea-basic-status b{display:inline-flex;align-items:center;gap:5px;color:#146cff;font-size:10px;white-space:nowrap}.metea-basic-status b::before{content:"✓";display:grid;place-items:center;width:15px;height:15px;border-radius:50%;background:#eaf3ff;color:#146cff;font-size:9px}.metea-basic-status.is-empty b{color:#e77618}.metea-basic-status.is-empty b::before{content:"!";background:#fff2e8;color:#e77618}.metea-basic-recommend{margin-top:1px;padding:13px;border:1px solid #bed6ff;border-radius:11px;background:linear-gradient(145deg,#f7fbff,#edf5ff)}.metea-basic-recommend__label{display:flex;align-items:center;gap:7px;color:#146cff;font-size:11px;font-weight:800}.metea-basic-recommend__label::before{content:"✦";display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:#e2efff}.metea-basic-recommend p{margin:9px 0 13px;color:#405673;font-size:11px;line-height:1.65}.metea-basic-side-action,.metea-basic-compare{display:flex;align-items:center;justify-content:center;min-height:37px;border-radius:8px;font-size:11px;font-weight:800;text-decoration:none!important}.metea-basic-side-action{border:1px solid #8db8ff;background:#fff;color:#146cff!important}.metea-basic-side-action:hover{background:#eef5ff}.metea-basic-compare{border:1px solid #146cff;background:#146cff;color:#fff!important;box-shadow:0 5px 13px rgba(20,108,255,.17)}.metea-basic-compare:hover{background:#0759df;color:#fff!important}
        .metea-basic-inline-edit{margin:0 0 18px;padding:18px 20px 8px;border:1px solid #9fc2ff;border-radius:14px;background:linear-gradient(145deg,#f8fbff,#f1f6ff);box-shadow:0 10px 26px rgba(20,108,255,.08)}.metea-basic-inline-edit h3{margin:0 0 4px;color:#071a36;font-size:17px}.metea-basic-inline-edit p{margin:0 0 12px;color:#52647d;font-size:12px}
        .metea-empty{border:1px dashed #b9cae1;border-radius:14px;background:#f9fbfe;padding:28px;text-align:center;color:#66758c}.metea-empty a{color:#146cff!important;font-weight:700;text-decoration:none!important}
        div[data-testid="stForm"]{border:1px solid #b9d3ff!important;border-radius:14px!important;background:#f8fbff!important;padding:16px!important;margin-bottom:12px}
        [data-testid="stDialog"] form [data-testid="stHorizontalBlock"]:last-child > div:first-child button{background:#146cff!important;border-color:#146cff!important;color:#fff!important;box-shadow:0 5px 13px rgba(20,108,255,.18)!important}[data-testid="stDialog"] form [data-testid="stHorizontalBlock"]:last-child > div:first-child button:hover{background:#0759df!important;border-color:#0759df!important;color:#fff!important}
        @media(max-width:1320px){.metea-category-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
        @media(max-width:1100px){.metea-review-nav{display:none}.metea-category-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.metea-summary-strip{grid-template-columns:repeat(2,1fr)}.metea-data-grid{grid-template-columns:repeat(2,1fr)}.metea-basic-overview,.metea-basic-release-grid{grid-template-columns:1fr}.metea-basic-section-grid,.metea-career-children{grid-template-columns:1fr}.metea-basic-sidebar{grid-template-columns:repeat(2,minmax(0,1fr))}.metea-basic-compare{grid-column:1/-1}}
        @media(max-width:640px){.metea-category-grid,.metea-summary-strip,.metea-data-grid,.metea-basic-facts,.metea-basic-sidebar{grid-template-columns:1fr}.metea-review-head,.metea-basic-head{display:block}.metea-basic-updated{margin-top:10px}.metea-basic-fact+.metea-basic-fact{border-left:0;border-top:1px solid #e5ebf3}.metea-basic-row{grid-template-columns:1fr;gap:4px}.metea-basic-next,.metea-career-import{align-items:flex-start;flex-direction:column}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _review_navigation(active: str) -> None:
    # 全画面共通ナビゲーションへ統合済み。カテゴリ選択は本文カードで行う。
    return None


def _asset_data_uri(filename: str) -> str:
    """assets内のSVGをHTMLカードで安全に表示する。"""
    data = (ASSETS_DIR / filename).read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _notice(message: str, error: bool = False) -> None:
    st.markdown(f'<div class="metea-notice{" metea-notice--error" if error else ""}">{escape(message)}</div>', unsafe_allow_html=True)


def _edit_key(category: str, card: str) -> str:
    return f"profile_review_edit_{category}_{card}"


def _edit_button(category: str, card: str) -> None:
    if st.button("編集", key=f"edit_{category}_{card}", type="tertiary"):
        st.session_state[_edit_key(category, card)] = True
        st.rerun()


def _finish_edit(category: str, card: str) -> None:
    st.session_state[_edit_key(category, card)] = False


@st.dialog("プロフィール情報を編集", width="large")
def _basic_profile_dialog(info: object) -> None:
    """氏名・性別・生年月日だけを編集する。"""
    st.caption("プロフィール情報を修正してください。居住地・最寄駅の情報は変更されません。")
    with st.form("review_basic_profile_form"):
        c1, c2 = st.columns(2)
        family = c1.text_input("姓 *", info.family_name)
        given = c2.text_input("名 *", info.given_name)
        gender_options = [key for key in GENDER_LABELS if key is not None]
        gender = st.selectbox(
            "性別 *",
            gender_options,
            index=gender_options.index(info.gender) if info.gender in gender_options else 0,
            format_func=lambda value: GENDER_LABELS.get(value, value),
        )
        b1, b2, b3 = st.columns(3)
        birth_year = b1.number_input("生年 *", 1900, date.today().year - 1, info.birth_date.year)
        birth_month = b2.number_input("月 *", 1, 12, info.birth_date.month)
        birth_day = b3.number_input("日 *", 1, 31, info.birth_date.day)
        save_col, cancel_col = st.columns(2)
        submitted = save_col.form_submit_button("変更を保存", type="primary", use_container_width=True)
        cancelled = cancel_col.form_submit_button("キャンセル", use_container_width=True)

    if cancelled:
        _finish_edit("basic", "profile")
        st.rerun()
    if submitted:
        new, errors = validate_basic_info(
            family,
            given,
            gender,
            int(birth_year),
            int(birth_month),
            int(birth_day),
            info.prefecture,
            info.municipality,
            info.nearest_station,
            info.nearest_station_place_id,
        )
        if errors:
            _notice("入力内容を確認してください：" + "／".join(errors.values()), True)
        elif new:
            save_basic_info(new)
            _finish_edit("basic", "profile")
            st.session_state["profile_review_notice"] = "基本情報を更新しました。"
            st.rerun()


@st.dialog("居住地・最寄駅を編集", width="large")
def _basic_location_dialog(info: object) -> None:
    """居住地と最寄駅だけを編集する。"""
    st.caption("居住地と最寄駅を修正してください。プロフィール情報は変更されません。")
    with st.form("review_basic_location_form"):
        c1, c2 = st.columns(2)
        prefecture = c1.text_input("都道府県 *", info.prefecture)
        municipality = c2.text_input("市区町村 *", info.municipality)
        station = st.text_input("最寄駅 *", info.nearest_station)
        save_col, cancel_col = st.columns(2)
        submitted = save_col.form_submit_button("変更を保存", type="primary", use_container_width=True)
        cancelled = cancel_col.form_submit_button("キャンセル", use_container_width=True)

    if cancelled:
        _finish_edit("basic", "location")
        st.rerun()
    if submitted:
        new, errors = validate_basic_info(
            info.family_name,
            info.given_name,
            info.gender,
            info.birth_date.year,
            info.birth_date.month,
            info.birth_date.day,
            prefecture,
            municipality,
            station,
            info.nearest_station_place_id,
        )
        if errors:
            _notice("入力内容を確認してください：" + "／".join(errors.values()), True)
        elif new:
            save_basic_info(new)
            _finish_edit("basic", "location")
            st.session_state["profile_review_notice"] = "居住地・最寄駅を更新しました。"
            st.rerun()


def _field(label: str, value: object) -> str:
    text = "未登録" if value is None or value == "" else str(value)
    return f'<div class="metea-data-field"><span>{escape(label)}</span><b>{escape(text)}</b></div>'


def _card(title: str, fields: list[tuple[str, object]]) -> None:
    st.markdown(f'<div class="metea-data-card"><div class="metea-data-card__head"><strong>{escape(title)}</strong></div><div class="metea-data-grid">{"".join(_field(k,v) for k,v in fields)}</div></div>', unsafe_allow_html=True)


def _status_counts() -> dict[str, tuple[bool, str]]:
    basic = load_basic_info()
    hope, hope_items = load_hope_conditions_data()
    rankings, details, styles = load_work_values_data()
    axes = load_job_hunting_axis_data()
    careers = load_career_data()
    return {
        "basic": (basic is not None, "登録済み" if basic else "未登録"),
        "hope": (hope is not None and bool(hope_items), f"{len(hope_items)}件の条件" if hope else "未登録"),
        "values": (bool(rankings or details or styles), f"{len(rankings)+len(details)+len(styles)}件の回答" if rankings or details or styles else "未登録"),
        "axis": (bool(axes), f"{len(axes)}件の軸" if axes else "未登録"),
        "career": (bool(careers), f"{len(careers)}社" if careers else "未登録"),
    }


def _render_category_selector() -> None:
    statuses = _status_counts()
    st.markdown('<a class="metea-review-back" href="?page=self_discovery">← 自分を知るへ戻る</a><div class="metea-review-head"><div><h1>登録内容を確認する</h1><p>これまでに登録した内容を、カテゴリごとに振り返れます。見直したい項目を選んでください。</p></div></div>', unsafe_allow_html=True)
    cards = []
    for key, title, subtitle, description, icon in CATEGORIES:
        registered, state = statuses[key]
        icon_uri = _asset_data_uri(icon)
        cards.append(f'<a class="metea-category-card" href="?page=profile_review&amp;category={key}"><span class="metea-category-icon"><img src="{icon_uri}" alt=""></span><span class="metea-category-body"><strong>{escape(title)}</strong><small>{escape(subtitle)}</small><p>{escape(description)}</p><span class="metea-category-state{"" if registered else " metea-category-state--empty"}">{"✓ " if registered else ""}{escape(state)}</span></span><span class="metea-category-chevron" aria-hidden="true"></span></a>')
    st.markdown(f'<div class="metea-category-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def _dashboard_header(category: str, title: str, description: str, counts: list[tuple[str, object]]) -> None:
    icon_name = next(icon for key, _, _, _, icon in CATEGORIES if key == category)
    icon_uri = _asset_data_uri(icon_name)
    st.markdown(
        f'<a class="metea-review-back" href="?page=profile_review">← 登録内容の一覧へ戻る</a>'
        f'<div class="metea-basic-head"><div class="metea-basic-title">'
        f'<span class="metea-basic-title__icon"><img src="{icon_uri}" alt=""></span>'
        f'<div><h1>{escape(title)}の確認</h1><p>{escape(description)}</p></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _consume_edit_query(category: str) -> str | None:
    requested = st.query_params.get("edit")
    if requested:
        prefix = f"profile_review_edit_{category}_"
        for key in list(st.session_state):
            if key.startswith(prefix):
                st.session_state[key] = False
        st.session_state[_edit_key(category, requested)] = True
        st.query_params.pop("edit", None)
        st.rerun()
    prefix = f"profile_review_edit_{category}_"
    return next((key.removeprefix(prefix) for key, value in st.session_state.items() if key.startswith(prefix) and value), None)


def _review_card_html(category: str, edit_key: str, title: str, rows: list[tuple[str, object]], *, wide: bool = False) -> str:
    icon_name = next(icon for key, _, _, _, icon in CATEGORIES if key == category)
    icon_uri = _asset_data_uri(icon_name)
    body = "".join(
        f'<div class="metea-basic-row"><span>{escape(label)}</span><b>{escape("未登録" if value in (None, "") else str(value))}</b></div>'
        for label, value in rows
    )
    url = f'?page=profile_review&amp;category={category}&amp;edit={edit_key}'
    return (
        f'<section class="metea-basic-card{" metea-basic-card--wide" if wide else ""}">'
        '<div class="metea-basic-card__head">'
        f'<div class="metea-basic-card__title"><img src="{icon_uri}" alt=""><strong>{escape(title)}</strong></div>'
        f'<a class="metea-basic-edit" target="_self" href="{url}">編集する</a>'
        f'</div>{body}</section>'
    )


def _work_style_review_card_html(edit_key: str, answer: WorkStyleAnswer, question: dict[str, str]) -> str:
    """左右の考え方と選択位置が一目で分かる価値観スケールを表示する。"""
    icon_uri = _asset_data_uri("review-values.svg")
    url = f'?page=profile_review&amp;category=values&amp;edit={edit_key}'
    score = answer.answer_score
    left_near = score < 3
    right_near = score > 3
    points = "".join(
        f'<span class="metea-value-scale__point{" is-selected" if value == score else ""}">{value}</span>'
        for value in range(1, 6)
    )
    return (
        '<section class="metea-basic-card metea-work-style-review">'
        '<div class="metea-basic-card__head">'
        f'<div class="metea-basic-card__title"><img src="{icon_uri}" alt=""><strong>{escape(question["title"])}</strong></div>'
        f'<a class="metea-basic-edit" target="_self" href="{url}">編集する</a></div>'
        '<div class="metea-value-scale">'
        '<div class="metea-value-scale__ends">'
        f'<div class="metea-value-scale__end{" is-near" if left_near else ""}">1に近い考え方<br>{escape(question["left_text"])}</div>'
        f'<div class="metea-value-scale__end{" is-near" if right_near else ""}">5に近い考え方<br>{escape(question["right_text"])}</div>'
        f'</div><div class="metea-value-scale__track">{points}</div>'
        f'<div class="metea-value-scale__result"><span>現在の回答</span><b>{score}　{escape(WORK_STYLE_SCORE_LABELS[score])}</b></div>'
        '</div></section>'
    )


def _review_facts_html(facts: list[tuple[str, object]]) -> str:
    return '<div class="metea-basic-facts">' + "".join(
        f'<div class="metea-basic-fact"><span>{escape(label)}</span><b>{escape(str(value))}</b></div>'
        for label, value in facts
    ) + '</div>'


def _progress_count(completed: int, total: int) -> str:
    """確認画面の集計を「回答済み／全項目」で統一する。"""
    return f"{completed}件 / {total}件"


def _review_sidebar(category: str, completion: int) -> None:
    statuses = _status_counts()
    labels = {"basic": "基本情報", "hope": "希望条件", "values": "価値観", "axis": "就活の軸", "career": "職務経歴・スキル"}
    rows = "".join(
        f'<div class="metea-basic-status{"" if registered else " is-empty"}"><span>{escape(labels[key])}</span><b>{"登録済み" if registered else "未登録"}</b></div>'
        for key, (registered, _) in statuses.items()
    )
    priority = ("basic", "axis", "hope", "career", "values")
    next_key = next((key for key in priority if not statuses[key][0]), None)
    links = {
        "basic": ("基本情報を充実させる", "?page=basic_info"),
        "axis": ("就活の軸を充実させる", "?page=job_hunting_axis"),
        "hope": ("希望条件を充実させる", "?page=hope_conditions"),
        "career": ("職務経歴を充実させる", "?page=career"),
        "values": ("価値観を整理する", "?page=work_values"),
    }
    recommend_html = ""
    if next_key:
        action, url = links[next_key]
        message = f'{labels[next_key]}を充実させると、AIがあなたと求人の相性をより具体的に判断できます。'
        recommend_html = (
            f'<div class="metea-basic-recommend"><div class="metea-basic-recommend__label">おすすめのアクション</div><p>{escape(message)}</p>'
            f'<a class="metea-basic-side-action" href="{url}">{escape(action)}</a></div>'
        )
    st.markdown(
        f'<aside class="metea-basic-sidebar"><div class="metea-basic-sidebar-card metea-basic-sidebar-shell">'
        f'<div class="metea-basic-completion"><div class="metea-basic-ring" style="--rate:{completion}"><b>{completion}%</b></div>'
        f'<div><span>{escape(labels[category])}の完成度</span><small>{"必要な情報がそろっています" if completion == 100 else "未入力の項目があります"}</small></div></div>'
        f'<div class="metea-basic-status-list">{rows}</div>{recommend_html}</div>'
        f'<a class="metea-basic-compare" href="?page=job_list">求人比較を始める →</a></aside>',
        unsafe_allow_html=True,
    )


def _render_basic() -> None:
    info = load_basic_info()
    requested_edit = st.query_params.get("edit")
    if requested_edit in {"profile", "location"}:
        st.session_state[_edit_key("basic", "profile")] = False
        st.session_state[_edit_key("basic", "location")] = False
        st.session_state[_edit_key("basic", requested_edit)] = True
        st.query_params.pop("edit", None)
        st.rerun()

    updated_at = load_basic_info_updated_at()
    updated_label = "未登録"
    if updated_at:
        try:
            updated_label = datetime.fromisoformat(updated_at).strftime("%Y/%m/%d %H:%M")
        except ValueError:
            updated_label = updated_at

    icon_uri = _asset_data_uri("review-basic.svg")
    required_values = [] if not info else [
        info.family_name,
        info.given_name,
        info.gender,
        info.birth_date,
        info.prefecture,
        info.municipality,
        info.nearest_station,
        info.nearest_station_place_id,
    ]
    completion = 0 if not info else round(sum(bool(value) for value in required_values) / len(required_values) * 100)
    name = f"{info.family_name} {info.given_name}" if info else "未登録"
    profile_values = [name != "未登録", info.gender, info.birth_date] if info else []
    location_values = [info.prefecture, info.municipality, info.nearest_station] if info else []
    profile_done = sum(bool(value) for value in profile_values)
    location_done = sum(bool(value) for value in location_values)
    facts_html = _review_facts_html([
        ("登録情報 全体", _progress_count(profile_done + location_done, 6)),
        ("プロフィール情報", _progress_count(profile_done, 3)),
        ("居住地・最寄駅", _progress_count(location_done, 3)),
    ])
    completion_html = f'''
      <div class="metea-basic-completion">
        <div class="metea-basic-ring" style="--rate:{completion}"><b>{completion}%</b></div>
        <div><span>基本情報の完成度</span><small>{"必要な情報がそろっています" if completion == 100 else "未入力の項目があります"}</small></div>
      </div>
    '''

    st.markdown(
        f'''
        <a class="metea-review-back" href="?page=profile_review">← 登録内容の一覧へ戻る</a>
        <div class="metea-basic-head">
          <div class="metea-basic-title">
            <span class="metea-basic-title__icon"><img src="{icon_uri}" alt=""></span>
            <div><h1>基本情報の確認</h1><p>登録しているプロフィールと居住地の情報を確認できます。</p></div>
          </div>
          <div class="metea-basic-updated">最終更新：{escape(updated_label)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    if not info:
        st.markdown('<div class="metea-empty">基本情報はまだ登録されていません。<br><a href="?page=basic_info">基本情報を入力する</a></div>', unsafe_allow_html=True); return
    if info:
        gender_label = GENDER_LABELS.get(info.gender, info.gender)
        statuses = _status_counts()
        status_labels = {
            "basic": "基本情報",
            "hope": "希望条件",
            "values": "価値観",
            "axis": "就活の軸",
            "career": "職務経歴・スキル",
        }
        status_rows = "".join(
            f'<div class="metea-basic-status{"" if registered else " is-empty"}"><span>{escape(status_labels[key])}</span><b>{"登録済み" if registered else "未登録"}</b></div>'
            for key, (registered, _) in statuses.items()
        )
        # AI評価への寄与が大きい情報を優先して案内する。
        ai_priority = ("basic", "axis", "hope", "career", "values")
        next_incomplete = next((key for key in ai_priority if not statuses[key][0]), None)
        next_links = {
            "basic": ("基本情報を充実させる", "?page=basic_info"),
            "hope": ("希望条件を充実させる", "?page=hope_conditions"),
            "values": ("価値観を整理する", "?page=work_values"),
            "axis": ("就活の軸を充実させる", "?page=job_hunting_axis"),
            "career": ("職務経歴を充実させる", "?page=career"),
        }
        recommend_html = ""
        if next_incomplete:
            recommend_label, recommend_url = next_links[next_incomplete]
            recommend_text = f'{status_labels[next_incomplete]}を充実させると、AIがあなたと求人の相性をより具体的に判断できます。'
            recommend_html = dedent(f'''
              <div class="metea-basic-recommend">
                <div class="metea-basic-recommend__label">おすすめのアクション</div>
                <p>{escape(recommend_text)}</p>
                <a class="metea-basic-side-action" href="{recommend_url}">{escape(recommend_label)}</a>
              </div>
            ''')

        def row(label: str, value: object) -> str:
            return f'<div class="metea-basic-row"><span>{escape(label)}</span><b>{escape(str(value))}</b></div>'

        profile_edit_url = "?page=profile_review&amp;category=basic&amp;edit=profile"
        location_edit_url = "?page=profile_review&amp;category=basic&amp;edit=location"
        st.markdown(
            dedent(f'''
            <div class="metea-basic-release-grid">
              <div class="metea-basic-release-main">
                {facts_html}
                <div class="metea-basic-section-grid">
                  <section class="metea-basic-card">
                <div class="metea-basic-card__head">
                  <div class="metea-basic-card__title"><img src="{icon_uri}" alt=""><strong>プロフィール情報</strong></div>
                  <a class="metea-basic-edit" target="_self" href="{profile_edit_url}">編集する</a>
                </div>
                {row("氏名", name)}
                {row("性別", gender_label)}
                {row("生年月日", info.birth_date.strftime("%Y年%m月%d日"))}
                  </section>
                  <section class="metea-basic-card">
                <div class="metea-basic-card__head">
                  <div class="metea-basic-card__title"><img src="{icon_uri}" alt=""><strong>居住地・最寄駅</strong></div>
                  <a class="metea-basic-edit" target="_self" href="{location_edit_url}">編集する</a>
                </div>
                {row("都道府県", info.prefecture)}
                {row("市区町村", info.municipality)}
                {row("現在の最寄駅", info.nearest_station)}
                  </section>
                </div>
                <div class="metea-basic-next">
                  <div><strong>次は希望条件を確認できます</strong><span>働き方や勤務地など、登録した希望条件を振り返ってみましょう。</span></div>
                  <a href="?page=profile_review&amp;category=hope">希望条件を確認する →</a>
                </div>
              </div>
              <aside class="metea-basic-sidebar">
                <div class="metea-basic-sidebar-card metea-basic-sidebar-shell">
                  {completion_html}
                  <div class="metea-basic-status-list">{status_rows}</div>
                  {recommend_html}
                </div>
                <a class="metea-basic-compare" href="?page=job_list">求人比較を始める →</a>
              </aside>
            </div>
            ''').replace("\n", ""),
            unsafe_allow_html=True,
        )
        if st.session_state.get(_edit_key("basic", "profile")):
            _basic_profile_dialog(info)
        elif st.session_state.get(_edit_key("basic", "location")):
            _basic_location_dialog(info)


@st.dialog("希望条件を編集", width="large")
def _hope_dialog(edit_key: str, condition: object, items: list[HopeConditionItem]) -> None:
    if edit_key == "base":
        with st.form("review_hope_base_dialog"):
            c1,c2,c3=st.columns(3); minimum=c1.number_input("最低許容年収（万円）",0,value=condition.minimum_salary);desired=c2.number_input("希望年収（万円）",0,value=condition.desired_salary);ideal=c3.number_input("理想年収（万円）",0,value=condition.ideal_salary)
            c1,c2,c3=st.columns(3);commute=c1.number_input("片道通勤時間上限（分）",0,value=condition.commute_minutes);overtime=c2.number_input("月間残業時間上限",0,value=condition.overtime_limit);holidays=c3.number_input("年間休日",0,value=condition.annual_holidays)
            other=st.text_area("その他の希望条件",condition.other_conditions);a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
        if cancel:_finish_edit("hope",edit_key);st.rerun()
        if submit:save_hope_conditions_data(replace(condition,minimum_salary=int(minimum),desired_salary=int(desired),ideal_salary=int(ideal),commute_minutes=int(commute),overtime_limit=int(overtime),annual_holidays=int(holidays),other_conditions=other.strip()),items);_finish_edit("hope",edit_key);st.session_state["profile_review_notice"]="希望条件を更新しました。";st.rerun()
        return
    index=int(edit_key.split("_")[1]);item=items[index]
    with st.form(f"hope_item_dialog_{index}"):
        priority_keys=list(PRIORITY_OPTIONS);value=st.text_input("希望内容",item.condition_value);priority=st.selectbox("優先度",priority_keys,index=priority_keys.index(item.priority) if item.priority in priority_keys else 1,format_func=lambda key: PRIORITY_OPTIONS[key]);detail=st.text_input("補足",item.detail_value or "");a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
    if cancel:_finish_edit("hope",edit_key);st.rerun()
    if submit:
        updated=list(items);updated[index]=replace(item,condition_value=value.strip(),priority=priority,detail_value=detail.strip() or None);save_hope_conditions_data(condition,updated);_finish_edit("hope",edit_key);st.session_state["profile_review_notice"]="希望条件を更新しました。";st.rerun()


@st.dialog("価値観を編集", width="large")
def _values_dialog(edit_key: str, rankings: list[WorkValueRanking], details: list[WorkValueDetail], answers: list[WorkStyleAnswer]) -> None:
    kind,index_text=edit_key.split("_");index=int(index_text)
    if kind=="ranking":
        item=rankings[index]
        with st.form(f"value_rank_dialog_{index}"):
            value=st.text_input("内容",item.selected_value);rank=st.number_input("順位",1,10,item.priority_rank);custom=st.text_input("補足",item.custom_value or "");a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
        new=list(rankings)
        if submit:new[index]=replace(item,selected_value=value.strip(),priority_rank=int(rank),custom_value=custom.strip() or None);errors=save_work_values_data(new,details,answers)
    elif kind=="detail":
        item=details[index]
        with st.form(f"value_detail_dialog_{index}"):
            text=st.text_area("回答内容",item.detail_text,height=220);a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
        new=list(details)
        if submit:new[index]=replace(item,detail_text=text.strip());errors=save_work_values_data(rankings,new,answers)
    else:
        item=answers[index]
        with st.form(f"value_style_dialog_{index}"):
            score=st.radio("自分に近い度合い",[1,2,3,4,5],index=item.answer_score-1,horizontal=True);a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
        new=list(answers)
        if submit:new[index]=replace(item,answer_score=score);errors=save_work_values_data(rankings,details,new)
    if cancel:_finish_edit("values",edit_key);st.rerun()
    if submit:
        if errors:_notice("／".join(errors),True)
        else:_finish_edit("values",edit_key);st.session_state["profile_review_notice"]="価値観を更新しました。";st.rerun()


@st.dialog("就活の軸を編集", width="large")
def _axis_dialog(edit_key: str, axes: list[JobHuntingAxis]) -> None:
    index=int(edit_key.split("_")[1]);item=axes[index]
    with st.form(f"axis_dialog_{index}"):
        title=st.text_input("軸の名称",item.axis_title);description=st.text_area("具体的な判断基準",item.axis_description,height=180);rank=st.number_input("順位",1,len(axes),item.priority_rank);a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
    if cancel:_finish_edit("axis",edit_key);st.rerun()
    if submit:
        new=list(axes);new[index]=replace(item,axis_title=title.strip(),axis_description=description.strip(),priority_rank=int(rank));new=sorted(new,key=lambda x:x.priority_rank);new=[replace(x,priority_rank=i+1) for i,x in enumerate(new)];errors=save_job_hunting_axis_data(new)
        if errors:_notice("／".join(errors),True)
        else:_finish_edit("axis",edit_key);st.session_state["profile_review_notice"]="就活の軸を更新しました。";st.rerun()


@st.dialog("職務経歴・スキルを編集", width="large")
def _career_dialog(edit_key: str, careers: list[tuple[Career,list[CareerHistory]]]) -> None:
    parts=edit_key.split("_");ci=int(parts[1]);career,histories=careers[ci]
    if parts[0]=="company":
        with st.form(f"career_company_dialog_{ci}"):
            name=st.text_input("会社名 *",career.company_name);employment=st.text_input("雇用形態",career.employment_type);industry=st.text_input("業種 *",career.industry);current=st.checkbox("在職中",career.is_current);a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
        if submit:updated=list(careers);updated[ci]=(replace(career,company_name=name.strip(),employment_type=employment.strip(),industry=industry.strip(),is_current=current),histories);errors=save_career_data(updated)
    else:
        hi=int(parts[2]);history=histories[hi]
        with st.form(f"career_history_dialog_{ci}_{hi}"):
            c1,c2,c3=st.columns(3);department=c1.text_input("部署",history.department);position=c2.text_input("役職",history.position);occupation=c3.text_input("職種 *",history.occupation);job=st.text_area("業務内容",history.job_description);achievement=st.text_area("実績・成果",history.achievements);a,b=st.columns(2);submit=a.form_submit_button("変更を保存",type="primary",use_container_width=True);cancel=b.form_submit_button("キャンセル",use_container_width=True)
        if submit:new_hist=list(histories);new_hist[hi]=replace(history,department=department.strip(),position=position.strip(),occupation=occupation.strip(),job_description=job.strip(),achievements=achievement.strip());updated=list(careers);updated[ci]=(career,new_hist);errors=save_career_data(updated)
    if cancel:_finish_edit("career",edit_key);st.rerun()
    if submit:
        if errors:_notice("／".join(errors),True)
        else:_finish_edit("career",edit_key);st.session_state["profile_review_notice"]="職務経歴・スキルを更新しました。";st.rerun()


def _render_hope() -> None:
    condition,items=load_hope_conditions_data();active=_consume_edit_query("hope");_dashboard_header("hope","希望条件","求人比較やAIマッチングに利用する希望条件を確認できます。",[])
    if not condition:st.markdown('<div class="metea-empty">希望条件はまだ登録されていません。<br><a href="?page=hope_conditions">希望条件を入力する</a></div>',unsafe_allow_html=True);return
    labels={"industry":"希望業種","occupation":"希望職種","location":"希望勤務地","employment_type":"雇用形態","holiday":"希望休日","age_group":"職場の年齢層","time_system":"勤務制度","workstyle":"働き方・風土","career_condition":"キャリア・組織風土"}
    cards=[_review_card_html("hope","base","年収・勤務条件",[("最低許容年収",f"{condition.minimum_salary}万円"),("希望年収",f"{condition.desired_salary}万円"),("理想年収",f"{condition.ideal_salary}万円"),("通勤時間上限",f"{condition.commute_minutes}分"),("残業時間上限",f"{condition.overtime_limit}時間"),("年間休日",f"{condition.annual_holidays}日")])]
    cards += [_review_card_html("hope",f"item_{i}",labels.get(item.condition_type,item.condition_type),[("希望内容",item.condition_value),("優先度",PRIORITY_OPTIONS.get(item.priority,item.priority)),("補足",item.detail_value or "―")]) for i,item in enumerate(items)]
    def item_summary(condition_type: str, empty: str = "未登録") -> str:
        values = [item.condition_value for item in items if item.condition_type == condition_type]
        return "・".join(values[:3]) if values else empty

    base_values = [condition.minimum_salary, condition.desired_salary, condition.ideal_salary, condition.commute_minutes, condition.overtime_limit, condition.annual_holidays]
    base_done = sum(value is not None for value in base_values)
    item_done = sum(bool(item.condition_value) for item in items)
    priority_done = sum(bool(item.priority) for item in items)
    total_questions = len(base_values) + len(items) * 2
    total_done = base_done + item_done + priority_done

    main,side=st.columns([3.2,1],gap="medium")
    with main:
        st.markdown(_review_facts_html([("回答状況 全体",_progress_count(total_done,total_questions)),("年収・勤務条件",_progress_count(base_done,len(base_values))),("希望条件",_progress_count(item_done,len(items))),("優先度",_progress_count(priority_done,len(items)))]),unsafe_allow_html=True);st.markdown(f'<div class="metea-basic-section-grid">{"".join(cards)}</div>',unsafe_allow_html=True);st.markdown('<div class="metea-basic-next"><div><strong>次は価値観を確認できます</strong><span>大切にしたいことや仕事の進め方を振り返ってみましょう。</span></div><a href="?page=profile_review&amp;category=values">価値観を確認する →</a></div>',unsafe_allow_html=True)
    with side:_review_sidebar("hope",100 if items else 50)
    if active:_hope_dialog(active,condition,items)


def _render_values() -> None:
    rankings,details,answers=load_work_values_data();active=_consume_edit_query("values");_dashboard_header("values","価値観","大切にしたいこと・経験・仕事の進め方を確認できます。",[])
    if not (rankings or details or answers):st.markdown('<div class="metea-empty">価値観はまだ登録されていません。<br><a href="?page=work_values">価値観を入力する</a></div>',unsafe_allow_html=True);return
    work_style_questions = {question["question_type"]: question for question in WORK_STYLE_QUESTIONS}
    cards=[_review_card_html("values",f"ranking_{i}",f"{item.priority_rank}位　{item.selected_value}",[(RANKING_QUESTION_LABELS.get(item.question_type,"大切にしたいこと"),item.selected_value),("補足",item.custom_value or "―")]) for i,item in enumerate(rankings)]
    cards += [_review_card_html("values",f"detail_{i}",DETAIL_LABELS.get(item.detail_type,"経験・理由"),[("回答内容",item.detail_text)],wide=True) for i,item in enumerate(details)]
    cards += [_work_style_review_card_html(f"style_{i}",item,work_style_questions[item.question_type]) for i,item in enumerate(answers) if item.question_type in work_style_questions]
    completion=round(sum((bool(rankings),bool(details),bool(answers)))/3*100)
    ranking_total=len(RANKING_QUESTION_LABELS)*MAX_RANKING_SELECTIONS;detail_total=len(DETAIL_LABELS);style_total=len(WORK_STYLE_QUESTIONS)
    main,side=st.columns([3.2,1],gap="medium")
    with main:
        st.markdown(_review_facts_html([("回答状況 全体",_progress_count(len(rankings)+len(details)+len(answers),ranking_total+detail_total+style_total)),("選択した価値観",_progress_count(len(rankings),ranking_total)),("経験・理由",_progress_count(len(details),detail_total)),("仕事の進め方",_progress_count(len(answers),style_total))]),unsafe_allow_html=True);st.markdown(f'<div class="metea-basic-section-grid">{"".join(cards)}</div>',unsafe_allow_html=True);st.markdown('<div class="metea-basic-next"><div><strong>次は就活の軸を確認できます</strong><span>価値観から整理した仕事選びの判断基準を確認しましょう。</span></div><a href="?page=profile_review&amp;category=axis">就活の軸を確認する →</a></div>',unsafe_allow_html=True)
    with side:_review_sidebar("values",completion)
    if active:_values_dialog(active,rankings,details,answers)


def _render_axis() -> None:
    axes=load_job_hunting_axis_data();active=_consume_edit_query("axis");_dashboard_header("axis","就活の軸","仕事を選ぶときに大切にする判断基準を確認できます。",[])
    if not axes:st.markdown('<div class="metea-empty">就活の軸はまだ登録されていません。<br><a href="?page=job_hunting_axis">就活の軸を入力する</a></div>',unsafe_allow_html=True);return
    cards=[_review_card_html("axis",f"axis_{i}",f"{item.priority_rank}位　{item.axis_title}",[("軸の名称",item.axis_title),("具体的な判断基準",item.axis_description),("作成方法","入力内容からの提案" if item.source_type!="manual" else "手動登録")]) for i,item in enumerate(axes)]
    axis_total=3;title_done=sum(bool(item.axis_title) for item in axes);description_done=sum(bool(item.axis_description) for item in axes);rank_done=sum(bool(item.priority_rank) for item in axes)
    main,side=st.columns([3.2,1],gap="medium")
    with main:
        st.markdown(_review_facts_html([("回答状況 全体",_progress_count(title_done+description_done+rank_done,axis_total*3)),("就活の軸",_progress_count(title_done,axis_total)),("判断基準",_progress_count(description_done,axis_total)),("優先順位",_progress_count(rank_done,axis_total))]),unsafe_allow_html=True);st.markdown(f'<div class="metea-basic-section-grid metea-axis-list">{"".join(cards)}</div>',unsafe_allow_html=True);st.markdown('<div class="metea-basic-next"><div><strong>次は職務経歴・スキルを確認できます</strong><span>会社・部署・役割ごとに登録した経験を振り返りましょう。</span></div><a href="?page=profile_review&amp;category=career">職務経歴を確認する →</a></div>',unsafe_allow_html=True)
    with side:_review_sidebar("axis",min(100,round(len(axes)/3*100)))
    if active:_axis_dialog(active,axes)


def _render_career() -> None:
    careers=load_career_data();active=_consume_edit_query("career");history_count=sum(len(h) for _,h in careers);_dashboard_header("career","職務経歴・スキル","会社・部署・役割ごとに登録した経験を確認できます。",[])
    if not careers:st.markdown('<div class="metea-empty">職務経歴はまだ登録されていません。<br><a href="?page=career">職務経歴を登録する</a></div>',unsafe_allow_html=True);return
    company_groups=[]
    for ci,(career,histories) in enumerate(careers):
        period=f'{career.start_year}/{career.start_month} ～ {"現在" if career.is_current else f"{career.end_year}/{career.end_month}"}'
        company_card=_review_card_html("career",f"company_{ci}",career.company_name,[("雇用形態",career.employment_type),("業種",career.industry),("在籍期間",period)])
        history_cards=[]
        for hi,history in enumerate(histories):
            hperiod=f'{history.start_year}/{history.start_month} ～ {f"{history.end_year}/{history.end_month}" if history.end_year else "現在"}'
            history_cards.append(_review_card_html("career",f"history_{ci}_{hi}",f'{history.department or "部署未設定"}　{history.position}',[("職種",history.occupation),("担当期間",hperiod),("業務内容",history.job_description),("実績・成果",history.achievements)]))
        children_html=f'<div class="metea-career-children">{"".join(history_cards)}</div>' if history_cards else '<div class="metea-career-empty">部署・役割はまだ登録されていません。</div>'
        company_groups.append(f'<section class="metea-career-group">{company_card}{children_html}</section>')
    achievement_done=sum(bool(history.achievements) for _,histories in careers for history in histories);total_records=len(careers)+history_count*2
    main,side=st.columns([3.2,1],gap="medium")
    with main:
        st.markdown(_review_facts_html([("登録情報 全体",_progress_count(len(careers)+history_count+achievement_done,total_records)),("会社情報",_progress_count(len(careers),len(careers))),("部署・役割",_progress_count(history_count,history_count)),("実績・成果",_progress_count(achievement_done,history_count))]),unsafe_allow_html=True);st.markdown(f'<div class="metea-career-list">{"".join(company_groups)}</div>',unsafe_allow_html=True);st.markdown('<div class="metea-career-import"><div class="metea-career-import__text"><div class="metea-career-import__icon">▤</div><div><strong>職務経歴書から情報を追加・更新できます</strong><span>PDFまたはWordファイルを読み込み、AIが整理した内容を確認してから登録できます。</span></div></div><a href="?page=career&amp;entry=document">PDF・Wordから取り込む →</a></div>',unsafe_allow_html=True);st.markdown('<div class="metea-basic-next"><div><strong>登録内容を求人比較に活用できます</strong><span>経験や実績をもとに、求人との相性を確認してみましょう。</span></div><a href="?page=job_list">求人を見てみる →</a></div>',unsafe_allow_html=True)
    with side:_review_sidebar("career",100 if careers and history_count else 50)
    if active:_career_dialog(active,careers)


def show_page() -> None:
    # 共通テーマの公開済み呼び出し方を維持し、起動中のStreamlitが
    # 変更前モジュールを保持していても画面を描画できるようにする。
    apply_self_discovery_theme(5, render_stepper=False)
    from pages.job_layout import render_job_navigation
    render_job_navigation("profile_review")
    _styles()
    notice=st.session_state.pop("profile_review_notice",None)
    if notice:_notice(notice)
    category=st.query_params.get("category","")
    _review_navigation(category)
    if not category:_render_category_selector();return
    renderers={"basic":_render_basic,"hope":_render_hope,"values":_render_values,"axis":_render_axis,"career":_render_career}
    renderer=renderers.get(category)
    if renderer is None:st.query_params["page"]="profile_review";st.query_params.pop("category",None);st.rerun()
    renderer()
