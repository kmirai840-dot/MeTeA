"""価値観機能で共通利用する定数を定義する。"""


# ========================================
# 順位付き質問の種類
# ========================================

QUESTION_IMPORTANT_VALUE = "important_value"
QUESTION_REWARDING_SCENE = "rewarding_scene"
QUESTION_STRENGTH_ENVIRONMENT = "strength_environment"


# ========================================
# 自由記述の種類
# ========================================

DETAIL_REWARDING_EXPERIENCE = "rewarding_experience"
DETAIL_ENVIRONMENT_REASON = "environment_reason"
    

# ========================================
# 仕事の進め方の質問
# ========================================

WORK_STYLE_STARTING_METHOD = "starting_method"
WORK_STYLE_TASK_MANAGEMENT = "task_management"
WORK_STYLE_SHARING_TIMING = "sharing_timing"
WORK_STYLE_IMPROVEMENT_METHOD = "improvement_method"
WORK_STYLE_CONSULTATION_TIMING = "consultation_timing"
WORK_STYLE_DECISION_METHOD = "decision_method"
WORK_STYLE_SOLUTION_SCOPE = "solution_scope"
WORK_STYLE_VERIFICATION_METHOD = "verification_method"
WORK_STYLE_PROBLEM_RESPONSE = "problem_response"
WORK_STYLE_THINKING_METHOD = "thinking_method"


# ========================================
# 5段階評価
# ========================================

WORK_STYLE_SCORE_MIN = 1
WORK_STYLE_SCORE_MAX = 5
WORK_STYLE_SCORE_NEUTRAL = 3


# ========================================
# 入力上限
# ========================================

MAX_RANKING_SELECTIONS = 3
MAX_OTHER_TEXT_LENGTH = 100
MAX_REWARDING_EXPERIENCE_LENGTH = 500
MAX_ENVIRONMENT_REASON_LENGTH = 300


# ========================================
# 下書き保存名
# ========================================

WORK_VALUES_FORM_NAME = "work_values"


# ========================================
# 仕事で大切にしたいこと
# ========================================

IMPORTANT_VALUE_OPTIONS = [
    "納得感",
    "成長",
    "安定",
    "挑戦",
    "人や社会への貢献",
    "専門性",
    "自律性",
    "公平性",
    "協働",
    "信頼関係",
    "創造性",
    "誠実さ",
    "その他",
]


# ========================================
# やりがいを感じる場面
# ========================================

REWARDING_SCENE_OPTIONS = [
    "顧客や利用者から感謝されたとき",
    "顧客や利用者の課題を解決できたとき",
    "目標や数字を達成したとき",
    "難しい問題を解決できたとき",
    "業務を効率化できたとき",
    "新しい仕組みやサービスを作れたとき",
    "誰かの成長を支援できたとき",
    "チームで成果を出せたとき",
    "自分の提案が採用されたとき",
    "専門知識や経験を活かせたとき",
    "正確に仕事をやり遂げたとき",
    "新しい知識や技術を身につけたとき",
    "責任のある仕事を任されたとき",
    "その他",
]


# ========================================
# 力を発揮しやすい環境
# ========================================

STRENGTH_ENVIRONMENT_OPTIONS = [
    "周囲と相談しながら進められる",
    "役割や期待される成果が明確である",
    "自分で考えて行動できる",
    "定期的にフィードバックを受けられる",
    "チームで協力して進められる",
    "一人で集中する時間が確保されている",
    "新しい挑戦や変化が多い",
    "手順や進め方がある程度整っている",
    "多様な立場の人と関われる",
    "自分の専門性や経験を活かせる",
    "長期的な視点で仕事に取り組める",
    "自分の意見や提案を伝えやすい",
    "必要な教育や支援を受けられる",
    "その他",
]


# ========================================
# 5段階評価の表示文言
# ========================================

WORK_STYLE_SCORE_LABELS = {
    1: "左側に非常に近い",
    2: "左側にやや近い",
    3: "どちらともいえない",
    4: "右側にやや近い",
    5: "右側に非常に近い",
}


# ========================================
# 仕事の進め方の質問一覧
# ========================================

WORK_STYLE_QUESTIONS = [
    {
        "question_type": WORK_STYLE_STARTING_METHOD,
        "title": "仕事に着手するときの進め方",
        "left_text": "事前に計画を立ててから着手する",
        "right_text": "まず着手してから調整する",
    },
    {
        "question_type": WORK_STYLE_TASK_MANAGEMENT,
        "title": "複数の業務への対応",
        "left_text": "一つずつ完了させる",
        "right_text": "複数の業務を並行して進める",
    },
    {
        "question_type": WORK_STYLE_SHARING_TIMING,
        "title": "成果物を共有するタイミング",
        "left_text": "十分に品質を高めてから共有する",
        "right_text": "早い段階で共有して改善する",
    },
    {
        "question_type": WORK_STYLE_IMPROVEMENT_METHOD,
        "title": "改善への取り組み方",
        "left_text": "既存の方法を磨き込む",
        "right_text": "新しい方法を試す",
    },
    {
        "question_type": WORK_STYLE_CONSULTATION_TIMING,
        "title": "周囲へ相談するタイミング",
        "left_text": "自分で整理してから相談する",
        "right_text": "早い段階で相談しながら整理する",
    },
    {
        "question_type": WORK_STYLE_DECISION_METHOD,
        "title": "判断が必要な場合の進め方",
        "left_text": "判断基準を確認してから進める",
        "right_text": "目的から自分で判断して進める",
    },
    {
        "question_type": WORK_STYLE_SOLUTION_SCOPE,
        "title": "課題解決で重視する範囲",
        "left_text": "目の前の課題を解決する",
        "right_text": "再発防止の仕組みまで作る",
    },
    {
        "question_type": WORK_STYLE_VERIFICATION_METHOD,
        "title": "情報が不足している場合の行動",
        "left_text": "必要な情報を集めてから判断する",
        "right_text": "仮説を立てて検証しながら進める",
    },
    {
        "question_type": WORK_STYLE_PROBLEM_RESPONSE,
        "title": "問題が発生した場合の着眼点",
        "left_text": "原因を深く分析する",
        "right_text": "打ち手を早く試す",
    },
    {
        "question_type": WORK_STYLE_THINKING_METHOD,
        "title": "考えをまとめる方法",
        "left_text": "一人で整理してから伝える",
        "right_text": "対話しながら考えを整理する",
    },
]




