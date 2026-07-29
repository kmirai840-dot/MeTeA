STYLE = """
<style>

/* ==============================
   全体
============================== */

.stApp{
    background:#F8FAFC;
}

/* コンテンツ幅 */

.block-container{
    max-width:1280px;
    padding-top:2rem;
    padding-bottom:3rem;
}

/* ==============================
   見出し
============================== */

h1,h2,h3{
    color:#1E293B;
    letter-spacing:-0.02em;
}

p{
    color:#475569;
    line-height:1.8;
}

/* ==============================
   ボタン
============================== */

.stButton>button{

    width:100%;

    border-radius:12px;

    height:48px;

    border:none;

    background:#246BFD;

    color:white;

    font-weight:600;

    transition:.2s;

}

.stButton>button:hover{

    background:#1756D6;

}

/* ==============================
   カード
============================== */

div[data-testid="stVerticalBlockBorderWrapper"]{

    border-radius:18px;

    border:1px solid #E2E8F0;

    background:white;

    box-shadow:
        0 8px 24px rgba(15,23,42,.05);

}

/* ==============================
   区切り線
============================== */

hr{

    border:none;

    border-top:1px solid #E2E8F0;

}

/* ==============================
   キャプション
============================== */

[data-testid="stCaptionContainer"]{

    color:#94A3B8;

}

</style>
"""