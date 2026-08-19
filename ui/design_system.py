"""MeTeAの共通デザイントークン、エラー表示、通知部品。"""

from collections.abc import Iterable, Mapping
from html import escape

import streamlit as st


DESIGN_TOKENS = {
    "ink": "#071a36",
    "muted": "#66758c",
    "primary": "#146cff",
    "primary_dark": "#0759df",
    # 既存画面で使用中の名称。段階的な共通化中も見た目を変えない。
    "blue": "#146cff",
    "blue_dark": "#0759df",
    "page": "#f5f8fc",
    "panel": "#ffffff",
    "line": "#dce5f2",
    "soft_blue": "#eef5ff",
    "error": "#d92d3a",
    "error_border": "#ffb8bd",
    "error_background": "#fff7f7",
    "radius_card": "14px",
    "radius_control": "9px",
    "shadow_card": "0 8px 24px rgba(31,65,114,.055)",
    "shadow": "0 14px 36px rgba(31,65,114,.08)",
    "space_section": "24px",
}


def common_design_css() -> str:
    """画面固有CSSから参照できる共通トークンと共通部品CSSを返す。"""

    token_lines = "".join(
        f"--metea-{name.replace('_', '-')}:{value};"
        for name, value in DESIGN_TOKENS.items()
    )
    return f"""
    :root{{{token_lines}}}
    .stApp,.stApp button,.stApp input,.stApp textarea,.stApp select{{
      font-family:"Yu Gothic","YuGothic","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
    }}
    .metea-error-summary,.metea-save-error{{
      display:flex;gap:14px;align-items:flex-start;margin:6px 0 12px;padding:13px 16px;
      border:1.5px solid var(--metea-error-border);border-radius:11px;
      background:var(--metea-error-background);color:var(--metea-error);
    }}
    .metea-error-summary__icon,.metea-save-error__icon{{
      display:grid;place-items:center;flex:0 0 25px;width:25px;height:25px;
      border:2px solid #ef3f4c;border-radius:7px 7px 9px 9px;font-weight:900;line-height:1;
    }}
    .metea-error-summary strong,.metea-save-error strong{{font-size:.95rem}}
    .metea-error-summary ul{{margin:5px 0 0;padding-left:1.15rem}}
    .metea-error-summary li{{margin:2px 0;font-size:.88rem}}
    .metea-save-error p{{margin:5px 0 0!important;color:#a92b35!important;font-size:.86rem!important;line-height:1.55!important}}
    .metea-field-error{{
      display:block;min-height:18px;margin:1px 0 4px!important;color:#dc3545!important;
      font-size:.84rem!important;font-weight:650;line-height:1.35!important;
    }}
    [data-testid="stElementContainer"]:has(.metea-field-error){{min-height:23px;margin-bottom:2px;overflow:visible}}
    .metea-card{{border:1px solid var(--metea-line);border-radius:var(--metea-radius-card);background:var(--metea-panel);box-shadow:var(--metea-shadow-card)}}
    """


def apply_common_design_system() -> None:
    """共通トークンと共通部品の見た目を現在画面へ適用する。"""

    st.markdown(f"<style>{common_design_css()}</style>", unsafe_allow_html=True)


def _messages(errors: Mapping[str, str] | Iterable[str]) -> list[str]:
    source = errors.values() if isinstance(errors, Mapping) else errors
    return list(dict.fromkeys(str(message).strip() for message in source if str(message).strip()))


def render_validation_summary(
    errors: Mapping[str, str] | Iterable[str],
    *,
    title: str = "入力内容を確認してください",
) -> None:
    """必須入力等のエラーを全画面共通の一覧形式で表示する。"""

    messages = _messages(errors)
    if not messages:
        return
    items = "".join(f"<li>{escape(message)}</li>" for message in messages)
    st.markdown(
        '<div class="metea-error-summary" role="alert">'
        '<span class="metea-error-summary__icon" aria-hidden="true">!</span>'
        f'<div><strong>{escape(title)}</strong><ul>{items}</ul></div></div>',
        unsafe_allow_html=True,
    )


def render_field_error(message: str | None) -> None:
    """入力欄直下へ共通書式のエラーを表示する。"""

    if message:
        st.markdown(
            f'<p class="metea-field-error" role="alert">{escape(str(message))}</p>',
            unsafe_allow_html=True,
        )


def render_save_failure(
    subject: str,
    *,
    recovery: str = "入力内容は保持されています。時間をおいて、もう一度お試しください。",
) -> None:
    """保存失敗と次に行うことを共通書式で伝える。"""

    st.markdown(
        '<div class="metea-save-error" role="alert">'
        '<span class="metea-save-error__icon" aria-hidden="true">!</span>'
        f'<div><strong>{escape(subject)}を保存できませんでした</strong>'
        f'<p>{escape(recovery)}</p></div></div>',
        unsafe_allow_html=True,
    )


def notify_saved(message: str) -> None:
    """正常完了はレイアウトを押し下げない一時通知で表示する。"""

    st.toast(message)
