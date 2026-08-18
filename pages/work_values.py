"""価値観入力画面。"""

import base64
from html import escape
from pathlib import Path

import streamlit as st

from constants.work_values import (
    IMPORTANT_VALUE_OPTIONS,
    REWARDING_SCENE_OPTIONS,
    STRENGTH_ENVIRONMENT_OPTIONS,
    WORK_STYLE_SCORE_LABELS,
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


VALUE_ICON_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def _value_icon_slug(option: str) -> str:
    """選択肢の意味に合う共通アイコン名を返す。"""

    keyword_icons = (
        (("その他",), "plus"),
        (("成長", "知識", "技術", "教育", "支援"), "growth"),
        (("安定", "長期", "手順", "整って"), "shield"),
        (("挑戦", "変化", "難しい"), "challenge"),
        (("貢献", "感謝", "顧客", "利用者"), "heart"),
        (("専門", "経験を活か", "責任"), "expertise"),
        (("自律", "自分で考", "集中"), "autonomy"),
        (("公平", "正確"), "balance"),
        (("協働", "チーム", "多様", "相談"), "team"),
        (("信頼", "フィードバック"), "trust"),
        (("創造", "新しい仕組み", "提案", "効率化"), "idea"),
        (("誠実", "達成", "明確"), "check"),
    )
    for keywords, slug in keyword_icons:
        if any(keyword in option for keyword in keywords):
            return slug
    return "compass"


def _value_icon_data_uri(slug: str) -> str:
    """assets内のSVGをCSS用のdata URIへ変換する。"""

    return _asset_data_uri(f"value-{slug}.svg")


def _asset_data_uri(filename: str) -> str:
    """assets内のSVGファイルをdata URIへ変換する。"""

    svg = (VALUE_ICON_ASSET_DIR / filename).read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")


def _update_ranking_values(
    key_prefix: str,
    current_values: list[str],
    updated_values: list[str],
) -> None:
    """順位と「その他」の入力値を一体で安全に更新する。"""

    custom_values = {
        value: st.session_state.get(f"{key_prefix}_{rank}_custom", "")
        for rank, value in enumerate(current_values, start=1)
        if value == "その他"
    }
    for rank in range(1, 4):
        st.session_state.pop(f"{key_prefix}_{rank}_custom", None)
        st.session_state[f"{key_prefix}_{rank}"] = (
            updated_values[rank - 1]
            if rank <= len(updated_values)
            else None
        )
    for rank, value in enumerate(updated_values, start=1):
        if value == "その他" and custom_values.get(value):
            st.session_state[f"{key_prefix}_{rank}_custom"] = custom_values[value]
    st.session_state[WORK_VALUES_EDITING_KEY] = True
    save_work_values_draft(collect_work_values_draft())


def _move_ranking_value(
    key_prefix: str,
    current_values: list[str],
    rank_index: int,
    direction: int,
) -> None:
    """選択済み項目の順位を一つ移動する。"""

    updated_values = list(current_values)
    target_index = rank_index + direction
    if not 0 <= target_index < len(updated_values):
        return
    updated_values[rank_index], updated_values[target_index] = (
        updated_values[target_index],
        updated_values[rank_index],
    )
    _update_ranking_values(key_prefix, current_values, updated_values)


def _remove_ranking_value(
    key_prefix: str,
    current_values: list[str],
    value: str,
) -> None:
    """指定した項目を選択順位から外す。"""

    updated_values = [item for item in current_values if item != value]
    _update_ranking_values(key_prefix, current_values, updated_values)


def _clear_ranking_values(key_prefix: str, current_values: list[str]) -> None:
    """対象ブロックの選択順位をすべて解除する。"""

    _update_ranking_values(key_prefix, current_values, [])

PAGE_TITLE = "価値観"
WORK_VALUES_LOADED_KEY = "work_values_loaded"
WORK_VALUES_ERRORS_KEY = "work_values_validation_errors"
WORK_VALUES_EDITING_KEY = "work_values_editing_in_session"

REWARDING_EXPERIENCE_FIELDS = (
    (
        "rewarding_experience_context",
        "まず、そのときのことを教えてください",
        "いつ頃、どこで、誰と取り組んだ経験ですか？",
        "例：以前の職場で、メンバーと一緒に運用改善へ取り組んだ経験です。",
    ),
    (
        "rewarding_experience_goal",
        "どんなことを良くしたい、または実現したいと思いましたか？",
        "困っていたことや、目指していた状態を教えてください。",
        "例：手順に従うだけではなく、一人ひとりが運用の目的を理解し、納得したうえで自ら改善を考えられる状態を目指しました。",
    ),
    (
        "rewarding_experience_action",
        "そのために、あなたはどんなことをしましたか？",
        "考えたこと、工夫したこと、周囲へ働きかけたことなどを教えてください。",
        "例：手順の背景や目的を共有し、日々の疑問や改善案を話しやすい場をつくりました。また、出た意見を一緒に整理し、運用へ反映しました。",
    ),
    (
        "rewarding_experience_result",
        "取り組んだあと、どんな変化がありましたか？",
        "結果だけでなく、周囲の反応や自分が感じたことでも構いません。",
        "例：メンバーが運用へ疑問を持ち、自分から改善を提案するようになりました。周囲が納得して主体的に動き始める瞬間に、大きなやりがいを感じました。",
    ),
)

ENVIRONMENT_REASON_FIELDS = (
    (
        "environment_reason_working_image",
        "その環境では、どのように仕事を進められそうですか？",
        "安心して動ける、考えを整理しやすい、周囲と連携しやすいなど、働いている自分を想像してみてください。",
        "例：役割や目標が共有されていると、自分で優先順位を整理し、周囲と認識を合わせながら進められます。",
    ),
    (
        "environment_reason_experience",
        "そう思うようになった経験を教えてください",
        "これまでに、仕事を進めやすかった、または力を発揮できたと感じた場面はありますか？",
        "例：目的や期待される成果が明確な業務では、自分から改善案を考え、周囲へ提案できました。",
    ),
    (
        "environment_reason_strength",
        "その環境で、どんな自分の良さを活かせそうですか？",
        "得意なこと、仕事の進め方、周囲との関わり方などを教えてください。",
        "例：相手の考えを整理し、納得できる進め方を一緒につくる力を活かせると思います。",
    ),
)


def _compose_rewarding_experience() -> str:
    """4つの対話回答を既存DBへ保存できる文章にまとめる。"""

    sections = []
    for key, label, _, _ in REWARDING_EXPERIENCE_FIELDS:
        value = str(st.session_state.get(key, "")).strip()
        if value:
            sections.append(f"【{label}】\n{value}")
    return "\n\n".join(sections)


def _initialize_rewarding_experience_fields() -> None:
    """既存の自由記述を新しい分割入力欄へ安全に引き継ぐ。"""

    if any(key in st.session_state for key, *_ in REWARDING_EXPERIENCE_FIELDS):
        return
    existing_text = str(st.session_state.get("rewarding_experience", "")).strip()
    if not existing_text:
        return
    parsed = False
    for index, (key, label, _, _) in enumerate(REWARDING_EXPERIENCE_FIELDS):
        marker = f"【{label}】"
        if marker not in existing_text:
            continue
        start = existing_text.index(marker) + len(marker)
        end = len(existing_text)
        for _, next_label, _, _ in REWARDING_EXPERIENCE_FIELDS[index + 1:]:
            next_marker = f"【{next_label}】"
            next_position = existing_text.find(next_marker, start)
            if next_position >= 0:
                end = min(end, next_position)
        st.session_state[key] = existing_text[start:end].strip()
        parsed = True
    if not parsed:
        st.session_state[REWARDING_EXPERIENCE_FIELDS[0][0]] = existing_text


def _compose_environment_reason() -> str:
    """環境に関する3つの回答を既存DB用の文章へまとめる。"""

    sections = []
    for key, label, _, _ in ENVIRONMENT_REASON_FIELDS:
        value = str(st.session_state.get(key, "")).strip()
        if value:
            sections.append(f"【{label}】\n{value}")
    return "\n\n".join(sections)


def _initialize_environment_reason_fields() -> None:
    """既存の環境理由を新しい分割入力欄へ安全に引き継ぐ。"""

    if any(key in st.session_state for key, *_ in ENVIRONMENT_REASON_FIELDS):
        return
    existing_text = str(st.session_state.get("environment_reason", "")).strip()
    if not existing_text:
        return
    parsed = False
    for index, (key, label, _, _) in enumerate(ENVIRONMENT_REASON_FIELDS):
        marker = f"【{label}】"
        if marker not in existing_text:
            continue
        start = existing_text.index(marker) + len(marker)
        end = len(existing_text)
        for _, next_label, _, _ in ENVIRONMENT_REASON_FIELDS[index + 1:]:
            next_marker = f"【{next_label}】"
            next_position = existing_text.find(next_marker, start)
            if next_position >= 0:
                end = min(end, next_position)
        st.session_state[key] = existing_text[start:end].strip()
        parsed = True
    if not parsed:
        st.session_state[ENVIRONMENT_REASON_FIELDS[0][0]] = existing_text


def initialize_work_values_state() -> None:
    """一時保存または正式保存済み回答を画面へ復元する。"""

    representative_key = (
        f"work_style_{WORK_STYLE_QUESTIONS[0]['question_type']}"
    )
    if (
        st.session_state.get(WORK_VALUES_LOADED_KEY)
        and (
            representative_key in st.session_state
            or st.session_state.get(WORK_VALUES_EDITING_KEY)
        )
    ):
        _initialize_rewarding_experience_fields()
        _initialize_environment_reason_fields()
        return

    if WORK_VALUES_ERRORS_KEY not in st.session_state:
        st.session_state[WORK_VALUES_ERRORS_KEY] = {}

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
    _initialize_rewarding_experience_fields()
    _initialize_environment_reason_fields()


def validate_work_values_form() -> dict[str, str]:
    """価値観画面の必須回答を画面遷移前に検証する。"""

    errors: dict[str, str] = {}
    ranking_groups = (
        ("important_value", "仕事で大切にしたいこと"),
        ("rewarding_scene", "やりがいを感じる場面"),
        ("strength_environment", "力を発揮しやすい環境"),
    )

    for key_prefix, label in ranking_groups:
        selected_values = [
            st.session_state.get(f"{key_prefix}_{rank}")
            for rank in range(1, 4)
        ]
        selected_values = [value for value in selected_values if value]

        if len(selected_values) != 3:
            errors[key_prefix] = f"「{label}」を3件選択してください"

        if "その他" in selected_values:
            custom_rank = selected_values.index("その他") + 1
            custom_key = f"{key_prefix}_{custom_rank}_custom"
            if not (st.session_state.get(custom_key, "") or "").strip():
                errors[custom_key] = f"「{label}」のその他の内容を入力してください"

    unanswered_work_style_keys = []
    for question in WORK_STYLE_QUESTIONS:
        state_key = f"work_style_{question['question_type']}"
        if st.session_state.get(state_key) is None:
            unanswered_work_style_keys.append(state_key)
            errors[state_key] = "回答を選択してください"
    if unanswered_work_style_keys:
        errors["work_style"] = "仕事の進め方の未回答項目を選択してください"

    return errors


def render_work_values_error_summary(errors: dict[str, str]) -> None:
    """基本情報・希望条件と同じ形式でエラー一覧を表示する。"""

    if not errors:
        return

    error_items = "".join(
        f"<li>{escape(message)}</li>"
        for message in dict.fromkeys(errors.values())
    )
    st.markdown(
        '<div class="metea-values-error-summary" role="alert">'
        '<span class="metea-values-error-icon">!</span>'
        '<div><strong>入力内容を確認してください</strong>'
        f'<ul>{error_items}</ul></div></div>',
        unsafe_allow_html=True,
    )


def render_work_values_field_error(
    errors: dict[str, str],
    field_key: str,
) -> None:
    """価値観の入力欄直下にエラーを表示する。"""

    message = errors.get(field_key)
    if message:
        st.markdown(
            f'<p class="metea-values-field-error">{escape(message)}</p>',
            unsafe_allow_html=True,
        )


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

    for field_key, *_ in REWARDING_EXPERIENCE_FIELDS:
        draft_data[field_key] = st.session_state.get(field_key, "")
    draft_data["rewarding_experience"] = _compose_rewarding_experience()

    for field_key, *_ in ENVIRONMENT_REASON_FIELDS:
        draft_data[field_key] = st.session_state.get(field_key, "")
    draft_data["environment_reason"] = _compose_environment_reason()

    for question in WORK_STYLE_QUESTIONS:
        question_type = question["question_type"]
        state_key = f"work_style_{question_type}"

        draft_data[state_key] = (
            st.session_state.get(state_key)
        )

    return draft_data


def ranking_section(
    section_number: int,
    title: str,
    options: list[str],
    key_prefix: str,
    errors: dict[str, str],
) -> None:
    """候補を一覧表示し、クリック順で最大3件の順位を付ける。"""

    selected_values = [
        st.session_state.get(f"{key_prefix}_{rank}")
        for rank in range(1, 4)
    ]
    selected_values = [value for value in selected_values if value]

    with st.expander(
        f"{section_number}　{title} :red[*]",
        expanded=(
            key_prefix in errors
            or any(
                key.startswith(f"{key_prefix}_")
                and key.endswith("_custom")
                for key in errors
            )
        ),
    ):
        st.markdown(
            f'<span class="metea-values-ranking-marker '
            f'metea-values-ranking-marker--{key_prefix}" '
            'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.caption(
            "候補を選ぶと、選んだ順に1位・2位・3位として登録されます。"
        )
        render_work_values_field_error(errors, key_prefix)

        icon_rules = []
        for option_index, option in enumerate(options):
            icon_uri = _value_icon_data_uri(_value_icon_slug(option))
            icon_rules.append(
                f'.st-key-{key_prefix}_option_{option_index} button::before'
                "{content:'';display:block;flex:0 0 20px;width:20px;"
                "height:20px;background-position:center;background-repeat:no-repeat;"
                f"background-size:20px 20px;background-image:url('{icon_uri}');"
                "}"
            )
        st.markdown(
            "<style>"
            + "".join(icon_rules)
            + f'[class*="st-key-{key_prefix}_option_"] button'
              "{display:flex;align-items:center;justify-content:flex-start;gap:4px;}"
              f'[class*="st-key-{key_prefix}_option_"] button p'
              "{margin:0;text-align:left;}"
              f'[class*="st-key-{key_prefix}_option_"] button[kind="primary"]'
              "{color:#0f5fd7 !important;background:#eaf3ff !important;"
              "border-color:#8fbdff !important;box-shadow:0 0 0 1px "
              "rgba(20,108,255,.05) !important;}"
              f'[class*="st-key-{key_prefix}_option_"] button[kind="primary"]:hover'
              "{color:#0b55c7 !important;background:#deedff !important;"
              "border-color:#70aaff !important;}"
              f'[class*="st-key-{key_prefix}_option_"] button[kind="primary"] p'
              "{color:#0f5fd7 !important;font-weight:700;}"
              "</style>",
            unsafe_allow_html=True,
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
                    label = (
                        f"{selected_rank}位　{option}"
                        if selected_rank
                        else option
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
                        st.session_state[WORK_VALUES_EDITING_KEY] = True
                        save_work_values_draft(collect_work_values_draft())
                        st.rerun()

        if selected_values:
            rank_up_icon = _asset_data_uri("rank-up.svg")
            rank_down_icon = _asset_data_uri("rank-down.svg")
            rank_remove_icon = _asset_data_uri("rank-remove.svg")
            st.markdown(
                f"""
                <div class="metea-ranking-result-heading">
                    <span class="metea-ranking-result-kicker">選択結果</span>
                    <h4>{escape(title)} TOP3</h4>
                    <p>「上へ」「下へ」で順位を変更し、「外す」で選択を解除できます。</p>
                </div>
                <style>
                .metea-ranking-result-heading {{
                    margin: 18px 0 9px;
                    padding: 14px 17px;
                    border: 1px solid #bdd7ff;
                    border-radius: 12px;
                    background: linear-gradient(100deg, #f1f7ff 0%, #f8fbff 100%);
                }}
                .metea-ranking-result-kicker {{
                    display: inline-flex;
                    align-items: center;
                    min-height: 23px;
                    padding: 0 9px;
                    border-radius: 999px;
                    color: #0f5fd7;
                    background: #dceaff;
                    font-size: .76rem;
                    font-weight: 700;
                    letter-spacing: 0;
                }}
                .metea-ranking-result-heading h4 {{
                    margin: 2px 0 1px;
                    color: #082b59;
                    font-size: 1.08rem;
                }}
                .metea-ranking-result-heading p {{
                    margin: 0;
                    color: #71839a;
                    font-size: .82rem;
                }}
                [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-rank-card) {{
                    padding: 10px 12px !important;
                    border-radius: 11px !important;
                    box-shadow: none !important;
                }}
                [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-rank-card--1) {{
                    border: 1.5px solid #75abff !important;
                    background: #eaf3ff !important;
                }}
                [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-rank-card--2) {{
                    border: 1px solid #b3d2ff !important;
                    background: #f2f7ff !important;
                }}
                [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-rank-card--3) {{
                    border: 1px solid #d2e3fa !important;
                    background: #f8fbff !important;
                }}
                .metea-rank-card {{
                    display: flex;
                    align-items: center;
                    min-height: 40px;
                    gap: 11px;
                }}
                .metea-rank-card img {{ width: 26px; height: 26px; }}
                .metea-rank-number {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    min-width: 44px;
                    height: 27px;
                    padding: 0 8px;
                    border-radius: 999px;
                    color: #fff;
                    background: #146cff;
                    font-size: .78rem;
                    font-weight: 800;
                }}
                .metea-rank-card--2 .metea-rank-number {{ background: #4b8df5; }}
                .metea-rank-card--3 .metea-rank-number {{
                    color: #2364b8;
                    background: #dceaff;
                }}
                .metea-rank-value {{
                    color: #082b59;
                    font-size: .98rem;
                    font-weight: 750;
                }}
                [class*="st-key-{key_prefix}_rank_up_"] button,
                [class*="st-key-{key_prefix}_rank_down_"] button,
                [class*="st-key-{key_prefix}_rank_remove_"] button {{
                    width: 74px !important;
                    min-width: 0 !important;
                    max-width: 74px !important;
                    height: 36px !important;
                    min-height: 36px !important;
                    margin: 0 auto !important;
                    padding: 0 8px !important;
                    border-color: #8fbaff !important;
                    border-radius: 9px !important;
                    background: #edf5ff !important;
                    box-shadow: 0 1px 3px rgba(20,108,255,.08) !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                    gap: 3px !important;
                }}
                [class*="st-key-{key_prefix}_rank_up_"] button:hover,
                [class*="st-key-{key_prefix}_rank_down_"] button:hover {{
                    border-color: #76aaff !important;
                    background: #e7f1ff !important;
                }}
                [class*="st-key-{key_prefix}_rank_remove_"] button {{
                    border-color: #f1c5c7 !important;
                    background: #fff8f8 !important;
                }}
                [class*="st-key-{key_prefix}_rank_remove_"] button:hover {{
                    border-color: #e99498 !important;
                    background: #fff0f1 !important;
                }}
                [class*="st-key-{key_prefix}_rank_up_"] button p,
                [class*="st-key-{key_prefix}_rank_down_"] button p,
                [class*="st-key-{key_prefix}_rank_remove_"] button p {{
                    display: block !important;
                    margin: 0 !important;
                    color: #0f5fd7 !important;
                    font-size: .78rem !important;
                    font-weight: 700 !important;
                    line-height: 1 !important;
                }}
                [class*="st-key-{key_prefix}_rank_remove_"] button p {{
                    color: #d53b41 !important;
                }}
                [class*="st-key-{key_prefix}_rank_up_"] button::before,
                [class*="st-key-{key_prefix}_rank_down_"] button::before,
                [class*="st-key-{key_prefix}_rank_remove_"] button::before {{
                    content: '';
                    display: block;
                    width: 20px;
                    height: 20px;
                    flex: 0 0 20px;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-size: 20px 20px;
                }}
                [class*="st-key-{key_prefix}_rank_up_"] button::before {{
                    background-image: url('{rank_up_icon}');
                }}
                [class*="st-key-{key_prefix}_rank_down_"] button::before {{
                    background-image: url('{rank_down_icon}');
                }}
                [class*="st-key-{key_prefix}_rank_remove_"] button::before {{
                    background-image: url('{rank_remove_icon}');
                }}
                [class*="st-key-{key_prefix}_rank_up_"] button:disabled,
                [class*="st-key-{key_prefix}_rank_down_"] button:disabled {{
                    opacity: .38 !important;
                    background: #f7f9fc !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
            clear_space, clear_action = st.columns([6, 1.25])
            with clear_action:
                st.button(
                    "すべてクリア",
                    key=f"{key_prefix}_rank_clear_all",
                    use_container_width=True,
                    on_click=_clear_ranking_values,
                    args=(key_prefix, list(selected_values)),
                )
            for rank_index, value in enumerate(selected_values):
                with st.container(border=True):
                    content_column, action_column = st.columns([7, 3])
                    with content_column:
                        icon_uri = _value_icon_data_uri(_value_icon_slug(value))
                        st.markdown(
                            f'<div class="metea-rank-card metea-rank-card--{rank_index + 1}">'
                            f'<span class="metea-rank-number">{rank_index + 1}位</span>'
                            f'<img src="{icon_uri}" alt="">'
                            f'<span class="metea-rank-value">{escape(value)}</span>'
                            '</div>',
                            unsafe_allow_html=True,
                        )
                    with action_column:
                        controls = st.columns(3)
                        with controls[0]:
                            st.button(
                                "上へ",
                                key=f"{key_prefix}_rank_up_{rank_index}",
                                disabled=rank_index == 0,
                                use_container_width=True,
                                help="順位を上げる",
                                on_click=_move_ranking_value,
                                args=(key_prefix, list(selected_values), rank_index, -1),
                            )
                        with controls[1]:
                            st.button(
                                "下へ",
                                key=f"{key_prefix}_rank_down_{rank_index}",
                                disabled=rank_index == len(selected_values) - 1,
                                use_container_width=True,
                                help="順位を下げる",
                                on_click=_move_ranking_value,
                                args=(key_prefix, list(selected_values), rank_index, 1),
                            )
                        with controls[2]:
                            st.button(
                                "外す",
                                key=f"{key_prefix}_rank_remove_{rank_index}",
                                use_container_width=True,
                                help="選択から外す",
                                on_click=_remove_ranking_value,
                                args=(key_prefix, list(selected_values), value),
                            )

        if "その他" in selected_values:
            custom_rank = selected_values.index("その他") + 1
            st.text_input(
                "その他の内容",
                max_chars=100,
                placeholder="具体的な内容を入力",
                key=f"{key_prefix}_{custom_rank}_custom",
            )
            render_work_values_field_error(
                errors,
                f"{key_prefix}_{custom_rank}_custom",
            )

def rewarding_experience_section(section_number: int) -> None:
    """やりがいを感じた経験を対話形式で整理する入力欄。"""

    with st.expander(f"{section_number}　実際にやりがいを感じた経験"):
        st.markdown(
            '<div class="metea-experience-guide">'
            '<strong>印象に残っている経験を、順番に振り返ってみましょう。</strong>'
            '<span>きれいな文章にまとめなくても大丈夫です。'
            '短い言葉や箇条書きでも入力できます。</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <style>
            .metea-experience-guide {
                display: flex;
                flex-direction: column;
                gap: 3px;
                margin: 2px 0 12px;
                padding: 12px 14px;
                border-left: 3px solid #4b8df5;
                border-radius: 0 9px 9px 0;
                background: #f4f8ff;
                color: #405a78;
            }
            .metea-experience-guide strong {
                color: #163b69;
                font-size: .92rem;
            }
            .metea-experience-guide span { font-size: .82rem; }
            .metea-experience-question {
                display: flex;
                align-items: flex-start;
                gap: 9px;
                margin: 10px 0 5px;
            }
            .metea-experience-question-number {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                flex: 0 0 24px;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                color: #146cff;
                background: #e6f0ff;
                font-size: .78rem;
                font-weight: 800;
            }
            .metea-experience-question strong {
                display: block;
                color: #082b59;
                font-size: .92rem;
            }
            .metea-experience-question small {
                display: block;
                margin-top: 2px;
                color: #7c8da3;
                font-size: .78rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        for index, (key, label, helper, placeholder) in enumerate(
            REWARDING_EXPERIENCE_FIELDS,
            start=1,
        ):
            st.markdown(
                f'<div class="metea-experience-question">'
                f'<span class="metea-experience-question-number">{index}</span>'
                f'<div><strong>{escape(label)}</strong>'
                f'<small>{escape(helper)}</small></div></div>',
                unsafe_allow_html=True,
            )
            st.text_area(
                label,
                key=key,
                height=82,
                max_chars=100,
                placeholder=placeholder,
                label_visibility="collapsed",
            )
        st.caption("すべて任意入力です。各項目100文字まで入力できます。")


def environment_reason_section(section_number: int) -> None:
    """力を発揮しやすい環境の理由を対話形式で整理する。"""

    with st.expander(
        f"{section_number}　その環境で力を発揮できると思う理由"
    ):
        st.markdown(
            '<div class="metea-experience-guide">'
            '<strong>選んだ環境が自分に合う理由を、少しずつ整理してみましょう。</strong>'
            '<span>正解はありません。思い浮かぶ範囲で入力してください。</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        for index, (key, label, helper, placeholder) in enumerate(
            ENVIRONMENT_REASON_FIELDS,
            start=1,
        ):
            st.markdown(
                f'<div class="metea-experience-question">'
                f'<span class="metea-experience-question-number">{index}</span>'
                f'<div><strong>{escape(label)}</strong>'
                f'<small>{escape(helper)}</small></div></div>',
                unsafe_allow_html=True,
            )
            st.text_area(
                label,
                key=key,
                height=82,
                max_chars=70,
                placeholder=placeholder,
                label_visibility="collapsed",
            )
        st.caption("すべて任意入力です。各項目70文字まで入力できます。")

def work_style_section(
    section_number: int,
    errors: dict[str, str],
) -> None:
    """仕事の進め方に関する5段階評価を表示する。"""

    with st.expander(
        f"{section_number}　仕事の進め方 :red[*]",
        expanded="work_style" in errors,
    ):
        st.markdown(
            '<div class="metea-work-style-guide">'
            '<strong>仕事を進めるとき、どちらの考え方が自分に近いですか？</strong>'
            '<span>正解・不正解はありません。普段の自分を思い浮かべて、'
            '1から5の中で最も近いものを選んでください。</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <style>
            .metea-work-style-guide {
                display: flex;
                flex-direction: column;
                gap: 3px;
                margin: 2px 0 14px;
                padding: 12px 14px;
                border: 1px solid #bdd7ff;
                border-radius: 10px;
                background: #f4f8ff;
                color: #405a78;
            }
            .metea-work-style-guide strong { color: #163b69; font-size: .92rem; }
            .metea-work-style-guide span { font-size: .82rem; }
            [data-testid="stVerticalBlockBorderWrapper"]:has(.metea-work-style-card-marker) {
                padding: 15px 16px 20px !important;
                border: 1px solid #d5e0ee !important;
                border-radius: 12px !important;
                background: #fff !important;
                box-shadow: 0 3px 10px rgba(31,65,114,.045) !important;
            }
            .metea-work-style-question {
                display: flex;
                align-items: center;
                gap: 9px;
                margin-bottom: 10px;
            }
            .metea-work-style-question span {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                flex: 0 0 27px;
                width: 27px;
                height: 27px;
                border-radius: 50%;
                color: #146cff;
                background: #e6f0ff;
                font-size: .75rem;
                font-weight: 800;
            }
            .metea-work-style-question strong {
                color: #082b59;
                font-size: 1rem;
            }
            .metea-work-style-choice {
                box-sizing: border-box;
                min-height: 67px;
                padding: 10px 13px;
                border: 1px solid #cbdcf2;
                border-radius: 10px;
                background: #f8fbff;
            }
            .metea-work-style-choice--right {
                border-color: #d7dff0;
                background: #fafbfe;
            }
            .metea-work-style-choice small {
                display: block;
                margin-bottom: 3px;
                color: #146cff;
                font-size: .72rem;
                font-weight: 800;
            }
            .metea-work-style-choice--right small { color: #526c91; }
            .metea-work-style-choice strong {
                color: #163b69;
                font-size: .88rem;
                line-height: 1.45;
            }
            .metea-work-style-prompt {
                box-sizing: border-box;
                min-height: 32px;
                margin: 0 0 5px;
                padding-top: 11px;
                text-align: center;
                color: #697d96;
                font-size: .8rem;
                font-weight: 650;
            }
            [class*="st-key-work_style_"] [role="radiogroup"] {
                display: grid !important;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                width: min(100%, 620px) !important;
                margin: 0 auto !important;
                gap: 6px;
            }
            [class*="st-key-work_style_"][data-testid="stRadio"],
            [class*="st-key-work_style_"] [data-testid="stRadio"] {
                width: 100% !important;
            }
            [class*="st-key-work_style_"] [role="radiogroup"] > label {
                min-height: 38px;
                margin: 0 !important;
                padding: 6px 8px;
                border: 1px solid #d4dfed;
                border-radius: 9px;
                background: #fff;
                justify-content: center;
            }
            [class*="st-key-work_style_"] [role="radiogroup"] > label:has(input:checked) {
                border-color: #74aaff;
                background: #eaf3ff;
                box-shadow: 0 0 0 1px rgba(20,108,255,.07);
            }
            .metea-work-style-result {
                margin: 7px 0 5px;
                padding: 7px 10px;
                border-radius: 8px;
                background: #f4f7fb;
                text-align: center;
                color: #526c91;
                font-size: .8rem;
            }
            .metea-work-style-result strong { color: #0f5fd7; }
            @media (max-width: 700px) {
                .metea-work-style-choice { min-height: 82px; }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        unanswered_card_selectors = [
            '[data-testid="stVerticalBlockBorderWrapper"]:'
            f'has(.metea-work-style-card-marker--{question["question_type"]})'
            for question in WORK_STYLE_QUESTIONS
            if f"work_style_{question['question_type']}" in errors
        ]
        if unanswered_card_selectors:
            st.markdown(
                "<style>"
                + ",".join(unanswered_card_selectors)
                + "{border:1.5px solid #ef4b55 !important;"
                  "background:#fffafa !important;}"
                  "</style>",
                unsafe_allow_html=True,
            )

        for question_index, question in enumerate(WORK_STYLE_QUESTIONS, start=1):
            state_key = f"work_style_{question['question_type']}"
            field_error = errors.get(state_key)
            with st.container(border=True):
                st.markdown(
                    '<span class="metea-work-style-card-marker '
                    f'metea-work-style-card-marker--{question["question_type"]}" '
                    'aria-hidden="true"></span>'
                    f'<div class="metea-work-style-question">'
                    f'<span>{question_index}</span>'
                    f'<strong>{escape(question["title"])}</strong></div>',
                    unsafe_allow_html=True,
                )
                endpoint_columns = st.columns(2)
                endpoint_columns[0].markdown(
                    '<div class="metea-work-style-choice">'
                    '<small>1 に近い考え方</small>'
                    f'<strong>{escape(question["left_text"])}</strong></div>',
                    unsafe_allow_html=True,
                )
                endpoint_columns[1].markdown(
                    '<div class="metea-work-style-choice metea-work-style-choice--right">'
                    '<small>5 に近い考え方</small>'
                    f'<strong>{escape(question["right_text"])}</strong></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<p class="metea-work-style-prompt">どの程度近いですか？</p>',
                    unsafe_allow_html=True,
                )
                radio_left, radio_center, radio_right = st.columns(
                    [4, 2, 4],
                    gap="small",
                )
                with radio_center:
                    score = st.radio(
                        label=f"{question['title']}の回答",
                        options=[1, 2, 3, 4, 5],
                        horizontal=True,
                        key=state_key,
                        index=None,
                        format_func=lambda value: str(value),
                        label_visibility="collapsed",
                    )
                if score is None:
                    st.markdown(
                        '<p class="metea-work-style-result">'
                        'まだ回答が選択されていません</p>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<p class="metea-work-style-result">現在の回答：'
                        f'<strong>{score}　{WORK_STYLE_SCORE_LABELS[score]}</strong></p>',
                        unsafe_allow_html=True,
                    )
                if field_error:
                    st.markdown(
                        f'<p class="metea-values-field-error">'
                        f'{escape(field_error)}</p>',
                        unsafe_allow_html=True,
                    )

def show_page() -> None:
    """価値観入力画面を表示する。"""

    apply_self_discovery_theme(current_step=3)

    st.markdown(
        """
        <span class="metea-values-page-marker" aria-hidden="true"></span>
        <style>
        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker),
        section.main > div.block-container:has(.metea-values-page-marker) {
            box-sizing: border-box;
            width: calc(100vw - 272px);
            max-width: none;
            height: calc(100dvh - 84px);
            min-height: 620px;
            margin: 66px 28px 18px 244px;
            padding: 12px 34px 18px;
            overflow-x: hidden;
            overflow-y: auto;
            scrollbar-gutter: stable;
            overscroll-behavior: contain;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker) h1 {
            margin-top: 0;
            margin-bottom: 0;
            font-size: clamp(1.9rem, 2.3vw, 2.35rem);
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        > [data-testid="stVerticalBlock"],
        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        > div > [data-testid="stVerticalBlock"] {
            gap: 0.5rem;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        [data-testid="stProgress"] {
            margin: 2px 0 7px;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--metea-line) !important;
            border-radius: 12px !important;
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(31, 65, 114, 0.055);
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        [data-testid="stExpander"] {
            margin-bottom: 4px;
            overflow: hidden;
            border: 1px solid var(--metea-line) !important;
            border-radius: 12px !important;
            background: #ffffff;
            box-shadow: 0 4px 12px rgba(31, 65, 114, 0.055);
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        [data-testid="stExpander"] details,
        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        [data-testid="stExpander"] summary {
            border-radius: 11px !important;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        [data-testid="stExpander"] summary {
            min-height: 43px;
            padding: 0 10px;
            font-size: 0.94rem;
            font-weight: 700;
        }

        [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker)
        [data-testid="stButton"] > button {
            min-height: 36px;
            border-radius: 9px;
        }

        .metea-values-error-summary {
            display: flex;
            gap: 14px;
            align-items: flex-start;
            margin: 4px 0 10px;
            padding: 13px 16px;
            border: 1.5px solid #ffb8bd;
            border-radius: 11px;
            background: #fff7f7;
            color: #d92d3a;
        }

        .metea-values-error-icon {
            display: grid;
            place-items: center;
            flex: 0 0 25px;
            width: 25px;
            height: 25px;
            border: 2px solid #ef3f4c;
            border-radius: 7px 7px 9px 9px;
            font-weight: 900;
            line-height: 1;
        }

        .metea-values-error-summary strong { font-size: 0.95rem; }
        .metea-values-error-summary ul { margin: 5px 0 0; padding-left: 1.15rem; }
        .metea-values-error-summary li { margin: 2px 0; font-size: 0.88rem; }

        .metea-values-field-error {
            display: block;
            min-height: 18px;
            margin: 1px 0 4px !important;
            color: #dc3545 !important;
            font-size: 0.84rem !important;
            font-weight: 650;
            line-height: 1.35 !important;
        }

        [data-testid="stElementContainer"]:has(.metea-values-field-error) {
            min-height: 23px;
            margin-bottom: 2px;
            overflow: visible;
        }

        .metea-values-guide {
            margin: 5px 0 0;
            padding: 10px 14px;
            border: 1px solid #bdd7ff;
            border-radius: 11px;
            background: #f4f8ff;
            color: #405a78;
        }

        .metea-values-section-spacer {
            display: block;
            width: 100%;
            height: 12px;
            min-height: 12px;
            line-height: 0;
        }

        [data-testid="stElementContainer"]:has(.metea-values-section-spacer) {
            height: 12px;
            min-height: 12px;
            margin: 0;
        }

        @media (max-width: 1100px) {
            [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker),
            section.main > div.block-container:has(.metea-values-page-marker) {
                width: calc(100vw - 36px);
                height: calc(100dvh - 36px);
                min-height: 0;
                margin: 18px;
                padding: 22px 28px 28px;
            }
        }

        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"]:has(.metea-values-page-marker),
            section.main > div.block-container:has(.metea-values-page-marker) {
                width: 100%;
                height: auto;
                min-height: 100dvh;
                margin: 0;
                padding: 20px 16px 32px;
                overflow: visible;
                border-left: 0;
                border-right: 0;
                border-radius: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    initialize_work_values_state()

    hope_conditions_message = st.session_state.pop(
        "hope_conditions_draft_message",
        None,
    )
    if hope_conditions_message:
        st.toast(hope_conditions_message)

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

    errors = st.session_state.get(WORK_VALUES_ERRORS_KEY, {})
    render_work_values_error_summary(errors)

    error_selectors: list[str] = []
    for ranking_key in (
        "important_value",
        "rewarding_scene",
        "strength_environment",
    ):
        if ranking_key in errors:
            error_selectors.append(
                '[data-testid="stExpander"]:'
                f'has(.metea-values-ranking-marker--{ranking_key})'
            )
    for error_key in errors:
        if error_key.endswith("_custom"):
            error_selectors.append(f'.st-key-{error_key} input')

    if error_selectors:
        st.markdown(
            "<style>"
            + ",".join(error_selectors)
            + "{border:1.5px solid #ef4b55 !important;"
              "background:#fffafa !important;"
              "box-shadow:0 0 0 2px rgba(239,75,85,.08) !important;}"
              "</style>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="metea-values-guide">'
        '<strong>まずは直感で回答してください。</strong> '
        'あとから何度でも変更できます。'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<span class="metea-values-section-spacer" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    ranking_section(
        section_number=1,
        title="仕事で大切にしたいこと",
        options=IMPORTANT_VALUE_OPTIONS,
        key_prefix="important_value",
        errors=errors,
    )

    ranking_section(
        section_number=2,
        title="やりがいを感じる場面",
        options=REWARDING_SCENE_OPTIONS,
        key_prefix="rewarding_scene",
        errors=errors,
    )

    rewarding_experience_section(section_number=3)

    ranking_section(
        section_number=4,
        title="力を発揮しやすい環境",
        options=STRENGTH_ENVIRONMENT_OPTIONS,
        key_prefix="strength_environment",
        errors=errors,
    )

    environment_reason_section(section_number=5)

    work_style_section(section_number=6, errors=errors)

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

                st.toast(
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
            # 基本情報・希望条件と同様に、下書き保存後に必須確認を行う。
            draft_data = collect_work_values_draft()
            save_work_values_draft(draft_data)

            validation_errors = validate_work_values_form()
            st.session_state[WORK_VALUES_ERRORS_KEY] = validation_errors

            if validation_errors:
                st.rerun()

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
                    detail_text=_compose_rewarding_experience(),
                ),
                WorkValueDetail(
                    detail_type="environment_reason",
                    detail_text=_compose_environment_reason(),
                ),
            ]

            work_style_answers: list[WorkStyleAnswer] = []

            for question in WORK_STYLE_QUESTIONS:
                answer_score = st.session_state.get(
                    "work_style_"
                    f"{question['question_type']}"
                )
                if answer_score is None:
                    continue
                work_style_answers.append(
                    WorkStyleAnswer(
                        question_type=question[
                            "question_type"
                        ],
                        answer_score=answer_score,
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
                st.session_state[WORK_VALUES_ERRORS_KEY] = {}
                st.session_state.pop("job_hunting_axes_loaded", None)
                st.session_state.pop("job_hunting_axes", None)
                st.query_params["page"] = "job_hunting_axis"
                st.rerun()
