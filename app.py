from pathlib import Path
from dataclasses import dataclass
from html import escape
import base64

import streamlit as st
from pages.basic_info import render_basic_info_page


# ========================================
# 基本設定
# ========================================


ASSETS_DIR = Path(__file__).parent / "assets"


st.set_page_config(
    page_title="MeTeA",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)



# ========================================
# 表示画面の判定
# ========================================

current_page = st.query_params.get(
    "page",
    "home",
)

valid_pages = {
    "home",
    "basic_info",
    "job_change_reason",
    "job_list",
    "application_list",
    "milestones",
    "activity_history",
    "settings",
    "help",
    "logout",
}


if current_page not in valid_pages:
    st.query_params.clear()
    st.rerun()

if current_page == "basic_info":
    render_basic_info_page()
    st.stop()

elif current_page == "job_change_reason":
    st.title("転職理由")

    st.write(
        "転職理由画面は、今後この場所に実装します。"
    )

    if st.button("基本情報画面へ戻る"):
        st.query_params["page"] = "basic_info"
        st.rerun()

    st.stop()

elif current_page == "job_list":
    st.title("求人一覧")

    st.write(
        "求人一覧画面は、今後この場所に実装します。"
    )

    if st.button("トップ画面へ戻る"):
        st.query_params.clear()
        st.rerun()

    st.stop()

elif current_page == "application_list":
    st.title("応募企業一覧")

    st.write(
        "応募企業一覧画面は、今後この場所に実装します。"
    )

    if st.button("トップ画面へ戻る"):
        st.query_params.clear()
        st.rerun()

    st.stop()

elif current_page == "milestones":
    st.title("マイルストーン")

    st.write(
        "期限が近いタスクの一覧画面は、今後この場所に実装します。"
    )

    if st.button("トップ画面へ戻る"):
        st.query_params.clear()
        st.rerun()

    st.stop()

elif current_page == "activity_history":
    st.title("活動履歴")

    st.write(
        "最近の活動の一覧画面は、今後この場所に実装します。"
    )

    if st.button("トップ画面へ戻る"):
        st.query_params.clear()
        st.rerun()

    st.stop()

elif current_page == "settings":
    st.title("設定")

    st.write(
        "設定画面は、今後この場所に実装します。"
    )

    if st.button("トップ画面へ戻る"):
        st.query_params.clear()
        st.rerun()

    st.stop()

elif current_page == "help":
    st.title("使い方")

    st.write(
        "使い方画面は、今後この場所に実装します。"
    )

    if st.button("トップ画面へ戻る"):
        st.query_params.clear()
        st.rerun()

    st.stop()

elif current_page == "logout":
    st.title("ログアウト")

    st.write(
        "ログアウトしますか？"
    )

    st.info(
        "実際のログアウト処理は、認証機能の実装時に追加します。"
    )

    if st.button("トップ画面へ戻る"):
        st.query_params.clear()
        st.rerun()

    st.stop()


# ========================================
# 表示データ用クラス
# ========================================


@dataclass(frozen=True)
class NavItem:
    label: str
    icon: str
    href: str = "#"


@dataclass(frozen=True)
class ActionCard:
    title: str
    description: str
    icon: str
    color_class: str
    href: str = "#"


@dataclass(frozen=True)
class TaskItem:
    dot_class: str
    date: str
    company: str
    task: str
    remaining: str
    deadline_class: str


@dataclass(frozen=True)
class ActivityItem:
    text: str
    time: str
    icon: str
    color_class: str

# ========================================
# ヘッダーメニュー
# ========================================


NAV_ITEMS = [
    NavItem(
        label="使い方",
        icon="help.svg",
        href="?page=help",
    ),
    NavItem(
        label="設定",
        icon="nav-settings.svg",
        href="?page=settings",
    ),
    NavItem(
        label="ログアウト",
        icon="logout.svg",
        href="?page=logout",
    ),
]

# ========================================
# メインメニュー
# ========================================


ACTION_CARDS = [
    ActionCard(
        title="① 自分を知る",
        description="あなたの情報や価値観を整理しましょう",
        icon="user.svg",
        color_class="metea-bubble-blue",
        href="?page=basic_info",
        
    ),
    ActionCard(
        title="② 求人を比較する",
        description="求人は比較・分析して、相性を見える化します",
        icon="compare.svg",
        color_class="metea-bubble-green",
        href="?page=job_list",
    ),
    ActionCard(
        title="③ 応募後を管理する",
        description="応募状況やマイルストーンを管理しましょう",
        icon="flag.svg",
        color_class="metea-bubble-orange",
        href="?page=application_list",
    ),
    ActionCard(
        title="設定",
        description="アカウント情報や各種設定を行います",
        icon="settings.svg",
        color_class="metea-bubble-purple",
        href="?page=settings",
    ),
]

# ========================================
# 期限が近いタスク
# ========================================


TASK_ITEMS = [
    TaskItem(
        dot_class="metea-dot-red",
        date="7/24（水）",
        company="A社",
        task="履歴書を提出",
        remaining="あと1日",
        deadline_class="metea-deadline-red",
    ),
    TaskItem(
        dot_class="metea-dot-orange",
        date="7/25（金）",
        company="B社",
        task="面接準備",
        remaining="あと2日",
        deadline_class="metea-deadline-orange",
    ),
    TaskItem(
        dot_class="metea-dot-amber",
        date="7/26（土）",
        company="C社",
        task="企業研究を深める",
        remaining="あと3日",
        deadline_class="metea-deadline-amber",
    ),
]

# ========================================
# 最近の活動
# ========================================


ACTIVITY_ITEMS = [
    ActivityItem(
        text="プロフィールを更新しました",
        time="7/22 14:30",
        icon="user.svg",
        color_class="metea-activity-blue",
    ),
    ActivityItem(
        text="A社の求人を登録しました",
        time="7/22 10:15",
        icon="compare.svg",
        color_class="metea-activity-green",
    ),
    ActivityItem(
        text="比較結果を保存しました",
        time="7/21 16:45",
        icon="compare.svg",
        color_class="metea-activity-green",
    ),
]

# ========================================
# SVG読み込み
# ========================================


def svg_data_uri(filename):
    """assets内のSVGをHTMLで表示できる形式に変換する。"""

    path = ASSETS_DIR / filename
    svg = path.read_text(encoding="utf-8")
    encoded = base64.b64encode(
        svg.encode("utf-8")
    ).decode("ascii")

    return f"data:image/svg+xml;base64,{encoded}"

# ========================================
# ヘッダーメニューHTML生成
# ========================================


def render_nav_item(item):
    icon = svg_data_uri(item.icon)

    return f"""
    <a
        class="metea-nav-link"
        href="{escape(item.href)}"
    >
        <img
            src="{icon}"
            alt=""
        >
        <span>{escape(item.label)}</span>
    </a>
    """


def render_nav_items():
    return "".join(
        render_nav_item(item)
        for item in NAV_ITEMS
    )

# ========================================
# メインメニューHTML生成
# ========================================


def render_action_card(card):
    icon = svg_data_uri(card.icon)

    return f"""
    <a
        class="metea-action-card"
        href="{escape(card.href)}"
    >
        <span class="
            metea-icon-bubble
            {escape(card.color_class)}
        ">
            <img
                src="{icon}"
                alt=""
            >
        </span>

        <span>
            <span class="metea-action-title">
                {escape(card.title)}
            </span>

            <span class="metea-action-desc">
                {escape(card.description)}
            </span>
        </span>

        <i
            class="metea-chevron"
            aria-hidden="true"
        ></i>
    </a>
    """


def render_action_cards():
    return "".join(
        render_action_card(card)
        for card in ACTION_CARDS
    )

# ========================================
# タスクHTML生成
# ========================================


def render_task_item(item):
    return f"""
    <div class="metea-task-row">
        <i class="
            metea-dot
            {escape(item.dot_class)}
        "></i>

        <span>{escape(item.date)}</span>
        <span>{escape(item.company)}</span>
        <span>{escape(item.task)}</span>

        <span class="
            metea-deadline
            {escape(item.deadline_class)}
        ">
            {escape(item.remaining)}
        </span>

    </div>
    """


def render_task_items():
    return "".join(
        render_task_item(item)
        for item in TASK_ITEMS
    )

# ========================================
# 最近の活動HTML生成
# ========================================


def render_activity_item(item):
    icon = svg_data_uri(item.icon)

    return f"""
    <div class="metea-activity-row">
        <span class="
            metea-activity-icon
            {escape(item.color_class)}
        ">
            <img
                src="{icon}"
                alt=""
            >
        </span>

        <span>{escape(item.text)}</span>

        <time class="metea-activity-time">
            {escape(item.time)}
        </time>
    </div>
    """


def render_activity_items():
    return "".join(
        render_activity_item(item)
        for item in ACTIVITY_ITEMS
    )

# ========================================
# 各ブロックのHTMLを生成
# ========================================

nav_items_html = render_nav_items()
action_cards_html = render_action_cards()
task_items_html = render_task_items()
activity_items_html = render_activity_items()



page = """
<style>
  :root {
    --ink: #071a36;
    --muted: #53627a;
    --blue: #146cff;
    --line: #e4e9f1;
    --panel: #ffffff;
    --page: #fbfcfe;
  }

  header[data-testid="stHeader"], #MainMenu, footer {
    display: none !important;
  }

  .stApp {
    background: var(--page);
  }

  .block-container {
    width: 100%;
    max-width: none;
    padding: 0 0 48px;
  }

  .metea-shell,
  .metea-shell * {
    box-sizing: border-box;
  }

  .metea-shell {
    min-height: 100vh;
    color: var(--ink);
    font-family: "Yu Gothic", "YuGothic", "Hiragino Kaku Gothic ProN",
      "Noto Sans JP", sans-serif;
    font-weight: 600;
    letter-spacing: .01em;
  }

  .metea-shell a {
    color: inherit;
    text-decoration: none;
  }

  .metea-header {
    height: 84px;
    background: rgba(255, 255, 255, .96);
    border-bottom: 1px solid #e8ecf2;
    box-shadow: 0 2px 8px rgba(20, 39, 73, .035);
  }

  .metea-header-inner {
    width: min(1174px, calc(100% - 72px));
    height: 100%;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .metea-brand-group {
    display: flex;
    align-items: center;
    gap: 42px;
  }

  .metea-logo-frame {
    width: 139px;
    height: 56px;
    display: grid;
    place-items: center;
    overflow: hidden;
  }

  .metea-logo {
    display: block;
    width: 139px;
    height: 56px;
    object-fit: contain;
    transform: scale(2);
  }

  .metea-tagline {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: .07em;
    white-space: nowrap;
  }

  .metea-nav {
    display: flex;
    align-items: center;
    gap: 38px;
  }

  .metea-nav-link {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
  }

  .metea-nav-link img {
    width: 24px;
    height: 24px;
  }

  .metea-dashboard {
    width: min(1168px, calc(100% - 72px));
    margin: 25px auto 0;
    display: grid;
    grid-template-columns: 545px 1fr;
    gap: 42px;
    align-items: start;
  }

  .metea-intro {
    padding: 20px 8px 0;
  }

  .metea-intro h1 {
    margin: 0 0 20px;
    color: var(--ink);
    font-size: 43px;
    line-height: 1.28;
    letter-spacing: .015em;
    font-weight: 800;
  }

  .metea-lead {
    margin: 0 0 33px;
    color: var(--ink);
    font-size: 17px;
    line-height: 1.85;
    font-weight: 600;
  }

  .metea-action-list {
    display: grid;
    gap: 16px;
  }

  .metea-action-card,
  .metea-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    box-shadow: 0 3px 10px rgba(17, 42, 82, .055);
  }

  .metea-action-card {
    min-height: 104px;
    border-radius: 12px;
    padding: 16px 30px 16px 17px;
    display: grid;
    grid-template-columns: 78px 1fr 28px;
    align-items: center;
    gap: 25px;
  }

  .metea-icon-bubble {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    display: grid;
    place-items: center;
  }

  .metea-icon-bubble img {
    width: 48px;
    height: 48px;
  }

  .metea-bubble-blue { background: #eef5ff; }
  .metea-bubble-green { background: #eaf9f4; }
  .metea-bubble-orange { background: #fff3e8; }
  .metea-bubble-purple { background: #f3efff; }

  .metea-action-title {
    display: block;
    margin: 0 0 8px;
    color: var(--ink);
    font-size: 20px;
    line-height: 1.2;
    font-weight: 800;
  }

  .metea-action-desc {
    display: block;
    margin: 0;
    color: var(--ink);
    font-size: 14px;
    line-height: 1.45;
  }

  .metea-chevron {
    width: 14px;
    height: 14px;
    border-top: 2px solid var(--ink);
    border-right: 2px solid var(--ink);
    transform: rotate(45deg);
  }

  .metea-right-column {
    display: grid;
    gap: 15px;
  }

  .metea-panel {
    border-radius: 12px;
  }

  .metea-next-step {
    min-height: 186px;
    padding: 21px 24px;
    display: grid;
    grid-template-columns: 91px 1fr;
    gap: 22px;
    align-items: start;
  }

  .metea-next-icon {
    width: 82px;
    height: 82px;
    border-radius: 50%;
    background: #eef5ff;
    display: grid;
    place-items: center;
  }

  .metea-next-icon img {
    width: 52px;
    height: 52px;
  }

  .metea-next-body h2 {
    margin: 0 0 10px;
    color: var(--ink);
    font-size: 21px;
  }

  .metea-next-body p {
    margin: 0 0 8px;
    color: var(--ink);
    font-size: 14px;
    line-height: 1.65;
  }

  .metea-text-link {
    color: var(--blue) !important;
    font-weight: 800;
  }

  .metea-primary-button {
    display: inline-flex;
    align-items: center;
    gap: 14px;
    margin-top: 8px;
    padding: 11px 25px;
    color: #fff !important;
    background: linear-gradient(180deg, #2878ff, #0862f1);
    border-radius: 7px;
    box-shadow: 0 4px 8px rgba(20, 108, 255, .2);
    font-size: 15px;
    font-weight: 800;
  }

  .metea-info-panel {
    padding: 14px 22px 11px;
  }

  .metea-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .metea-panel-head h2 {
    margin: 0;
    color: var(--ink);
    font-size: 18px;
  }

  .metea-panel-head a {
    color: var(--blue);
    font-size: 12px;
    font-weight: 800;
  }

  .metea-task-row {
    min-height: 43px;
    display: grid;
    grid-template-columns: 17px 82px 53px 1fr 69px;
    align-items: center;
    gap: 9px;
    border-top: 1px solid #edf0f5;
    color: var(--ink);
    font-size: 13px;
  }

  .metea-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }

  .metea-dot-red { background: #ff3340; }
  .metea-dot-orange { background: #ff6729; }
  .metea-dot-amber { background: #ffb118; }

  .metea-deadline {
    justify-self: end;
    padding: 3px 9px;
    border: 1px solid currentColor;
    border-radius: 999px;
    line-height: 1;
    white-space: nowrap;
    font-size: 12px;
  }

  .metea-deadline-red { color: #ff4c57; }
  .metea-deadline-orange { color: #ff692d; }
  .metea-deadline-amber { color: #eea000; }

  .metea-activity-panel {
    padding: 14px 22px 10px;
  }

  .metea-activity-row {
    min-height: 42px;
    display: grid;
    grid-template-columns: 38px 1fr auto;
    align-items: center;
    border-top: 1px solid #edf0f5;
    color: var(--ink);
    font-size: 14px;
  }

  .metea-activity-icon {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    display: grid;
    place-items: center;
  }

  .metea-activity-icon img {
    width: 21px;
    height: 21px;
  }

  .metea-activity-blue { background: #edf4ff; }
  .metea-activity-green { background: #eaf9f4; }

  .metea-activity-time {
    color: #8997ad;
    font-size: 13px;
    font-weight: 500;
  }

  .metea-quote-panel {
    min-height: 108px;
    padding: 17px 21px;
    overflow: hidden;
    position: relative;
    background: linear-gradient(110deg, #edf6ff 0%, #f6faff 58%, #e8f1ff 100%);
  }

  .metea-quote-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 0 7px;
    color: #126dff;
    font-size: 15px;
  }

  .metea-quote-title img {
    width: 19px;
    height: 19px;
  }

  .metea-quote-panel p {
    position: relative;
    z-index: 2;
    margin: 0;
    color: var(--ink);
    font-size: 13px;
    line-height: 1.7;
  }

  .metea-scenery {
    position: absolute;
    right: 8px;
    bottom: 0;
    width: 225px;
    height: 100px;
    object-fit: contain;
    object-position: bottom right;
  }

  div[data-testid="stToast"] {
    display: none !important;
  }

  @media (max-width: 980px) {
    .metea-header-inner,
    .metea-dashboard {
      width: min(92%, 680px);
    }

    .metea-tagline {
      display: none;
    }

    .metea-nav {
      gap: 16px;
    }

    .metea-dashboard {
      grid-template-columns: 1fr;
    }

    .metea-intro {
      padding-top: 0;
    }
  }

  @media (max-width: 560px) {
    .metea-header {
      height: 70px;
    }

    .metea-header-inner {
      width: calc(100% - 30px);
    }

    .metea-logo {
      width: 115px;
    }

    .metea-nav-link span {
      display: none;
    }

    .metea-dashboard {
      width: calc(100% - 28px);
      margin-top: 22px;
    }

    .metea-intro h1 {
      font-size: 34px;
    }

    .metea-action-card {
      grid-template-columns: 62px 1fr 20px;
      gap: 14px;
      padding-left: 12px;
    }

    .metea-icon-bubble {
      width: 58px;
      height: 58px;
    }

    .metea-next-step {
      grid-template-columns: 72px 1fr;
      padding: 18px;
      gap: 14px;
    }

    .metea-next-icon {
      width: 66px;
      height: 66px;
    }

    .metea-task-row {
      grid-template-columns: 14px 63px 42px 1fr 58px;
      gap: 5px;
      font-size: 11px;
    }
  }

/* PC画面全体を80％に縮小 */
@media (min-width: 1000px) {
    .metea-shell {
        zoom: 0.8;
    }
}
</style>

<div class="metea-shell">
  <header class="metea-header">
    <div class="metea-header-inner">
      <div class="metea-brand-group">
        <span class="metea-logo-frame"><img class="metea-logo" src="__LOGO__" alt="MeTeA"></span>
        <div class="metea-tagline">自分が見えた、道が見えた。</div>
      </div>

      <nav class="metea-nav" aria-label="メインナビゲーション">
        __NAV_ITEMS_HTML__
        </nav>
    </div>
  </header>

  <main class="metea-dashboard">
    <section class="metea-intro">
      <h1>納得できる一歩を。</h1>
      <p class="metea-lead">
        あなたの価値観や経験を整理し、<br>
        求人との相性を見える化することで、<br>
        納得できる応募判断をサポートします。
      </p>

      <div class="metea-action-list">
      __ACTION_CARDS_HTML__
      </div>
    </section>

    <section class="metea-right-column">
      <article class="metea-panel metea-next-step">
        <div class="metea-next-icon">
          <img src="__SPARKLE__" alt="">
        </div>
        <div class="metea-next-body">
          <h2>次の一歩</h2>
          <p>まだ入力が完了していない項目があります。</p>
          <p>まずは「<a class="metea-text-link" href="?page=basic_info">基本情報</a>」から始めてみましょう。</p>
          <a class="metea-primary-button" href="?page=basic_info">基本情報を入力する <span>→</span></a>
        </div>
      </article>

      <article class="metea-panel metea-info-panel">
        <div class="metea-panel-head">
          <h2>期限が近いタスク</h2>
          <a href="?page=milestones">すべてのタスクを見る</a>
        </div>

        __TASK_ITEMS_HTML__
      </article>

      <article class="metea-panel metea-activity-panel">
        <div class="metea-panel-head">
          <h2>最近の活動</h2>
          <a href="?page=activity_history">すべて見る</a>
        </div>

        __ACTIVITY_ITEMS_HTML__
      </article>

      <article class="metea-panel metea-quote-panel">
        <h2 class="metea-quote-title"><img src="__LEAF__" alt="">今日のひとこと</h2>
        <p>焦らなくても大丈夫です。<br>納得できる一歩は、きっと未来につながります。</p>
        <img class="metea-scenery" src="__SCENERY__" alt="">
      </article>
    </section>
  </main>
</div>
"""

# ========================================
# Pythonで生成したHTMLをページへ差し込む
# ========================================


page = page.replace(
    "__NAV_ITEMS_HTML__",
    nav_items_html,
)

page = page.replace(
    "__ACTION_CARDS_HTML__",
    action_cards_html,
)

page = page.replace(
    "__TASK_ITEMS_HTML__",
    task_items_html,
)

page = page.replace(
    "__ACTIVITY_ITEMS_HTML__",
    activity_items_html,
)

# ========================================
# ページ固定SVG
# ========================================


assets = {
    "__LOGO__": "logo.svg",
    "__SPARKLE__": "sparkle.svg",
    "__LEAF__": "leaf.svg",
    "__SCENERY__": "scenery.svg",
}


for placeholder, filename in assets.items():
    page = page.replace(
        placeholder,
        svg_data_uri(filename),
    )


# ========================================
# ページ表示
# ========================================


st.html(page)
