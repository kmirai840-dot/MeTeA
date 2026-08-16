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


def render_basic_information(
    job,
) -> None:
    """求人基本情報を表示する。"""

    with st.container(border=True):
        st.subheader("基本情報")

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
        st.subheader("仕事内容")

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
        st.subheader("応募要件")

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
        st.subheader("勤務条件")

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
        st.subheader("給与・待遇")

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
) -> None:
    """AI評価の点数と進捗バーを表示する。"""

    st.metric(
        label,
        (
            f"{score}点"
            if score is not None
            else "未評価"
        ),
    )

    if score is not None:
        normalized_score = max(
            0,
            min(
                int(score),
                100,
            ),
        )

        st.progress(
            normalized_score / 100
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

    item_html = "".join(
        f"<li>{escape(item)}</li>"
        for item in items
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


def render_ai_matching_result(
    job_id: int,
    job,
) -> None:
    """求人のAIマッチング結果を表示する。"""

    evaluations = (
        load_job_match_evaluations()
    )

    evaluation = evaluations.get(job_id)

    st.subheader("1　AIマッチング結果")

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

        with st.container(border=True):
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

                render_score(
                    overall_label,
                    evaluation.overall_score,
                )

                coverage_label = (
                    "前回評価時に評価できた情報"
                    if evaluation.is_stale
                    else "評価できた情報"
                )

                st.caption(
                    f"{coverage_label}："
                    f"{evaluation.evaluation_coverage}%"
                )

            with detail_col:
                (
                    hope_col,
                    value_col,
                    career_col,
                    required_col,
                ) = st.columns(4)

                with hope_col:
                    render_score(
                        "希望条件",
                        evaluation.hope_condition_score,
                    )

                with value_col:
                    render_score(
                        "価値観",
                        evaluation.work_value_score,
                    )

                with career_col:
                    render_score(
                        "職務経歴・スキル",
                        evaluation.career_skill_score,
                    )

                with required_col:
                    render_score(
                        "必須条件",
                        evaluation.required_condition_score,
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


def render_matching_detail(
    job_id: int,
) -> None:
    """AIマッチング評価の内訳を表示する。"""

    evaluations = (
        load_job_match_evaluations()
    )

    evaluation = evaluations.get(job_id)

    st.subheader("2　マッチング詳細")

    with st.expander(
        "マッチング詳細を見る",
        expanded=False,
    ):
        if evaluation is None:
            st.info(
                "AI評価後にマッチング詳細を表示します。"
            )

            return

        matching_rows = [
            {
                "項目": "希望条件",
                "評価": (
                    f"{evaluation.hope_condition_score}点"
                    if evaluation.hope_condition_score
                    is not None
                    else "未評価"
                ),
                "判定": get_score_judgment(
                    evaluation.hope_condition_score
                ),
            },
            {
                "項目": "価値観",
                "評価": (
                    f"{evaluation.work_value_score}点"
                    if evaluation.work_value_score
                    is not None
                    else "未評価"
                ),
                "判定": get_score_judgment(
                    evaluation.work_value_score
                ),
            },
            {
                "項目": "職務経歴・スキル",
                "評価": (
                    f"{evaluation.career_skill_score}点"
                    if evaluation.career_skill_score
                    is not None
                    else "未評価"
                ),
                "判定": get_score_judgment(
                    evaluation.career_skill_score
                ),
            },
            {
                "項目": "必須条件",
                "評価": (
                    f"{evaluation.required_condition_score}点"
                    if evaluation.required_condition_score
                    is not None
                    else "未評価"
                ),
                "判定": get_score_judgment(
                    evaluation.required_condition_score
                ),
            },
        ]

        st.dataframe(
            matching_rows,
            width="stretch",
            hide_index=True,
        )

        if evaluation.confirmation_points:
            st.caption("確認が必要な項目")

            st.write(
                evaluation.confirmation_points
            )


def render_application_decision(
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

    decision_options = [
        "選択してください",
        *APPLICATION_DECISION_OPTIONS,
    ]

    selected_index = 0

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

    st.subheader("4　応募判断")

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
        selected_status = st.selectbox(
            "応募判断",
            decision_options,
            index=selected_index,
        )

        next_action = st.text_input(
            "次のアクション",
            value=(
                decision.next_action
                if decision is not None
                else ""
            ),
            placeholder=(
                "例：採用担当者へ確認する"
            ),
        )

        action_deadline = st.date_input(
            "期限",
            value=deadline_value,
        )

        memo = st.text_area(
            "メモ",
            value=(
                decision.memo
                if decision is not None
                else ""
            ),
            placeholder=(
                "気になった点や、"
                "次に確認したいことを記録します。"
            ),
        )

        submitted = st.form_submit_button(
            "応募判断を保存する",
            type="primary",
            width="stretch",
        )

    if submitted:
        errors = (
            save_job_application_decision_data(
                JobApplicationDecision(
                    job_id=job_id,
                    decision_status=(
                        selected_status
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

    st.divider()

    st.caption(
        "応募判断の前に他の求人との違いを"
        "確認したい場合は、比較対象を追加できます。"
    )

    if st.button(
        "他の求人と比較する",
        key=f"job_detail_compare_{job_id}",
        width="stretch",
    ):
        st.session_state[
            "job_compare_selected_ids"
        ] = [job_id]

        st.session_state[
            f"compare_job_{job_id}"
        ] = True

        st.query_params["page"] = (
            "job_list"
        )

        if "job_id" in st.query_params:
            del st.query_params["job_id"]

        st.rerun()


def render_job_detail_styles() -> None:
    """求人確認画面専用のスタイルを適用する。"""

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 32px;
            padding-bottom: 64px;
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

        @media (max-width: 900px) {
            .evaluation-point-card {
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

    header_col, source_col = st.columns(
        [4, 1]
    )

    with header_col:
        st.title(
            job.company_name
            or "会社名未入力"
        )

        st.subheader(
            job.job_title
            or job.occupation
            or "求人名未入力"
        )

    with source_col:
        st.caption(
            f"求人ID：{job_id}"
        )

    render_ai_matching_result(
        job_id=job_id,
        job=job,
    )

    st.divider()

    render_matching_detail(job_id)

    st.divider()

    st.subheader("3　求人詳細")

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