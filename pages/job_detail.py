"""登録済み求人の詳細画面。"""

from datetime import date
from html import escape

import streamlit as st

from models import JobApplicationDecision
from services.job_evaluation_service import (
    APPLICATION_DECISION_OPTIONS,
    load_job_application_decisions,
    load_job_match_evaluations,
    save_job_application_decision_data,
)
from services.basic_info_service import (
    load_basic_info,
)
from services.job_commute_service import (
    build_google_maps_transit_url,
    load_current_job_commute,
    save_manual_job_commute,
)
from services.job_confirmation_service import (
    CONFIRMATION_STATUS_NOT_REQUIRED,
    build_confirmation_item_key,
    load_job_confirmation_resolutions,
    mark_confirmation_not_required,
    restore_confirmation_item,
)
from services.job_matching_auto_evaluation_service import (
    automatically_evaluate_and_save_job,
)
from services.job_matching_cache_service import (
    invalidate_current_user_job_evaluation,
)
from services.job_service import load_job

from pages.job_layout import (
    render_job_navigation,
)


def move_to_job_list() -> None:
    """求人一覧へ移動する。"""

    st.query_params["page"] = "job_list"

    if "job_id" in st.query_params:
        del st.query_params["job_id"]

    st.rerun()


def move_back_from_job_detail() -> None:
    """開いた元の画面へ戻る。"""

    return_page = st.query_params.get(
        "return_page",
        "",
    )

    comparison_job_ids = (
        st.query_params.get(
            "job_ids",
            "",
        )
    )

    if return_page == "job_comparison":
        st.query_params.clear()

        st.query_params["page"] = (
            "job_comparison"
        )

        if comparison_job_ids:
            st.query_params["job_ids"] = (
                comparison_job_ids
            )

    else:
        st.query_params.clear()

        st.query_params["page"] = (
            "job_list"
        )

    st.rerun()


def display_value(
    value,
) -> str:
    """未入力値を画面表示用に整える。"""

    if value is None:
        return "未入力"

    if isinstance(value, list):
        cleaned_values = [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

        if not cleaned_values:
            return "未入力"

        return "\n".join(
            f"・{item}"
            for item in cleaned_values
        )

    cleaned_value = str(value).strip()

    return cleaned_value or "未入力"


def render_field(
    label: str,
    value,
) -> None:
    """項目名と内容を表示する。"""

    st.caption(label)

    st.write(
        display_value(value)
    )


def render_job_information_heading(
    title: str,
    icon: str,
    tone: str,
) -> None:
    """求人情報カードの見出しを表示する。"""

    st.markdown(
        f"""
        <div class="job-information-heading {escape(tone)}">
            <span class="job-information-icon">{escape(icon)}</span>
            <span>{escape(title)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_basic_information(
    job,
) -> None:
    """求人基本情報を表示する。"""

    with st.container(border=True):
        render_job_information_heading("基本情報", "▣", "tone-blue")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "会社名",
                job.company_name,
            )

            render_field(
                "求人名",
                job.job_title,
            )

            render_field(
                "募集ポジション（職種）",
                job.occupation,
            )

            render_field(
                "業種",
                job.industry,
            )

        with col2:
            source_text = job.source_name

            if (
                job.source_type
                and job.source_name
            ):
                source_text = (
                    f"{job.source_type}／"
                    f"{job.source_name}"
                )

            render_field(
                "紹介経路",
                source_text,
            )

            render_field(
                "求人番号",
                job.job_number,
            )

            render_field(
                "雇用形態",
                job.employment_type,
            )

            render_field(
                "配属部署",
                job.department,
            )


def render_job_description(
    job,
) -> None:
    """仕事内容を表示する。"""

    with st.container(border=True):
        render_job_information_heading("仕事内容", "◎", "tone-blue")

        render_field(
            "仕事内容・業務概要",
            job.job_summary,
        )

        render_field(
            "具体的な業務内容",
            job.job_details,
        )

        render_field(
            "担当範囲・役割",
            job.responsibility_scope,
        )

        render_field(
            "顧客・対象者",
            job.customers,
        )

        render_field(
            "目標・KPI",
            job.goals_kpi,
        )

        render_field(
            "期待される成果",
            job.expected_results,
        )


def render_requirements(
    job,
) -> None:
    """応募要件を表示する。"""

    with st.container(border=True):
        render_job_information_heading("応募要件", "✓", "tone-orange")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "必須経験",
                job.required_experience,
            )

            render_field(
                "必須スキル",
                job.required_skills,
            )

            render_field(
                "必須資格",
                job.required_qualifications,
            )

        with col2:
            render_field(
                "歓迎経験",
                job.preferred_experience,
            )

            render_field(
                "歓迎スキル",
                job.preferred_skills,
            )

            render_field(
                "求める人物像",
                job.desired_personality,
            )


def render_working_conditions(
    job,
) -> None:
    """勤務条件を表示する。"""

    with st.container(border=True):
        render_job_information_heading("勤務条件", "◷", "tone-green")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "勤務地",
                " ".join(
                    value
                    for value in (
                        job.prefecture,
                        job.municipality,
                    )
                    if value
                ),
            )

            render_field(
                "最寄駅",
                job.nearest_station,
            )

            render_field(
                "勤務形態・働き方",
                job.work_style,
            )

            render_field(
                "転勤",
                job.transfer_required,
            )

        with col2:
            render_field(
                "勤務時間",
                (
                    f"{job.start_time}～"
                    f"{job.end_time}"
                    if (
                        job.start_time
                        or job.end_time
                    )
                    else ""
                ),
            )

            render_field(
                "フレックスタイム",
                job.flextime,
            )

            render_field(
                "残業",
                job.overtime,
            )

            render_field(
                "年間休日数",
                job.annual_holidays,
            )


def render_salary_and_benefits(
    job,
) -> None:
    """給与と福利厚生を表示する。"""

    with st.container(border=True):
        render_job_information_heading("給与・待遇", "◇", "tone-purple")

        col1, col2 = st.columns(2)

        with col1:
            render_field(
                "年収",
                job.annual_salary,
            )

            render_field(
                "想定年収（下限）",
                job.expected_salary_min,
            )

            render_field(
                "想定年収（上限）",
                job.expected_salary_max,
            )

            render_field(
                "月給",
                job.monthly_salary,
            )

        with col2:
            render_field(
                "賞与",
                job.bonus,
            )

            render_field(
                "昇給",
                job.salary_increase,
            )

            render_field(
                "社会保険",
                job.social_insurance,
            )

            render_field(
                "研修制度",
                job.training_program,
            )


def render_score(
    label: str,
    score: int | None,
    tone: str,
) -> None:
    """カテゴリ点数を円形メーターで表示する。"""

    normalized_score = (
        max(0, min(int(score), 100))
        if score is not None
        else 0
    )
    score_text = (
        f"{normalized_score}%"
        if score is not None
        else "未評価"
    )
    state_class = (
        "is-unscored"
        if score is None
        else ""
    )

    st.markdown(
        f"""
        <div class="category-score-card {escape(tone)}">
            <div class="category-score-label">{escape(label)}</div>
            <div class="category-score-ring {state_class}"
                 style="--score: {normalized_score};">
                <div class="category-score-ring-inner">
                    <span>{escape(score_text)}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overall_score(
    label: str,
    score: int | None,
    coverage: int,
) -> None:
    """総合点を星評価とともに大きく表示する。"""

    if score is None:
        score_text = "未評価"
        stars = "☆☆☆☆☆"
    else:
        normalized_score = max(
            0,
            min(int(score), 100),
        )
        score_text = f"{normalized_score}"
        filled_stars = max(
            0,
            min(5, round(normalized_score / 20)),
        )
        stars = (
            "★" * filled_stars
            + "☆" * (5 - filled_stars)
        )

    st.markdown(
        f"""
        <div class="overall-score-panel">
            <div class="overall-score-label">{escape(label)}</div>
            <div class="overall-score-value">
                <strong>{escape(score_text)}</strong>
                <span>/100</span>
            </div>
            <div class="overall-score-stars">{stars}</div>
            <div class="overall-score-coverage">
                評価できた情報 {int(coverage)}%
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_evaluation_point_card(
    title: str,
    content: str,
    tone: str,
) -> None:
    """AI評価の説明を項目ごとのカードで表示する。"""

    tone_classes = {
        "positive": (
            "evaluation-point-card-positive"
        ),
        "caution": (
            "evaluation-point-card-caution"
        ),
        "information": (
            "evaluation-point-card-information"
        ),
    }

    tone_icons = {
        "positive": "●",
        "caution": "●",
        "information": "●",
    }

    tone_class = tone_classes.get(
        tone,
        "evaluation-point-card-information",
    )

    tone_icon = tone_icons.get(
        tone,
        "●",
    )

    items = []

    for line in (content or "").splitlines():
        normalized_line = line.strip()

        if not normalized_line:
            continue

        normalized_line = (
            normalized_line
            .lstrip("・")
            .lstrip("•")
            .lstrip("-")
            .strip()
        )

        if normalized_line:
            items.append(normalized_line)

    if not items:
        items = [
            "該当する項目はありません。"
        ]

    summary_items = []

    for item in items[:3]:
        item_name, separator, reason = (
            item.partition("：")
        )

        if separator and len(reason) > 64:
            reason = f"{reason[:63]}…"

        summary_item = (
            f"{item_name}：{reason}"
            if separator
            else item
        )

        if len(summary_item) > 92:
            summary_item = (
                f"{summary_item[:91]}…"
            )

        summary_items.append(summary_item)

    item_html = "".join(
        f"<li>{escape(item)}</li>"
        for item in summary_items
    )

    st.markdown(
        f"""
        <div class="evaluation-point-card {tone_class}">
            <div class="evaluation-point-card-title">
                <span class="evaluation-point-card-icon">
                    {tone_icon}
                </span>
                <span>{escape(title)}</span>
            </div>
            <ul class="evaluation-point-card-list">
                {item_html}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )




def render_commute_confirmation(
    job_id: int,
    job,
) -> None:
    """必要な場合だけ通勤時間の確認欄を表示する。"""

    basic_info = load_basic_info()

    save_message_key = (
        f"job_commute_saved_message_{job_id}"
    )

    save_message = st.session_state.pop(
        save_message_key,
        None,
    )

    with st.expander(
        "電車移動時間の確認",
        expanded=(
            save_message is not None
        ),
    ):
        if basic_info is None:
            st.info(
                "通勤時間を確認するには、"
                "基本情報を登録してください。"
                "未確認の通勤時間はAI評価で減点しません。"
            )
            return

        origin_station_name = (
            basic_info.nearest_station.strip()
        )

        origin_station_place_id = (
            basic_info.nearest_station_place_id.strip()
        )

        if (
            not origin_station_name
            or not origin_station_place_id
        ):
            st.info(
                "基本情報で現在の最寄駅が"
                "登録されていません。"
                "未確認の通勤時間はAI評価で減点しません。"
            )
            return

        destination_station_name = (
            job.nearest_station.strip()
            if job.nearest_station
            else ""
        )

        if not destination_station_name:
            st.info(
                "求人票に勤務地の最寄駅が"
                "記載されていないため、"
                "通勤時間は要確認です。"
                "この項目はAI評価で減点しません。"
            )
            return

        saved_commute = load_current_job_commute(
            job_id=job_id,
            current_origin_station_place_id=(
                origin_station_place_id
            ),
            current_destination_station_name=(
                destination_station_name
            ),
        )

        maps_origin = " ".join(
            value
            for value in [
                basic_info.prefecture,
                basic_info.municipality,
                origin_station_name,
            ]
            if value
        )

        maps_destination = " ".join(
            value
            for value in [
                job.prefecture,
                job.municipality,
                destination_station_name,
            ]
            if value
        )

        maps_url = build_google_maps_transit_url(
            origin_station_name=maps_origin,
            destination_station_name=(
                maps_destination
            ),
        )

        st.write(
            f"**{origin_station_name} → "
            f"{destination_station_name}**"
        )

        st.caption(
            "求人票に記載された最寄駅を使って、"
            "駅間の電車移動時間を確認します。"
        )

        if save_message:
            st.success(
                save_message,
                icon="✅",
            )

        if saved_commute is not None:
            st.success(
                f"片道"
                f"{saved_commute.duration_minutes}分として"
                f"確認済みです。"
                f"（確認日：{saved_commute.checked_at}）"
            )
        else:
            st.warning(
                "通勤時間はまだ確認されていません。"
                "未確認の間はAI評価で減点しません。"
            )

        st.link_button(
            "Googleマップで電車経路を確認する",
            maps_url,
            width="stretch",
        )

        with st.form(
            f"job_commute_form_{job_id}"
        ):
            duration_minutes = st.number_input(
                "片道の電車移動時間（分）",
                min_value=0,
                max_value=600,
                value=(
                    saved_commute.duration_minutes
                    if saved_commute is not None
                    else None
                ),
                step=1,
            )

            submitted = st.form_submit_button(
                "確認した時間を保存する",
                type="primary",
                width="stretch",
            )

        if submitted:
            try:
                saved_commute_result = (
                    save_manual_job_commute(
                        job_id=job_id,
                        origin_station_name=(
                            origin_station_name
                        ),
                        origin_station_place_id=(
                            origin_station_place_id
                        ),
                        destination_station_name=(
                            destination_station_name
                        ),
                        duration_minutes=(
                            duration_minutes
                        ),
                    )
                )

            except ValueError as error:
                st.error(str(error))

            else:
                commute_changed = (
                    saved_commute is None
                    or saved_commute.duration_minutes
                    != saved_commute_result.duration_minutes
                )

                if not commute_changed:
                    st.session_state[
                        save_message_key
                    ] = (
                        "通勤時間を保存しました。"
                        "内容に変更がないため、"
                        "AI評価は更新していません。"
                    )

                    st.rerun()

                invalidate_current_user_job_evaluation(
                    job_id=job_id,
                    reason=(
                        "電車移動時間が変更されました。"
                    ),
                )

                with st.spinner(
                    "通勤時間をもとにAI評価を"
                    "更新しています..."
                ):
                    (
                        updated_evaluation,
                        evaluation_error,
                    ) = (
                        automatically_evaluate_and_save_job(
                            job_id=job_id,
                        )
                    )

                if (
                    updated_evaluation is not None
                    and not evaluation_error
                ):
                    save_message = (
                        "通勤時間を保存し、"
                        "AI評価を更新しました。"
                    )

                else:
                    save_message = (
                        "通勤時間は保存しましたが、"
                        "AI評価を更新できませんでした。"
                    )

                st.session_state[
                    save_message_key
                ] = save_message

                st.rerun()


def render_section_heading(
    number: int,
    title: str,
    description: str = "",
) -> None:
    """番号付きの画面セクション見出しを表示する。"""

    description_html = (
        '<div class="detail-section-description">'
        f'{escape(description)}'
        '</div>'
        if description
        else ""
    )

    st.markdown(
        f"""
        <div class="detail-section-heading">
            <span class="detail-section-number">{number}</span>
            <div>
                <div class="detail-section-title">{escape(title)}</div>
                {description_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_ai_matching_result(
    job_id: int,
    job,
) -> None:
    """求人のAIマッチング結果を表示する。"""

    evaluations = (
        load_job_match_evaluations()
    )

    evaluation = evaluations.get(job_id)

    render_section_heading(
        1,
        "AIマッチング結果",
        "現在のプロフィールと求人情報をもとに評価しています。",
    )

    if evaluation is None:
        st.info(
            "この求人のAIマッチング評価は"
            "まだ完了していません。"
        )

    else:
        if evaluation.is_stale:
            stale_reason = (
                evaluation.stale_reason.strip()
                or "評価に使用した情報が変更されました。"
            )

            st.warning(
                "この求人はAI評価の再評価待ちです。"
                "以下には前回の評価結果を表示しています。\n\n"
                f"再評価理由：{stale_reason}"
            )

        elif evaluation.is_provisional:
            st.info(
                "この評価は暫定結果です。"
                "全評価カテゴリの配点のうち、"
                "現在評価できた情報は"
                f"{evaluation.evaluation_coverage}%です。"
            )

        else:
            st.success(
                "必要な評価カテゴリをすべて"
                "採点した総合評価です。"
            )

        with st.container(
            border=True,
            key="ai_matching_result_card",
        ):
            overall_col, detail_col = st.columns(
                [1, 4]
            )

            with overall_col:
                if evaluation.is_stale:
                    overall_label = (
                        "前回の暫定AI総合マッチ度"
                        if evaluation.is_provisional
                        else "前回のAI総合マッチ度"
                    )

                elif evaluation.is_provisional:
                    overall_label = (
                        "暫定AI総合マッチ度"
                    )

                else:
                    overall_label = (
                        "AI総合マッチ度"
                    )

                render_overall_score(
                    overall_label,
                    evaluation.overall_score,
                    evaluation.evaluation_coverage,
                )


            with detail_col:
                (
                    hope_col,
                    value_col,
                    career_col,
                    required_col,
                ) = st.columns(
                    4,
                    gap="medium",
                )

                with hope_col:
                    render_score(
                        "希望条件",
                        evaluation.hope_condition_score,
                        "tone-blue",
                    )

                with value_col:
                    render_score(
                        "就活の軸",
                        evaluation.work_value_score,
                        "tone-green",
                    )

                with career_col:
                    render_score(
                        "職務経歴・スキル",
                        evaluation.career_skill_score,
                        "tone-orange",
                    )

                with required_col:
                    render_score(
                        "必須条件",
                        evaluation.required_condition_score,
                        "tone-purple",
                    )

            st.markdown(
                '<div class="ai-score-row-spacer"></div>',
                unsafe_allow_html=True,
            )

            (
                comment_col1,
                comment_col2,
                comment_col3,
            ) = st.columns(
                3,
                gap="medium",
            )

            with comment_col1:
                render_evaluation_point_card(
                    title="合っている点",
                    content=(
                        evaluation.matching_points
                    ),
                    tone="positive",
                )

            with comment_col2:
                render_evaluation_point_card(
                    title="懸念点",
                    content=(
                        evaluation.concern_points
                    ),
                    tone="caution",
                )

            with comment_col3:
                render_evaluation_point_card(
                    title="次に確認すること",
                    content=(
                        evaluation.confirmation_points
                    ),
                    tone="information",
                )

            if evaluation.ai_comment:
                st.caption("評価について")

                st.write(
                    evaluation.ai_comment
                )

    render_commute_confirmation(
        job_id=job_id,
        job=job,
    )


def get_score_judgment(
    score: int | None,
) -> str:
    """マッチング点数を判定表示へ変換する。"""

    if score is None:
        return "要確認"

    if score >= 80:
        return "一致"

    if score >= 60:
        return "一部一致"

    return "要確認"


def parse_evaluation_detail_items(
    content: str,
    judgment: str,
) -> list[dict[str, str]]:
    """保存済み評価文章を詳細表示用の項目へ変換する。"""

    detail_items = []

    for line in (content or "").splitlines():
        normalized_line = (
            line.strip()
            .lstrip("・")
            .lstrip("•")
            .lstrip("-")
            .strip()
        )

        if not normalized_line:
            continue

        item_name, separator, reason = (
            normalized_line.partition("：")
        )

        detail_items.append(
            {
                "item_name": (
                    item_name.strip()
                    if separator
                    else normalized_line
                ),
                "judgment": judgment,
                "reason": (
                    reason.strip()
                    if separator
                    else ""
                ),
            }
        )

    return detail_items


def classify_confirmation_target(
    item: dict[str, str],
) -> str:
    """要確認項目を企業確認とプロフィール確認へ分類する。"""

    searchable_text = (
        f"{item.get('item_name', '')} "
        f"{item.get('reason', '')}"
    )

    user_information_keywords = (
        "利用者情報",
        "プロフィール",
        "ユーザー情報",
        "設定されていません",
        "入力されていません",
        "登録されていません",
        "まだ確認されていません",
        "現在の最寄駅",
    )

    if any(
        keyword in searchable_text
        for keyword in user_information_keywords
    ):
        return "user"

    return "company"


def render_evaluation_detail_table(
    detail_items: list[dict[str, str]],
) -> None:
    """判定理由を含む評価一覧表を表示する。"""

    judgment_classes = {
        "適合": "is-match",
        "一致": "is-match",
        "一部一致": "is-partial",
        "不一致": "is-mismatch",
        "要確認": "is-confirmation",
    }

    rows_html = []

    for item in detail_items:
        judgment = item.get(
            "judgment",
            "要確認",
        )
        judgment_class = judgment_classes.get(
            judgment,
            "is-confirmation",
        )
        reason = (
            item.get("reason", "").strip()
            or "判定理由の詳細はありません。"
        )

        rows_html.append(
            "<div class=\"matching-detail-row\">"
            "<div class=\"matching-detail-judgment\">"
            f"<span class=\"matching-judgment-badge {judgment_class}\">"
            f"{escape(judgment)}"
            "</span>"
            "</div>"
            "<div class=\"matching-detail-item-name\">"
            f"{escape(item.get('item_name', '評価項目'))}"
            "</div>"
            "<div class=\"matching-detail-reason\">"
            f"{escape(reason)}"
            "</div>"
            "</div>"
        )

    st.markdown(
        """
        <div class="matching-detail-table">
            <div class="matching-detail-table-header">
                <div>判定</div>
                <div>評価項目</div>
                <div>評価理由</div>
            </div>
        """
        + "".join(rows_html)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_confirmation_group(
    title: str,
    description: str,
    items: list[dict[str, str]],
    tone: str,
) -> None:
    """確認先ごとのアクションカードを表示する。"""

    if items:
        item_html = "".join(
            "<li>"
            f"<strong>{escape(item['item_name'])}</strong>"
            f"<span>{escape(item.get('reason', ''))}</span>"
            "</li>"
            for item in items
        )
    else:
        item_html = (
            "<li class=\"is-empty\">"
            "現在、該当する確認項目はありません。"
            "</li>"
        )

    st.markdown(
        f"""
        <div class="matching-confirmation-card {escape(tone)}">
            <div class="matching-confirmation-title">
                {escape(title)}
            </div>
            <div class="matching-confirmation-description">
                {escape(description)}
            </div>
            <ul>{item_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def partition_company_confirmation_items(
    job_id: int,
    items: list[dict[str, str]],
) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
]:
    """企業確認項目を確認中と確認不要に分ける。"""

    resolutions = (
        load_job_confirmation_resolutions(job_id)
    )
    active_items = []
    dismissed_items = []

    for item in items:
        item_with_key = dict(item)
        item_key = build_confirmation_item_key(
            item.get("item_name", ""),
            item.get("reason", ""),
        )
        item_with_key["item_key"] = item_key

        if resolutions.get(item_key) == (
            CONFIRMATION_STATUS_NOT_REQUIRED
        ):
            dismissed_items.append(item_with_key)
        else:
            active_items.append(item_with_key)

    return active_items, dismissed_items


def render_actionable_confirmation_group(
    job_id: int,
    items: list[dict[str, str]],
) -> None:
    """企業確認項目と確認不要操作を表示する。"""

    with st.container(
        border=True,
        key=f"company_confirmation_card_{job_id}",
    ):
        st.markdown(
            '<div class="action-confirmation-heading company">'
            '<span>●</span><strong>企業・求人元へ確認</strong>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "面談や応募前に、企業へ確認したい内容です。"
        )

        if not items:
            st.success(
                "現在、確認が必要な項目はありません。"
            )
            return

        for index, item in enumerate(items):
            text_col, action_col = st.columns(
                [4, 1],
                gap="small",
                vertical_alignment="center",
            )

            with text_col:
                st.markdown(
                    f"**{item.get('item_name', '確認項目')}**"
                )
                st.caption(item.get("reason", ""))

            with action_col:
                if st.button(
                    "確認不要",
                    key=(
                        "dismiss_confirmation_"
                        f"{job_id}_{index}_"
                        f"{item['item_key']}"
                    ),
                    use_container_width=True,
                    help=(
                        "AI評価は変えず、確認が必要な一覧から外します。"
                    ),
                ):
                    mark_confirmation_not_required(
                        job_id=job_id,
                        item_name=item.get(
                            "item_name",
                            "",
                        ),
                        item_reason=item.get(
                            "reason",
                            "",
                        ),
                    )
                    st.rerun()

            if index < len(items) - 1:
                st.divider()


def render_dismissed_confirmation_items(
    job_id: int,
    items: list[dict[str, str]],
) -> None:
    """確認不要にした項目と復元操作を表示する。"""

    if not items:
        return

    with st.expander(
        f"確認不要にした項目（{len(items)}件）",
        expanded=False,
    ):
        st.caption(
            "必要になった項目は、確認一覧へ戻せます。"
        )

        for index, item in enumerate(items):
            text_col, action_col = st.columns(
                [5, 1],
                gap="small",
                vertical_alignment="center",
            )

            with text_col:
                st.markdown(
                    f"**{item.get('item_name', '確認項目')}**"
                )
                st.caption(item.get("reason", ""))

            with action_col:
                if st.button(
                    "元に戻す",
                    key=(
                        "restore_confirmation_"
                        f"{job_id}_{index}_"
                        f"{item['item_key']}"
                    ),
                    use_container_width=True,
                ):
                    restore_confirmation_item(
                        job_id=job_id,
                        item_key=item["item_key"],
                    )
                    st.rerun()

            if index < len(items) - 1:
                st.divider()

def render_matching_detail(
    job_id: int,
) -> None:
    """AIマッチング評価の内訳を表示する。"""

    evaluations = (
        load_job_match_evaluations()
    )

    evaluation = evaluations.get(job_id)

    render_section_heading(
        2,
        "マッチング詳細",
        "評価理由と、次に確認したい情報を確認できます。",
    )

    with st.expander(
        "評価一覧と確認項目を見る",
        expanded=False,
    ):
        if evaluation is None:
            st.info(
                "AI評価後にマッチング詳細を表示します。"
            )

            return

        detail_items = [
            *parse_evaluation_detail_items(
                evaluation.matching_points,
                "適合",
            ),
            *parse_evaluation_detail_items(
                evaluation.concern_points,
                "不一致",
            ),
            *parse_evaluation_detail_items(
                evaluation.confirmation_points,
                "要確認",
            ),
        ]

        st.markdown(
            '<div class="matching-detail-section-title">'
            '評価一覧表'
            '</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "AI評価とルール判定で確認した項目を、"
            "判定理由とともに表示しています。"
        )

        if detail_items:
            render_evaluation_detail_table(
                detail_items
            )
        else:
            st.info(
                "表示できる評価項目はありません。"
            )

        confirmation_items = [
            item
            for item in detail_items
            if item.get("judgment") == "要確認"
        ]
        company_items = [
            item
            for item in confirmation_items
            if classify_confirmation_target(item)
            == "company"
        ]
        user_items = [
            item
            for item in confirmation_items
            if classify_confirmation_target(item)
            == "user"
        ]
        (
            active_company_items,
            dismissed_company_items,
        ) = partition_company_confirmation_items(
            job_id,
            company_items,
        )

        st.markdown(
            '<div class="matching-detail-section-title '
            'has-top-margin">確認が必要な項目</div>',
            unsafe_allow_html=True,
        )

        company_col, user_col = st.columns(
            2,
            gap="medium",
        )

        with company_col:
            render_actionable_confirmation_group(
                job_id=job_id,
                items=active_company_items,
            )

        with user_col:
            render_confirmation_group(
                title="プロフィール入力を確認",
                description=(
                    "入力を補うと、次回評価の精度が上がります。"
                ),
                items=user_items,
                tone="user",
            )

        render_dismissed_confirmation_items(
            job_id=job_id,
            items=dismissed_company_items,
        )


def _render_application_decision_content(
    job_id: int,
) -> None:
    """応募判断と管理情報を表示・保存する。"""

    decisions = (
        load_job_application_decisions()
    )

    decision = decisions.get(job_id)

    save_message_key = (
        f"job_decision_saved_message_{job_id}"
    )

    save_message = st.session_state.pop(
        save_message_key,
        None,
    )

    decision_options = list(
        APPLICATION_DECISION_OPTIONS
    )

    selected_index = None
    decision_captions = (
        "応募へ進む",
        "不明点を確認してから判断",
        "いったん判断を保留",
        "今回は応募を見送る",
        "別の応募経路で進める",
    )

    if (
        decision is not None
        and decision.decision_status
        in decision_options
    ):
        selected_index = decision_options.index(
            decision.decision_status
        )

    deadline_value = None

    if (
        decision is not None
        and decision.action_deadline
    ):
        try:
            deadline_value = date.fromisoformat(
                decision.action_deadline
            )

        except ValueError:
            deadline_value = None

    if save_message:
        st.success(
            save_message,
            icon="✅",
        )

    if (
        decision is not None
        and decision.decision_status
    ):
        st.info(
            "現在の応募判断："
            f"{decision.decision_status}"
        )

    else:
        st.warning(
            "応募判断はまだ保存されていません。"
        )

    st.caption(
        "AI評価と求人情報を確認したうえで、"
        "最終的な応募判断を選択してください。"
    )

    with st.form(
        f"job_application_decision_form_{job_id}"
    ):
        selected_status = st.radio(
            "応募判断",
            decision_options,
            index=selected_index,
            horizontal=True,
            captions=decision_captions,
            width="stretch",
        )

        action_col, deadline_col, memo_col = st.columns(
            [1.15, 1, 2.2],
            gap="medium",
            vertical_alignment="top",
        )

        with action_col:
            next_action = st.text_input(
                "次のアクション",
                value=(
                    decision.next_action
                    if decision is not None
                    else ""
                ),
                placeholder="例：採用担当者へ確認",
            )

        with deadline_col:
            action_deadline = st.date_input(
                "期限",
                value=deadline_value,
            )

        with memo_col:
            memo = st.text_area(
                "メモ（任意）",
                value=(
                    decision.memo
                    if decision is not None
                    else ""
                ),
                placeholder=(
                    "気になった点や、次に確認したいことを記録します。"
                ),
                height=104,
            )

        compare_col, save_col = st.columns(
            [1, 2],
            gap="medium",
        )

        with compare_col:
            compare_submitted = st.form_submit_button(
                "他の求人と比較する",
                type="secondary",
                width="stretch",
            )

        with save_col:
            submitted = st.form_submit_button(
                "応募判断を保存する",
                type="primary",
                width="stretch",
            )

    if compare_submitted:
        st.session_state[
            "job_compare_selected_ids"
        ] = [job_id]
        st.session_state[
            f"compare_job_{job_id}"
        ] = True
        st.query_params["page"] = "job_list"

        if "job_id" in st.query_params:
            del st.query_params["job_id"]

        st.rerun()

    if submitted:
        errors = (
            save_job_application_decision_data(
                JobApplicationDecision(
                    job_id=job_id,
                    decision_status=(
                        selected_status or ""
                    ),
                    next_action=(
                        next_action.strip()
                    ),
                    action_deadline=(
                        action_deadline.isoformat()
                        if action_deadline
                        is not None
                        else None
                    ),
                    memo=memo.strip(),
                )
            )
        )

        if errors:
            for error in errors:
                st.error(error)

        else:
            st.session_state[
                save_message_key
            ] = (
                f"応募判断「{selected_status}」を"
                "保存しました。"
            )

            st.rerun()


def render_application_decision(
    job_id: int,
) -> None:
    """応募判断をカード内に表示する。"""

    render_section_heading(
        4,
        "応募判断",
        "AI評価と求人情報を確認し、現在の判断と次の行動を記録します。",
    )

    with st.container(
        border=True,
        key=f"application_decision_card_{job_id}",
    ):
        _render_application_decision_content(job_id)

def render_job_detail_styles() -> None:
    """求人確認画面専用のスタイルを適用する。"""

    st.markdown(
        """
        <style>
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background-color: #f7f9fc;
        }

        [data-testid="stHeader"] {
            background-color: rgba(247, 249, 252, 0.92);
        }

        .block-container {
            max-width: 1320px;
            padding-top: 32px;
            padding-bottom: 64px;
        }


        .stApp h1 {
            margin-bottom: 8px;
            color: #10213d;
            font-size: 38px;
            font-weight: 800;
            line-height: 1.3;
            letter-spacing: -0.02em;
        }

        .stApp h2,
        .stApp h3 {
            color: #10213d;
            font-weight: 750;
            line-height: 1.45;
        }

        .stApp h2 {
            font-size: 25px;
        }

        .stApp h3 {
            font-size: 21px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff !important;
            border-color: #dfe6f0;
            border-radius: 12px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]
        div[data-testid="stVerticalBlock"] {
            background-color: #ffffff !important;
        }

        [class*="st-key-ai_matching_result_card"] {
            background-color: #ffffff !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            [class*="st-key-ai_matching_result_card"]
        ) {
            background-color: #ffffff !important;
        }

        [class*="st-key-ai_matching_result_card"]
        > div,
        [class*="st-key-ai_matching_result_card"]
        div[data-testid="stVerticalBlock"] {
            background-color: #ffffff !important;
        }

        div[data-testid="stMetric"] {
            min-height: 108px;
            padding: 14px 16px;
            background: #ffffff;
            border: 1px solid #e3e8f0;
            border-radius: 10px;
        }

        div[data-testid="stMetricValue"] {
            color: #1268f3;
            font-weight: 800;
        }

        div[data-testid="stExpander"] {
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 10px;
        }

        div[data-testid="stForm"] {
            padding: 20px;
            background: #fbfcff;
            border: 1px solid #dfe6f0;
            border-radius: 12px;
        }

        div[data-testid="stAlert"] {
            border-radius: 10px;
        }

        .ai-score-row-spacer {
            height: 20px;
        }

        [class*="st-key-ai_matching_result_card"]
        [data-testid="stHorizontalBlock"] {
            column-gap: 18px;
        }
        .overall-score-panel {
            box-sizing: border-box;
            min-height: 190px;
            padding: 22px 18px;
            text-align: center;
            background: #f8fbff;
            border: 1px solid #d9e6f8;
            border-radius: 12px;
        }

        .overall-score-label,
        .category-score-label {
            color: #263956;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.5;
        }

        .overall-score-value {
            display: flex;
            align-items: baseline;
            justify-content: center;
            gap: 4px;
            margin-top: 8px;
            color: #1268f3;
        }

        .overall-score-value strong {
            font-size: 46px;
            font-weight: 850;
            line-height: 1;
            letter-spacing: -0.04em;
        }

        .overall-score-value span {
            color: #71809a;
            font-size: 12px;
            font-weight: 700;
        }

        .overall-score-stars {
            margin-top: 8px;
            color: #1268f3;
            font-size: 22px;
            line-height: 1;
            letter-spacing: 2px;
        }

        .overall-score-coverage {
            display: inline-flex;
            margin-top: 14px;
            padding: 5px 10px;
            color: #1268f3;
            background: #eaf3ff;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
        }

        .category-score-card {
            min-height: 190px;
            padding: 18px 8px 14px;
            text-align: center;
            background: #ffffff;
            border-radius: 12px;
        }

        .category-score-ring {
            --ring-color: #1268f3;
            position: relative;
            display: grid;
            width: 112px;
            height: 112px;
            margin: 18px auto 0;
            place-items: center;
            background: conic-gradient(
                var(--ring-color) calc(var(--score) * 1%),
                #e8edf5 0
            );
            border-radius: 50%;
        }

        .category-score-ring::before {
            position: absolute;
            width: 88px;
            height: 88px;
            content: "";
            background: #ffffff;
            border-radius: 50%;
        }

        .category-score-ring-inner {
            position: relative;
            z-index: 1;
            color: var(--ring-color);
            font-size: 24px;
            font-weight: 850;
            line-height: 1;
        }

        .category-score-ring.is-unscored {
            background: #e8edf5;
        }

        .category-score-ring.is-unscored::before {
            width: 86px;
            height: 86px;
        }

        .category-score-ring.is-unscored span {
            color: #8996a9;
            font-size: 15px;
        }

        .category-score-card.tone-blue {
            --ring-color: #1268f3;
        }

        .category-score-card.tone-green {
            --ring-color: #18a66a;
        }

        .category-score-card.tone-orange {
            --ring-color: #f59e0b;
        }

        .category-score-card.tone-purple {
            --ring-color: #7657e8;
        }

        .category-score-card .category-score-ring {
            --ring-color: inherit;
        }
        .evaluation-point-card {
            box-sizing: border-box;
            width: 100%;
            min-height: 190px;
            padding: 18px 18px 16px;
            border: 1px solid transparent;
            border-radius: 10px;
            overflow-wrap: anywhere;
            word-break: normal;
        }

        .evaluation-point-card-positive {
            color: #137a3f;
            background: #effaf3;
            border-color: #d2eedc;
        }

        .evaluation-point-card-caution {
            color: #9a6700;
            background: #fffaf0;
            border-color: #f4e6bd;
        }

        .evaluation-point-card-information {
            color: #075eae;
            background: #f0f6ff;
            border-color: #d7e6fb;
        }

        .evaluation-point-card-title {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            font-size: 15px;
            font-weight: 700;
            line-height: 1.5;
        }

        .evaluation-point-card-icon {
            flex: 0 0 auto;
            font-size: 11px;
        }

        .evaluation-point-card-list {
            margin: 0;
            padding-left: 21px;
        }

        .evaluation-point-card-list li {
            margin: 0 0 10px;
            padding-left: 2px;
            font-size: 14px;
            line-height: 1.65;
        }

        .evaluation-point-card-list li:last-child {
            margin-bottom: 0;
        }

        .evaluation-point-card {
            min-height: 160px;
        }

        .evaluation-point-card-list li {
            margin-bottom: 8px;
            font-size: 13px;
            line-height: 1.55;
        }

        .matching-detail-section-title {
            margin: 8px 0 4px;
            color: #10213d;
            font-size: 18px;
            font-weight: 800;
            line-height: 1.5;
        }

        .matching-detail-section-title.has-top-margin {
            margin-top: 28px;
        }

        .matching-detail-table {
            margin-top: 12px;
            overflow: hidden;
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 12px;
        }

        .matching-detail-table-header,
        .matching-detail-row {
            display: grid;
            grid-template-columns: 116px minmax(180px, 0.8fr) minmax(320px, 2fr);
            column-gap: 18px;
            align-items: start;
        }

        .matching-detail-table-header {
            padding: 12px 18px;
            color: #5f6f86;
            background: #f5f8fc;
            border-bottom: 1px solid #dfe6f0;
            font-size: 13px;
            font-weight: 700;
        }

        .matching-detail-row {
            padding: 15px 18px;
            border-bottom: 1px solid #e8edf4;
        }

        .matching-detail-row:last-child {
            border-bottom: 0;
        }

        .matching-detail-item-name {
            color: #10213d;
            font-size: 14px;
            font-weight: 700;
            line-height: 1.65;
        }

        .matching-detail-reason {
            color: #43526a;
            font-size: 14px;
            line-height: 1.7;
        }

        .matching-judgment-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 78px;
            min-height: 28px;
            padding: 4px 10px;
            border: 1px solid transparent;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            line-height: 1;
        }

        .matching-judgment-badge.is-match {
            color: #118443;
            background: #eaf8ef;
            border-color: #bfe8cc;
        }

        .matching-judgment-badge.is-partial {
            color: #b56a00;
            background: #fff7e8;
            border-color: #f5d79c;
        }

        .matching-judgment-badge.is-mismatch {
            color: #d23f45;
            background: #fff0f1;
            border-color: #f4c4c7;
        }

        .matching-judgment-badge.is-confirmation {
            color: #1268f3;
            background: #edf5ff;
            border-color: #c8defd;
        }

        .matching-confirmation-card {
            box-sizing: border-box;
            min-height: 230px;
            padding: 18px 20px;
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 12px;
        }

        .matching-confirmation-card.company {
            border-top: 4px solid #f5a623;
        }

        .matching-confirmation-card.user {
            background: #f4f8ff;
            border-color: #d7e6fb;
            border-top: 4px solid #1268f3;
        }

        .matching-confirmation-title {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #10213d;
            font-size: 16px;
            font-weight: 800;
            line-height: 1.5;
        }

        .matching-confirmation-card.user .matching-confirmation-title::before {
            color: #1268f3;
            font-size: 11px;
            content: "●";
        }

        .matching-confirmation-description {
            margin-top: 4px;
            color: #66758c;
            font-size: 13px;
            line-height: 1.6;
        }

        .matching-confirmation-card ul {
            margin: 14px 0 0;
            padding-left: 20px;
        }

        .matching-confirmation-card li {
            margin-bottom: 12px;
            color: #43526a;
            font-size: 13px;
            line-height: 1.65;
        }

        .matching-confirmation-card li:last-child {
            margin-bottom: 0;
        }

        .matching-confirmation-card li strong,
        .matching-confirmation-card li span {
            display: block;
        }

        .matching-confirmation-card li strong {
            margin-bottom: 2px;
            color: #10213d;
            font-size: 14px;
        }

        .matching-confirmation-card li.is-empty {
            color: #7a8799;
        }

        .job-information-heading {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 18px;
            padding-bottom: 12px;
            color: #10213d;
            border-bottom: 1px solid #e8edf4;
            font-size: 18px;
            font-weight: 800;
            line-height: 1.4;
        }

        .job-information-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            color: #1268f3;
            background: #eaf3ff;
            border-radius: 50%;
            font-size: 14px;
        }

        .job-information-heading.tone-orange .job-information-icon {
            color: #c97500;
            background: #fff4df;
        }

        .job-information-heading.tone-green .job-information-icon {
            color: #118443;
            background: #eaf8ef;
        }

        .job-information-heading.tone-purple .job-information-icon {
            color: #6846d6;
            background: #f0ebff;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 10px;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label {
            box-sizing: border-box;
            min-height: 82px;
            margin: 0;
            padding: 14px 10px;
            align-items: flex-start;
            justify-content: center;
            text-align: center;
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 10px;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:has(input:checked) {
            box-shadow: 0 0 0 2px rgba(18, 104, 243, 0.10);
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(1) {
            --decision-radio-color: #1268f3;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(2) {
            --decision-radio-color: #1268f3;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(3) {
            --decision-radio-color: #1268f3;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(4) {
            --decision-radio-color: #1268f3;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(5) {
            --decision-radio-color: #1268f3;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label input:checked {
            accent-color: var(--decision-radio-color) !important;
        }
        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:has(input:checked) > div:first-child {
            background-color: var(--decision-radio-color) !important;
            border-color: var(--decision-radio-color) !important;
            border-radius: 50% !important;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label input:checked + div,
        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label input:checked ~ div:first-of-type {
            background-color: var(--decision-radio-color) !important;
            border-color: var(--decision-radio-color) !important;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:has(input:checked)
        > div:first-child > div:last-child {
            background-color: var(--decision-radio-color) !important;
            border-color: var(--decision-radio-color) !important;
        }        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(1) {
            background: #f2fbf5;
            border-color: #cbead5;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(1):has(input:checked) {
            background: #e5f7eb;
            border-color: #18a66a;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(2) {
            background: #fff9ef;
            border-color: #f3dfb5;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(2):has(input:checked) {
            background: #fff1d8;
            border-color: #f59e0b;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(3) {
            background: #f3f7ff;
            border-color: #d5e3fb;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(3):has(input:checked) {
            background: #e7f0ff;
            border-color: #1268f3;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(4) {
            background: #fff5f5;
            border-color: #f4d0d2;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(4):has(input:checked) {
            background: #ffe9ea;
            border-color: #e2555a;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(5) {
            background: #f7f4ff;
            border-color: #dfd7f8;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label:nth-child(5):has(input:checked) {
            background: #eee9ff;
            border-color: #7657e8;
        }

        [class*="st-key-application_decision_card_"]
        div[role="radiogroup"] label p {
            color: #233955;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.5;
        }
        .detail-section-heading {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin: 34px 0 16px;
        }

        .detail-section-number {
            display: inline-flex;
            flex: 0 0 28px;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            margin-top: 1px;
            color: #ffffff;
            background: #1268f3;
            border-radius: 50%;
            font-size: 14px;
            font-weight: 800;
        }

        .detail-section-title {
            color: #10213d;
            font-size: 21px;
            font-weight: 800;
            line-height: 1.35;
        }

        .detail-section-description {
            margin-top: 4px;
            color: #66758c;
            font-size: 13px;
            line-height: 1.6;
        }

        [class*="st-key-company_confirmation_card_"] {
            background: #fffaf2 !important;
            border-top: 4px solid #f5a623 !important;
            box-shadow: 0 5px 16px rgba(16, 33, 61, 0.05);
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            [class*="st-key-company_confirmation_card_"]
        ) {
            background: #fffaf2 !important;
            border-top: 4px solid #f5a623 !important;
        }

        .action-confirmation-heading {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #10213d;
            font-size: 16px;
            line-height: 1.5;
        }

        .action-confirmation-heading.company span {
            color: #f5a623;
            font-size: 11px;
        }

        .matching-confirmation-card {
            box-shadow: 0 5px 16px rgba(16, 33, 61, 0.05);
        }

        [class*="st-key-application_decision_card_"] {
            padding: 22px !important;
            background: #ffffff !important;
            border: 1px solid #dfe6f0 !important;
            box-shadow: 0 8px 22px rgba(16, 33, 61, 0.06);
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            [class*="st-key-application_decision_card_"]
        ) {
            background: #ffffff !important;
        }

        [class*="st-key-application_decision_card_"]
        div[data-testid="stForm"] {
            background: #f8fbff;
            border-color: #d9e6f8;
        }

        [class*="st-key-application_decision_card_"]
        [data-testid="stFormSubmitButton"]
        button[data-testid="stBaseButton-primaryFormSubmit"],
        [class*="st-key-application_decision_card_"]
        [data-testid="stFormSubmitButton"] button[kind="primary"] {
            color: #ffffff !important;
            background: #1268f3 !important;
            border-color: #1268f3 !important;
            box-shadow: 0 5px 12px rgba(18, 104, 243, 0.20) !important;
        }

        [class*="st-key-application_decision_card_"]
        [data-testid="stFormSubmitButton"]
        button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
        [class*="st-key-application_decision_card_"]
        [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: #0759d9 !important;
            border-color: #0759d9 !important;
        }

        [class*="st-key-application_decision_card_"]
        [data-testid="stFormSubmitButton"]
        button[data-testid="stBaseButton-secondaryFormSubmit"],
        [class*="st-key-application_decision_card_"]
        [data-testid="stFormSubmitButton"] button[kind="secondary"] {
            color: #1268f3 !important;
            background: #ffffff !important;
            border-color: #9fc0f4 !important;
            box-shadow: none !important;
        }
        [data-testid="stMain"] button[kind="primary"],
        [data-testid="stMain"] button[data-testid="stBaseButton-primary"] {
            min-height: 42px;
            color: #ffffff;
            background: #1268f3;
            border-color: #1268f3;
            border-radius: 8px;
            font-weight: 700;
            box-shadow: 0 5px 12px rgba(18, 104, 243, 0.18);
        }

        [data-testid="stMain"] button[kind="secondary"],
        [data-testid="stMain"] button[data-testid="stBaseButton-secondary"] {
            min-height: 40px;
            color: #17457e;
            background: #ffffff;
            border-color: #cdd8e8;
            border-radius: 8px;
            font-weight: 650;
        }

        div[data-testid="stExpander"] > details > summary {
            min-height: 52px;
            color: #17457e;
            font-weight: 700;
        }

        div[data-testid="stExpander"] > details[open] > summary {
            border-bottom: 1px solid #e8edf4;
        }
        @media (max-width: 900px) {
            .evaluation-point-card {
                min-height: auto;
            }

            .matching-detail-table-header {
                display: none;
            }

            .matching-detail-row {
                grid-template-columns: 1fr;
                row-gap: 8px;
            }

            .matching-confirmation-card {
                min-height: auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_page() -> None:
    """求人詳細画面を表示する。"""

    render_job_navigation(
        "job_detail"
    )

    render_job_detail_styles()

    job_id_value = st.query_params.get(
        "job_id"
    )

    try:
        job_id = int(job_id_value)
    except (
        TypeError,
        ValueError,
    ):
        st.error(
            "表示する求人を特定できませんでした。"
        )

        if st.button(
            "求人一覧へ戻る",
            key="invalid_job_back",
        ):
            move_to_job_list()

        return

    job = load_job(job_id)

    if job is None:
        st.error(
            "求人が見つかりませんでした。"
        )

        if st.button(
            "求人一覧へ戻る",
            key="missing_job_back",
        ):
            move_to_job_list()

        return

    return_page = st.query_params.get(
        "return_page",
        "",
    )

    back_button_label = (
        "← 比較結果へ戻る"
        if return_page == "job_comparison"
        else "← 求人一覧へ戻る"
    )

    if st.button(
        back_button_label,
        key="job_detail_back",
    ):
        move_back_from_job_detail()


    st.title(
        job.company_name
        or "会社名未入力"
    )

    st.subheader(
        job.job_title
        or job.occupation
        or "求人名未入力"
    )

    render_ai_matching_result(
        job_id=job_id,
        job=job,
    )

    st.divider()

    render_matching_detail(job_id)

    st.divider()

    render_section_heading(
        3,
        "求人詳細",
        "応募条件、仕事内容、勤務条件を求人票の情報から確認します。",
    )

    with st.expander(
        "求人詳細を見る",
        expanded=False,
    ):
        render_basic_information(job)
        render_job_description(job)
        render_requirements(job)
        render_working_conditions(job)
        render_salary_and_benefits(job)

    st.divider()

    render_application_decision(job_id)