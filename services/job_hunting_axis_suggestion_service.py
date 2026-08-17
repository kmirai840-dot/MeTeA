"""保存済み回答から、利用者が確認する就活の軸候補を作成する。"""

from constants.work_values import (
    QUESTION_IMPORTANT_VALUE,
    QUESTION_REWARDING_SCENE,
    QUESTION_STRENGTH_ENVIRONMENT,
)
from models import HopeCondition, HopeConditionItem, JobHuntingAxis, WorkValueRanking
from services.hope_condition_service import load_hope_conditions_data
from services.work_values_service import load_work_values_data


VALUE_AXIS_TEMPLATES: dict[str, tuple[str, str]] = {
    "納得感": ("納得できる意思決定", "仕事の目的や判断理由が明確で、納得して取り組める環境を重視する"),
    "成長": ("成長できる環境", "新しい知識や経験を得ながら、継続的に成長できる仕事を重視する"),
    "安定": ("長く安心して働けること", "雇用や事業の安定性があり、長期的に働ける環境を重視する"),
    "挑戦": ("新しい挑戦の機会", "変化や新しい課題に取り組み、経験の幅を広げられる環境を重視する"),
    "人や社会への貢献": ("人や社会への貢献", "仕事を通じて、顧客や社会の役に立っている実感を持てることを重視する"),
    "専門性": ("専門性を高められること", "これまでの経験を活かしながら、専門知識や技能を深められる仕事を重視する"),
    "自律性": ("自分で考えて進められること", "一定の裁量があり、自分で考えて行動できる環境を重視する"),
    "公平性": ("公平な評価と制度", "役割や成果が公平な基準で評価される組織を重視する"),
    "協働": ("チームで協力できること", "周囲と協力しながら、チームで成果を目指せる環境を重視する"),
    "信頼関係": ("信頼関係のある組織", "互いに尊重し、安心して相談や意見交換ができる組織を重視する"),
    "創造性": ("新しい発想を活かせること", "改善案や新しいアイデアを提案し、形にできる環境を重視する"),
    "誠実さ": ("誠実な組織運営", "顧客や社員に対して誠実で、説明責任を大切にする組織を重視する"),
}

ENVIRONMENT_AXIS_TEMPLATES: dict[str, tuple[str, str]] = {
    "周囲と相談しながら進められる": ("相談しやすい環境", "困ったときに周囲へ相談し、協力しながら仕事を進められる環境を重視する"),
    "役割や期待される成果が明確である": ("役割と期待が明確なこと", "担当する役割と期待される成果が明確な環境を重視する"),
    "自分で考えて行動できる": ("裁量を持って働けること", "目的に沿って自分で考え、行動を選択できる環境を重視する"),
    "定期的にフィードバックを受けられる": ("適切なフィードバック", "定期的に振り返りや助言を受け、改善につなげられる環境を重視する"),
    "チームで協力して進められる": ("協力して成果を出せること", "個人だけでなく、チームで協力して成果を目指せる環境を重視する"),
    "一人で集中する時間が確保されている": ("集中できる時間の確保", "必要な場面で一人で集中し、落ち着いて業務へ取り組める環境を重視する"),
    "新しい挑戦や変化が多い": ("変化と挑戦があること", "新しい課題や変化に継続的に関われる環境を重視する"),
    "手順や進め方がある程度整っている": ("業務の進め方が整っていること", "必要な手順や役割分担が整備され、安定して仕事を進められる環境を重視する"),
    "多様な立場の人と関われる": ("多様な人と関われること", "異なる立場や専門性を持つ人と関わりながら働ける環境を重視する"),
    "自分の専門性や経験を活かせる": ("経験を活かせること", "これまで培った経験や専門性を活かして貢献できる仕事を重視する"),
    "長期的な視点で仕事に取り組める": ("長期的に取り組める仕事", "短期成果だけでなく、長期的な改善や成長に取り組める環境を重視する"),
    "自分の意見や提案を伝えやすい": ("意見や提案を伝えやすいこと", "立場にかかわらず、改善案や意見を伝えやすい組織を重視する"),
    "必要な教育や支援を受けられる": ("教育と支援があること", "業務に必要な教育や支援を受けながら、安心して成長できる環境を重視する"),
}

PRIORITY_WEIGHTS = {"must": 3, "want": 2, "acceptable": 1}


def _ranking_value(ranking: WorkValueRanking) -> str:
    if ranking.selected_value == "その他" and ranking.custom_value:
        return ranking.custom_value.strip()
    return ranking.selected_value.strip()


def _axis_from_ranking(
    rankings: list[WorkValueRanking],
    question_type: str,
    templates: dict[str, tuple[str, str]],
) -> JobHuntingAxis | None:
    targets = sorted(
        (item for item in rankings if item.question_type == question_type),
        key=lambda item: item.priority_rank,
    )
    if not targets:
        return None
    value = _ranking_value(targets[0])
    title, description = templates.get(
        value,
        (value[:50], f"「{value}」を実現できる仕事内容や組織環境を重視する"),
    )
    return JobHuntingAxis(title, description, 1, "suggested")


def _hope_axis(
    hope_condition: HopeCondition | None,
    items: list[HopeConditionItem],
) -> JobHuntingAxis | None:
    if hope_condition is None:
        return None

    parts: list[str] = []
    locations = [
        item.condition_value
        for item in sorted(items, key=lambda item: item.rank or 99)
        if item.condition_type == "location"
        and PRIORITY_WEIGHTS.get(item.priority, 0) >= 2
    ]
    if locations:
        parts.append(f"勤務地は{'、'.join(locations[:2])}")
    if PRIORITY_WEIGHTS.get(hope_condition.commute_priority, 0) >= 2:
        parts.append(f"電車移動は片道{hope_condition.commute_minutes}分以内")
    if PRIORITY_WEIGHTS.get(hope_condition.annual_holiday_priority, 0) >= 2:
        parts.append(f"年間休日{hope_condition.annual_holidays}日以上")
    if PRIORITY_WEIGHTS.get(hope_condition.overtime_priority, 0) >= 2:
        parts.append(f"残業は月{hope_condition.overtime_limit}時間以内")

    if not parts:
        return None

    return JobHuntingAxis(
        "希望する働き方との両立",
        "、".join(parts[:3]) + "を重視する",
        1,
        "suggested",
    )


def suggest_job_hunting_axes() -> list[JobHuntingAxis]:
    """希望条件・価値観から、確認前の軸候補を最大3件作る。"""

    hope_condition, hope_items = load_hope_conditions_data()
    rankings, _, _ = load_work_values_data()

    candidates = [
        _axis_from_ranking(
            rankings,
            QUESTION_IMPORTANT_VALUE,
            VALUE_AXIS_TEMPLATES,
        ),
        _hope_axis(hope_condition, hope_items),
        _axis_from_ranking(
            rankings,
            QUESTION_STRENGTH_ENVIRONMENT,
            ENVIRONMENT_AXIS_TEMPLATES,
        ),
        _axis_from_ranking(
            rankings,
            QUESTION_REWARDING_SCENE,
            {},
        ),
    ]

    unique_axes: list[JobHuntingAxis] = []
    used_titles: set[str] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        key = candidate.axis_title.casefold()
        if key in used_titles:
            continue
        used_titles.add(key)
        unique_axes.append(candidate)
        if len(unique_axes) == 3:
            break

    return [
        JobHuntingAxis(
            axis_title=axis.axis_title,
            axis_description=axis.axis_description,
            priority_rank=index,
            source_type=axis.source_type,
        )
        for index, axis in enumerate(unique_axes, start=1)
    ]