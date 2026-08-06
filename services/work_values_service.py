"""価値観回答の入力確認・保存・取得を担当する。"""

from collections import defaultdict

from constants.work_values import (
    DETAIL_ENVIRONMENT_REASON,
    DETAIL_REWARDING_EXPERIENCE,
    IMPORTANT_VALUE_OPTIONS,
    MAX_ENVIRONMENT_REASON_LENGTH,
    MAX_OTHER_TEXT_LENGTH,
    MAX_RANKING_SELECTIONS,
    MAX_REWARDING_EXPERIENCE_LENGTH,
    QUESTION_IMPORTANT_VALUE,
    QUESTION_REWARDING_SCENE,
    QUESTION_STRENGTH_ENVIRONMENT,
    REWARDING_SCENE_OPTIONS,
    STRENGTH_ENVIRONMENT_OPTIONS,
    WORK_STYLE_QUESTIONS,
    WORK_STYLE_SCORE_MAX,
    WORK_STYLE_SCORE_MIN,
    WORK_VALUES_FORM_NAME,
)
from database.repositories.draft_repository import (
    get_draft,
    save_draft,
)
from database.repositories.work_values_repository import (
    get_work_values,
    save_work_values,
)
from models import (
    WorkStyleAnswer,
    WorkValueDetail,
    WorkValueRanking,
)
from services.current_user_service import get_current_user_id


RANKING_OPTION_MAP = {
    QUESTION_IMPORTANT_VALUE: IMPORTANT_VALUE_OPTIONS,
    QUESTION_REWARDING_SCENE: REWARDING_SCENE_OPTIONS,
    QUESTION_STRENGTH_ENVIRONMENT: STRENGTH_ENVIRONMENT_OPTIONS,
}

RANKING_QUESTION_LABELS = {
    QUESTION_IMPORTANT_VALUE: "仕事で大切にしたいこと",
    QUESTION_REWARDING_SCENE: "やりがいを感じる場面",
    QUESTION_STRENGTH_ENVIRONMENT: "力を発揮しやすい環境",
}

DETAIL_MAX_LENGTH_MAP = {
    DETAIL_REWARDING_EXPERIENCE: MAX_REWARDING_EXPERIENCE_LENGTH,
    DETAIL_ENVIRONMENT_REASON: MAX_ENVIRONMENT_REASON_LENGTH,
}

DETAIL_LABELS = {
    DETAIL_REWARDING_EXPERIENCE: "やりがいを感じた経験",
    DETAIL_ENVIRONMENT_REASON: "力を発揮できる理由",
}

REQUIRED_WORK_STYLE_TYPES = {
    question["question_type"]
    for question in WORK_STYLE_QUESTIONS
}


def validate_rankings(
    rankings: list[WorkValueRanking],
) -> tuple[list[WorkValueRanking] | None, list[str]]:
    """順位付き回答を確認し、保存用データへ整える。"""

    errors: list[str] = []
    grouped_rankings: dict[str, list[WorkValueRanking]] = defaultdict(list)

    for ranking in rankings:
        grouped_rankings[ranking.question_type].append(ranking)

    validated_rankings: list[WorkValueRanking] = []

    for question_type, allowed_options in RANKING_OPTION_MAP.items():
        question_label = RANKING_QUESTION_LABELS[question_type]
        question_rankings = grouped_rankings.get(
            question_type,
            [],
        )

        if len(question_rankings) != MAX_RANKING_SELECTIONS:
            errors.append(
                f"「{question_label}」は"
                f"{MAX_RANKING_SELECTIONS}件選択してください。"
            )
            continue

        selected_values: list[str] = []
        priority_ranks: list[int] = []

        for ranking in question_rankings:
            selected_value = ranking.selected_value.strip()
            custom_value = (
                ranking.custom_value.strip()
                if ranking.custom_value
                else None
            )

            if selected_value not in allowed_options:
                errors.append(
                    f"「{question_label}」に"
                    "選択できない回答が含まれています。"
                )
                continue

            if selected_value in selected_values:
                errors.append(
                    f"「{question_label}」で"
                    f"「{selected_value}」が重複しています。"
                )

            selected_values.append(selected_value)
            priority_ranks.append(ranking.priority_rank)

            if selected_value == "その他":
                if not custom_value:
                    errors.append(
                        f"「{question_label}」の"
                        "「その他」の内容を入力してください。"
                    )
                elif len(custom_value) > MAX_OTHER_TEXT_LENGTH:
                    errors.append(
                        f"「{question_label}」の"
                        f"「その他」は{MAX_OTHER_TEXT_LENGTH}文字以内で"
                        "入力してください。"
                    )
            else:
                custom_value = None

            validated_rankings.append(
                WorkValueRanking(
                    question_type=question_type,
                    selected_value=selected_value,
                    priority_rank=ranking.priority_rank,
                    custom_value=custom_value,
                )
            )

        expected_ranks = list(
            range(
                1,
                MAX_RANKING_SELECTIONS + 1,
            )
        )

        if sorted(priority_ranks) != expected_ranks:
            errors.append(
                f"「{question_label}」の順位を"
                "1位から3位まで設定してください。"
            )

    unexpected_types = (
        set(grouped_rankings)
        - set(RANKING_OPTION_MAP)
    )

    if unexpected_types:
        errors.append(
            "認識できない価値観質問が含まれています。"
        )

    if errors:
        return None, errors

    validated_rankings.sort(
        key=lambda ranking: (
            ranking.question_type,
            ranking.priority_rank,
        )
    )

    return validated_rankings, []


def validate_details(
    details: list[WorkValueDetail],
) -> tuple[list[WorkValueDetail] | None, list[str]]:
    """自由記述回答を確認し、保存用データへ整える。"""

    errors: list[str] = []
    validated_details: list[WorkValueDetail] = []
    registered_types: set[str] = set()

    for detail in details:
        if detail.detail_type not in DETAIL_MAX_LENGTH_MAP:
            errors.append(
                "認識できない自由記述項目が含まれています。"
            )
            continue

        if detail.detail_type in registered_types:
            errors.append(
                f"「{DETAIL_LABELS[detail.detail_type]}」が"
                "重複しています。"
            )
            continue

        detail_text = detail.detail_text.strip()
        max_length = DETAIL_MAX_LENGTH_MAP[detail.detail_type]

        if len(detail_text) > max_length:
            errors.append(
                f"「{DETAIL_LABELS[detail.detail_type]}」は"
                f"{max_length}文字以内で入力してください。"
            )

        registered_types.add(detail.detail_type)

        validated_details.append(
            WorkValueDetail(
                detail_type=detail.detail_type,
                detail_text=detail_text,
            )
        )

    if errors:
        return None, errors

    return validated_details, []


def validate_work_style_answers(
    answers: list[WorkStyleAnswer],
) -> tuple[list[WorkStyleAnswer] | None, list[str]]:
    """仕事の進め方への回答を確認する。"""

    errors: list[str] = []
    validated_answers: list[WorkStyleAnswer] = []
    registered_types: set[str] = set()

    for answer in answers:
        if answer.question_type not in REQUIRED_WORK_STYLE_TYPES:
            errors.append(
                "認識できない仕事の進め方の質問が含まれています。"
            )
            continue

        if answer.question_type in registered_types:
            errors.append(
                "仕事の進め方の回答が重複しています。"
            )
            continue

        if not (
            WORK_STYLE_SCORE_MIN
            <= answer.answer_score
            <= WORK_STYLE_SCORE_MAX
        ):
            errors.append(
                "仕事の進め方は1から5の範囲で回答してください。"
            )
            continue

        registered_types.add(answer.question_type)

        validated_answers.append(
            WorkStyleAnswer(
                question_type=answer.question_type,
                answer_score=answer.answer_score,
            )
        )

    missing_types = (
        REQUIRED_WORK_STYLE_TYPES
        - registered_types
    )

    if missing_types:
        errors.append(
            "仕事の進め方の質問すべてに回答してください。"
        )

    if errors:
        return None, errors

    question_order = {
        question["question_type"]: index
        for index, question in enumerate(
            WORK_STYLE_QUESTIONS
        )
    }

    validated_answers.sort(
        key=lambda answer: question_order[
            answer.question_type
        ]
    )

    return validated_answers, []


def save_work_values_data(
    rankings: list[WorkValueRanking],
    details: list[WorkValueDetail],
    work_style_answers: list[WorkStyleAnswer],
) -> list[str]:
    """価値観回答を確認して正式保存する。"""

    validated_rankings, ranking_errors = validate_rankings(
        rankings
    )

    validated_details, detail_errors = validate_details(
        details
    )

    validated_answers, answer_errors = (
        validate_work_style_answers(
            work_style_answers
        )
    )

    errors = (
        ranking_errors
        + detail_errors
        + answer_errors
    )

    if errors:
        return errors

    if (
        validated_rankings is None
        or validated_details is None
        or validated_answers is None
    ):
        return [
            "価値観の保存データを作成できませんでした。"
        ]

    save_work_values(
        user_id=get_current_user_id(),
        rankings=validated_rankings,
        details=validated_details,
        work_style_answers=validated_answers,
        draft_form_name=WORK_VALUES_FORM_NAME,
    )

    return []


def load_work_values_data(
) -> tuple[
    list[WorkValueRanking],
    list[WorkValueDetail],
    list[WorkStyleAnswer],
]:
    """正式保存済みの価値観回答を取得する。"""

    return get_work_values(
        get_current_user_id()
    )


def save_work_values_draft(
    draft_data: dict[str, object],
) -> None:
    """価値観画面の入力途中データを保存する。"""

    save_draft(
        user_id=get_current_user_id(),
        form_name=WORK_VALUES_FORM_NAME,
        draft_data=draft_data,
    )


def load_work_values_draft(
) -> dict[str, object] | None:
    """価値観画面の入力途中データを取得する。"""

    return get_draft(
        user_id=get_current_user_id(),
        form_name=WORK_VALUES_FORM_NAME,
    )