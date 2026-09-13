"""選択式スキルを既存の文章形式へ変換する。旧文章は補足として保持する。"""

SKILL_OPTIONS = (
    "Excel入力", "Excel関数", "Excel VBA",
    "Word：文書作成・書式設定", "PowerPoint：スライド作成",
    "Googleスプレッドシート：表作成・集計", "Googleドキュメント：文書作成",
    "Googleスライド：資料作成", "SQL：データ抽出・集計",
    "Python：プログラミング", "Java：プログラミング",
    "GAS（Google Apps Script）：自動化・スクリプト作成",
    "HTML・CSS：Webページ作成",
    "Canva：画像・資料作成", "Figma：画面デザイン",
)
HEADER = "【選択したスキル】\n"
WORK = "仕事で使用："
LEARNING = "学習・個人活動で使用："
NOTES = "補足："
LEGACY_EXCEL = {
    "Excel：入力・表作成": "Excel入力",
    "Excel：四則演算・SUM・AVERAGE": "Excel関数",
    "Excel：IF": "Excel関数", "Excel：SUMIF・SUMIFS": "Excel関数",
    "Excel：COUNTIF・COUNTIFS": "Excel関数", "Excel：VLOOKUP": "Excel関数",
    "Excel：XLOOKUP": "Excel関数", "Excel：マクロ・VBA": "Excel VBA",
    "Excel：ピボットテーブル": None, "Excel：グラフ作成": None,
    "Excel：Power Query": None,
}


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
            if all(value in SKILL_OPTIONS or value in LEGACY_EXCEL for value in work + learning):
                notes = lines[2][len(NOTES):]
                converted = []
                for label, values in ((WORK, work), (LEARNING, learning)):
                    previous = [value for value in values if value in LEGACY_EXCEL]
                    if previous:
                        notes = (notes + "\n以前の詳細（" + label.rstrip("：") + "）：" + "／".join(previous)).strip()
                    mapped = [LEGACY_EXCEL.get(value, value) for value in values]
                    converted.append([value for value in SKILL_OPTIONS if value in mapped])
                return converted[0], converted[1], notes
    return [], [], text
