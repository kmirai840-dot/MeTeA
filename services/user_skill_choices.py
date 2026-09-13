"""選択式スキルを既存の文章形式へ変換する。旧文章は補足として保持する。"""

SKILL_OPTIONS = (
    "Excel：入力・表作成", "Excel：四則演算・SUM・AVERAGE", "Excel：IF",
    "Excel：SUMIF・SUMIFS", "Excel：COUNTIF・COUNTIFS", "Excel：VLOOKUP",
    "Excel：XLOOKUP", "Excel：ピボットテーブル", "Excel：グラフ作成",
    "Excel：Power Query", "Excel：マクロ・VBA",
    "Word：文書作成・書式設定", "PowerPoint：スライド作成",
    "Googleスプレッドシート：表作成・集計", "Googleドキュメント：文書作成",
    "Googleスライド：資料作成", "SQL：データ抽出・集計",
    "Python：プログラミング", "HTML・CSS：Webページ作成",
    "Canva：画像・資料作成", "Figma：画面デザイン",
)
HEADER = "【選択したスキル】\n"
WORK = "仕事で使用："
LEARNING = "学習・個人活動で使用："
NOTES = "補足："


def format_skill_choices(work, learning, notes):
    if any(value not in SKILL_OPTIONS for value in [*work, *learning]):
        raise ValueError("選択肢にないスキルは補足欄に入力してください。")
    work = [value for value in SKILL_OPTIONS if value in work]
    learning = [value for value in SKILL_OPTIONS if value in learning]
    if not work and not learning:
        return notes.strip()
    return HEADER + WORK + "／".join(work) + "\n" + LEARNING + "／".join(learning) + "\n" + NOTES + notes.strip()


def parse_skill_choices(text):
    if text.startswith(HEADER):
        lines = text[len(HEADER):].split("\n", 2)
        if len(lines) == 3 and lines[0].startswith(WORK) and lines[1].startswith(LEARNING) and lines[2].startswith(NOTES):
            work = list(filter(None, lines[0][len(WORK):].split("／")))
            learning = list(filter(None, lines[1][len(LEARNING):].split("／")))
            if all(value in SKILL_OPTIONS for value in work + learning):
                return work, learning, lines[2][len(NOTES):]
    return [], [], text
