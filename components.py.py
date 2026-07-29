from pathlib import Path
import base64

ASSETS_DIR = Path(__file__).parent / "assets"


# ============================
# SVG表示
# ============================

def svg_image(filename, width=42):

    path = ASSETS_DIR / filename

    if not path.exists():
        return ""

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

# ============================
# 丸アイコン
# ============================

def circle_icon(
        filename,
        color,
        size=82):

    return f"""

<div
style="
width:{size}px;
height:{size}px;

background:{color};

border-radius:50%;

display:flex;

justify-content:center;

align-items:center;

">

{svg_image(filename,48)}

</div>

"""

# ============================
# メニューカード
# ============================

def menu_card(

    icon,

    bg,

    title,

    text

):

    return f"""

<div
style="
display:flex;
gap:22px;
align-items:center;
">

{circle_icon(icon,bg)}

<div>

<h3
style="
margin-bottom:8px;
">
{title}
</h3>

<p
style="
margin:0;
font-size:15px;
">
{text}
</p>

</div>

</div>

"""

# ============================
# ロゴ
# ============================

def logo(width=230):

    return f"""

<img

src="assets/logo.png"

width="{width}"

>

"""