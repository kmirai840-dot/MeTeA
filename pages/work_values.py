"""価値観入力画面。"""

import streamlit as st

from constants.work_values import (
    IMPORTANT_VALUE_OPTIONS,
    MAX_ENVIRONMENT_REASON_LENGTH,
    MAX_REWARDING_EXPERIENCE_LENGTH,
    REWARDING_SCENE_OPTIONS,
    STRENGTH_ENVIRONMENT_OPTIONS,
    WORK_STYLE_SCORE_LABELS,
    WORK_STYLE_SCORE_NEUTRAL,
    WORK_STYLE_QUESTIONS,
)
from pages.self_discovery_theme import apply_self_discovery_theme

from services.work_values_service import (
    load_work_values_data,
    load_work_values_draft,
    save_work_values_data,
    save_work_values_draft,
)

from models import (
    WorkStyleAnswer,
    WorkValueDetail,
    WorkValueRanking,
)

PAGE_TITLE = "価値観"
WORK_VALUES_LOADED_KEY = "work_values_loaded"


def initialize_work_values_state() -> None:
    """一時保存または正式保存済み回答を画面へ復元する。"""

    if st.session_state.get(
        WORK_VALUES_LOADED_KEY
    ):
        return

    draft_data = load_work_values_draft()

    if draft_data:
        for key, value in draft_data.items():
            st.session_state[key] = value

    else:
        rankings, details, work_style_answers = (
            load_work_values_data()
        )

        for ranking in rankings:
            ranking_key = (
                f"{ranking.question_type}_"
                f"{ranking.priority_rank}"
            )

            st.session_state[ranking_key] = (
                ranking.selected_value
            )

            if ranking.custom_value:
                custom_key = (
                    f"{ranking.question_type}_"
                    f"{ranking.priority_rank}_custom"
                )

                st.session_state[custom_key] = (
                    ranking.custom_value
                )

        for detail in details:
            st.session_state[
                detail.detail_type
            ] = detail.detail_text

        for answer in work_style_answers:
            state_key = (
                f"work_style_{answer.question_type}"
            )

            st.session_state[state_key] = (
                answer.answer_score
            )

    st.session_state[WORK_VALUES_LOADED_KEY] = True


def collect_work_values_draft() -> dict[str, object]:
    """現在の入力内容を一時保存用データへ変換する。"""

    draft_data: dict[str, object] = {}

    ranking_prefixes = [
        "important_value",
        "rewarding_scene",
        "strength_environment",
    ]

    for key_prefix in ranking_prefixes:
        for priority_rank in range(1, 4):
            ranking_key = (
                f"{key_prefix}_{priority_rank}"
            )
            custom_key = (
                f"{key_prefix}_{priority_rank}_custom"
            )

            draft_data[ranking_key] = (
                st.session_state.get(ranking_key)
            )
            draft_data[custom_key] = (
                st.session_state.get(
                    custom_key,
                    "",
                )
            )

    draft_data["rewarding_experience"] = (
        st.session_state.get(
            "rewarding_experience",
            "",
        )
    )

    draft_data["environment_reason"] = (
        st.session_state.get(
            "environment_reason",
            "",
        )
    )

    for question in WORK_STYLE_QUESTIONS:
        question_type = question["question_type"]
        state_key = f"work_style_{question_type}"

        draft_data[state_key] = (
            st.session_state.get(
                state_key,
                WORK_STYLE_SCORE_NEUTRAL,
            )
        )

    return draft_data


def ranking_section(
    title: str,
    options: list[str],
    key_prefix: str,
) -> None:
    """候補を一覧表示し、クリック順で最大3件の順位を付ける。"""

    option_icons = {
        "納得感": "◎", "成長": "↗", "安定": "◇", "挑戦": "⚑",
        "人や社会への貢献": "♡", "専門性": "◆", "自律性": "◈",
        "公平性": "⚖", "協働": "∞", "信頼関係": "○", "創造性": "✦",
        "誠実さ": "✓", "その他": "＋",
    }

    selected_values = [
        st.session_state.get(f"{key_prefix}_{rank}")
        for rank in range(1, 4)
    ]
    selected_values = [value for value in selected_values if value]

    with st.container(border=True):
        st.subheader(title)
        st.caption(
            "候補を選ぶと、選んだ順に1位・2位・3位として登録されます。"
        )

        for row_start in range(0, len(options), 3):
            option_columns = st.columns(3)
            for offset, option in enumerate(
                options[row_start:row_start + 3]
            ):
                with option_columns[offset]:
                    selected_rank = (
                        selected_values.index(option) + 1
                        if option in selected_values
                        else None
                    )
                    icon = option_icons.get(option, "○")
                    label = (
                        f"{selected_rank}位　{icon}　{option}"
                        if selected_rank
                        else f"{icon}　{option}"
                    )
                    disabled = (
                        len(selected_values) >= 3
                        and selected_rank is None
                    )
                    if st.button(
                        label,
                        key=f"{key_prefix}_option_{row_start + offset}",
                        type="primary" if selected_rank else "secondary",
                        disabled=disabled,
                        use_container_width=True,
                    ):
                        updated_values = list(selected_values)
                        if option in updated_values:
                            updated_values.remove(option)
                        else:
                            updated_values.append(option)

                        for rank in range(1, 4):
                            st.session_state[f"{key_prefix}_{rank}"] = (
                                updated_values[rank - 1]
                                if rank <= len(updated_values)
                                else None
                            )
                        st.rerun()

        if selected_values:
            st.markdown("#### 選択中の順位")
            st.caption("▲・▼で順位を入れ替えられます。解除後は別の候補を選べます。")
            rank_columns = st.columns(len(selected_values))
            for rank_index, value in enumerate(selected_values):
                with rank_columns[rank_index]:
                    with st.container(border=True):
                        st.markdown(
                            f"<div class='metea-selected-rank'><span>{rank_index + 1}位</span>"
                            f"<strong>{value}</strong></div>",
                            unsafe_allow_html=True,
                        )
                        controls = st.columns([1, 1, 1.4])
                        with controls[0]:
                            if st.button(
                                "▲",
                                key=f"{key_prefix}_rank_up_{rank_index}",
                                disabled=rank_index == 0,
                                use_container_width=True,
                            ):
                                updated_values = list(selected_values)
                                updated_values[rank_index - 1], updated_values[rank_index] = (
                                    updated_values[rank_index], updated_values[rank_index - 1]
                                )
                                for rank in range(1, 4):
                                    st.session_state[f"{key_prefix}_{rank}"] = (
                                        updated_values[rank - 1]
                                        if rank <= len(updated_values) else None
                                    )
                                st.rerun()
                        with controls[1]:
                            if st.button(
                                "▼",
                                key=f"{key_prefix}_rank_down_{rank_index}",
                                disabled=rank_index == len(selected_values) - 1,
                                use_container_width=True,
                            ):
                                updated_values = list(selected_values)
                                updated_values[rank_index + 1], updated_values[rank_index] = (
                                    updated_values[rank_index], updated_values[rank_index + 1]
                                )
                                for rank in range(1, 4):
                                    st.session_state[f"{key_prefix}_{rank}"] = (
                                        updated_values[rank - 1]
                                        if rank <= len(updated_values) else None
                                    )
                                st.rerun()
                        with controls[2]:
                            if st.button(
                                "解除",
                                key=f"{key_prefix}_rank_remove_{rank_index}",
                                use_container_width=True,
                            ):
                                updated_values = [
                                    item for item in selected_values if item != value
                                ]
                                for rank in range(1, 4):
                                    st.session_state[f"{key_prefix}_{rank}"] = (
                                        updated_values[rank - 1]
                                        if rank <= len(updated_values) else None
                                    )
                                st.rerun()

        if "その他" in selected_values:
            custom_rank = selected_values.index("その他") + 1
            st.text_input(
                "その他の内容",
                max_chars=100,
                placeholder="具体的な内容を入力",
                key=f"{key_prefix}_{custom_rank}_custom",
            )

def text_detail_section(
    title: str,
    description: str,
    key: str,
    max_length: int,
    placeholder: str,
) -> None:
    """価値観に関する自由記述欄を表示する。"""

    with st.container(border=True):
        st.subheader(title)
        st.caption(description)
        st.text_area(
            "回答",
            key=key,
            height=120,
            max_chars=max_length,
            placeholder=placeholder,
            label_visibility="collapsed",
        )
        st.caption(f"最大{max_length}文字まで入力できます。")

def work_style_section() -> None:
    """仕事の進め方に関する5段階評価を表示する。"""

    st.subheader("仕事の進め方")
    st.caption("左右の考え方を見比べ、自分に近い数字を選択してください。")

    for question in WORK_STYLE_QUESTIONS:
        with st.container(border=True):
            st.markdown(f"### {question['title']}")
            endpoint_columns = st.columns([3.2, 4.6, 3.2], vertical_alignment="center")
            endpoint_columns[0].markdown(
                f"<div class='metea-scale-end metea-scale-end--left'><span>1</span>"
                f"<strong>{question['left_text']}</strong></div>",
                unsafe_allow_html=True,
            )
            with endpoint_columns[1]:
                score = st.radio(
                    label=f"{question['title']}の回答",
                    options=[1, 2, 3, 4, 5],
                    horizontal=True,
                    key=f"work_style_{question['question_type']}",
                    index=WORK_STYLE_SCORE_NEUTRAL - 1,
                    format_func=lambda value: str(value),
                    label_visibility="collapsed",
                )
                st.markdown(
                    f"<p class='metea-scale-caption'>{WORK_STYLE_SCORE_LABELS[score]}</p>",
                    unsafe_allow_html=True,
                )
            endpoint_columns[2].markdown(
                f"<div class='metea-scale-end metea-scale-end--right'>"
                f"<strong>{question['right_text']}</strong><span>5</span></div>",
                unsafe_allow_html=True,
            )

def show_page() -> None:
    """価値観入力画面を表示する。"""

    apply_self_discovery_theme(current_step=3)

    initialize_work_values_state()

    if st.button(
        "← 希望条件へ戻る",
        key="work_values_back_top",
    ):
        st.query_params["page"] = "hope_conditions"
        st.rerun()

    st.title("価値観")

    st.caption(
        "あなたが仕事で大切にしたいことや、"
        "力を発揮しやすい環境を整理します。"
    )

    st.progress(
        3 / 5,
        text="自分を知る 3 / 5　価値観",
    )

    st.divider()

    st.info(
        "まずは直感で回答してください。"
        "あとから何度でも変更できます。"
    )

    ranking_section(
        title="仕事で大切にしたいこと",
        options=IMPORTANT_VALUE_OPTIONS,
        key_prefix="important_value",
    )

    ranking_section(
        title="やりがいを感じる場面",
        options=REWARDING_SCENE_OPTIONS,
        key_prefix="rewarding_scene",
    )

    text_detail_section(
        title="実際にやりがいを感じた経験",
        description=(
            "選択した内容に関連する出来事を、"
            "具体的に振り返ってみましょう。"
        ),
        key="rewarding_experience",
        max_length=MAX_REWARDING_EXPERIENCE_LENGTH,
        placeholder=(
            "例：業務改善によって作業時間を短縮し、"
            "利用者から感謝された経験"
        ),
    )

    ranking_section(
        title="力を発揮しやすい環境",
        options=STRENGTH_ENVIRONMENT_OPTIONS,
        key_prefix="strength_environment",
    )

    text_detail_section(
        title="その環境で力を発揮できると思う理由",
        description=(
            "過去の経験や、自分の仕事の進め方をもとに"
            "入力してください。"
        ),
        key="environment_reason",
        max_length=MAX_ENVIRONMENT_REASON_LENGTH,
        placeholder=(
            "例：期待される役割が明確だと、"
            "優先順位を整理して行動しやすいため"
        ),
    )

    work_style_section()

    st.divider()

    action_columns = st.columns(3)

    with action_columns[0]:
        if st.button(
            "← 希望条件へ戻る",
            key="work_values_back_bottom",
            use_container_width=True,
        ):
            st.query_params["page"] = "hope_conditions"
            st.rerun()

    with action_columns[1]:
        if st.button(
            "一時保存",
            key="work_values_draft_save",
            use_container_width=True,
        ):
            try:
                draft_data = (
                    collect_work_values_draft()
                )

                save_work_values_draft(
                    draft_data
                )

                st.success(
                    "入力内容を一時保存しました。"
                )

            except Exception as error:
                st.error(
                    "一時保存に失敗しました。"
                    f"\n\n{error}"
                )

    with action_columns[2]:
        if st.button(
            "保存して次へ →",
            key="work_values_save",
            type="primary",
            use_container_width=True,
        ):
            rankings: list[WorkValueRanking] = []

            ranking_groups = [
                (
                    "important_value",
                    IMPORTANT_VALUE_OPTIONS,
                ),
                (
                    "rewarding_scene",
                    REWARDING_SCENE_OPTIONS,
                ),
                (
                    "strength_environment",
                    STRENGTH_ENVIRONMENT_OPTIONS,
                ),
            ]

            for question_type, _ in ranking_groups:
                for priority_rank in range(1, 4):
                    selected_value = st.session_state.get(
                        f"{question_type}_{priority_rank}"
                    )

                    if selected_value:
                        custom_value = None

                        if selected_value == "その他":
                            custom_value = st.session_state.get(
                                (
                                    f"{question_type}_"
                                    f"{priority_rank}_custom"
                                ),
                                "",
                            )

                        rankings.append(
                            WorkValueRanking(
                                question_type=question_type,
                                selected_value=selected_value,
                                priority_rank=priority_rank,
                                custom_value=custom_value,
                            )
                        )

            details = [
                WorkValueDetail(
                    detail_type="rewarding_experience",
                    detail_text=st.session_state.get(
                        "rewarding_experience",
                        "",
                    ),
                ),
                WorkValueDetail(
                    detail_type="environment_reason",
                    detail_text=st.session_state.get(
                        "environment_reason",
                        "",
                    ),
                ),
            ]

            work_style_answers: list[WorkStyleAnswer] = []

            for question in WORK_STYLE_QUESTIONS:
                work_style_answers.append(
                    WorkStyleAnswer(
                        question_type=question[
                            "question_type"
                        ],
                        answer_score=st.session_state.get(
                            (
                                "work_style_"
                                f"{question['question_type']}"
                            ),
                            WORK_STYLE_SCORE_NEUTRAL,
                        ),
                    )
                )

            save_errors = save_work_values_data(
                rankings=rankings,
                details=details,
                work_style_answers=work_style_answers,
            )

            if save_errors:
                for error in save_errors:
                    st.error(error)

            else:
                st.session_state.pop("job_hunting_axes_loaded", None)
                st.session_state.pop("job_hunting_axes", None)
                st.query_params["page"] = "job_hunting_axis"
                st.rerun()