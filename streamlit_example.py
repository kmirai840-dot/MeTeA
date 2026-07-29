from pathlib import Path
import base64
import streamlit as st


ASSETS_DIR = Path(__file__).parent / "assets"


def svg_image(filename: str, width: int) -> str:
    svg = (ASSETS_DIR / filename).read_text(encoding="utf-8")
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    return f'''
    <img
        src="data:image/svg+xml;base64,{encoded}"
        width="{width}"
        alt=""
        style="display:block;"
    >
    '''


# ロゴ
st.html(svg_image("logo.svg", 220))

# アイコン例
st.html(
    f'''
    <div style="
        width:82px;
        height:82px;
        border-radius:50%;
        background:#EEF4FF;
        display:flex;
        align-items:center;
        justify-content:center;
    ">
        {svg_image("user.svg", 48)}
    </div>
    '''
)
