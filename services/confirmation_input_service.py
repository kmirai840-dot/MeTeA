"""確認項目に応じた入力形式。保存形式は既存の文章を維持する。"""
import re
from datetime import time

OTHER = 'その他（補足に記載）'
UNKNOWN = '確認できなかった'
CHOICES = {
    '転勤条件': ['転勤なし', '転勤あり', '条件付きで転勤あり'],
    'シフト勤務': ['シフト勤務なし', 'シフト勤務あり'],
    '夜勤': ['夜勤なし', '夜勤あり'],
    '雇用形態': ['正社員', '契約社員', '派遣社員', 'パート・アルバイト', '業務委託'],
    '休日形態': ['完全週休2日制（土日）', '完全週休2日制（曜日はシフト）', '週休2日制', 'シフト制'],
}
for name in ('在宅勤務', 'リモートワーク', 'フレックスタイム制度', '副業', '研修制度', '資格取得支援', '試用期間'):
    CHOICES[name] = ['あり', 'なし', '条件付きであり']
NUMBERS = {'残業時間': ('月平均・時間', 744), '年間休日数': ('日／年', 366),
           '年収': ('万円／年', None), '電車移動時間': ('片道・分', None)}
TIMES = {'始業時刻', '終業時刻'}


def input_kind(name):
    if name in CHOICES: return 'choice'
    if name in NUMBERS: return 'number'
    if name in TIMES: return 'time'
    return 'text'


def restore_input(name, saved):
    """自分の保存形式のみ解釈。以前の自由文は失わず補足に引き継ぐ。"""
    first, _, notes = saved.partition('\n補足：')
    prefix = name + '：'
    raw = first[len(prefix):] if first.startswith(prefix) else first
    kind = input_kind(name)
    if kind == 'choice' and raw in CHOICES[name] + [UNKNOWN, OTHER]:
        return raw, notes
    if first.startswith(prefix) and kind == 'number':
        suffix = ' ' + NUMBERS[name][0]
        if raw.endswith(suffix) and re.fullmatch(r'\d+', raw[:-len(suffix)]):
            value = int(raw[:-len(suffix)])
            maximum = NUMBERS[name][1]
            if maximum is None or value <= maximum:
                return value, notes
    if first.startswith(prefix) and kind == 'time' and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', raw):
        return time.fromisoformat(raw), notes
    return (OTHER if kind == 'choice' and saved else None), saved


def format_input(name, value, notes):
    kind = input_kind(name)
    notes = notes.strip()
    if kind == 'text': return notes
    if kind == 'choice':
        if value is None: raise ValueError('確認結果を選択してください。')
        if value not in CHOICES[name] + [UNKNOWN, OTHER]: raise ValueError('選択肢を確認してください。')
        if value == OTHER:
            if not notes: raise ValueError('その他の確認結果を補足に入力してください。')
            return notes
        raw = value
    elif value is None:
        if not notes: raise ValueError('確認した値、または確認できなかった理由を入力してください。')
        return notes
    elif kind == 'number':
        maximum = NUMBERS[name][1]
        if not isinstance(value, int) or value < 0 or (maximum is not None and value > maximum):
            raise ValueError('確認した数値を確認してください。')
        raw = f'{value} {NUMBERS[name][0]}'
    else:
        raw = value.strftime('%H:%M')
    return name + '：' + raw + ('\n補足：' + notes if notes else '')
