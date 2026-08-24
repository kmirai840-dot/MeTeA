"""登録済み求人の一覧画面。"""

from html import escape

import streamlit as st

from database.repositories.home_activity_repository import save_general_activity

from pages.job_registration import (
    JOB_FORM_RETURN_PAGE_KEY,
    load_job_for_edit,
    start_new_job_registration,
)
from services.job_service import (
    delete_job_data,
    load_job_sources,
    load_jobs,
)
from services.job_evaluation_service import (
    APPLICATION_DECISION_OPTIONS,
    is_job_match_evaluation_ready,
    load_job_application_decisions,
    load_job_match_evaluations,
)
from services.job_matching_auto_evaluation_service import (
    enqueue_job_evaluation,
    enqueue_stale_job_evaluations,
)
from services.job_matching_cache_service import (
    load_current_user_stale_job_ids,
)
from services.current_user_service import get_current_user_id

from pages.job_layout import (
    render_job_navigation,
    svg_data_uri,
)

JOB_DELETE_CONFIRM_KEY = (
    "job_list_delete_confirm_id"
)

JOB_COMPARE_SELECTED_KEY = (
    "job_compare_selected_ids"
)

JOB_LIST_PAGE_KEY = (
    "job_list_current_page"
)

JOB_STALE_REFRESH_SIGNATURE_KEY = (
    "job_list_stale_refresh_signature"
)

JOB_LIST_PAGE_SIZE = 20


def move_to_page(
    page_name: str | None,
) -> None:
    """指定した画面へ移動する。"""

    if page_name is None:
        st.query_params.clear()
    else:
        st.query_params["page"] = page_name

    st.rerun()


def render_empty_state() -> None:
    """求人が未登録の場合の案内を表示する。"""

    with st.container(border=True):
        st.info(
            "登録済みの求人はありません。"
            "気になる求人を登録してみましょう。"
        )

        if st.button(
            "求人を登録する",
            key="empty_job_registration",
            type="primary",
            width="stretch",
        ):
            start_new_job_registration()
            move_to_page("job_registration")


def render_delete_confirmation(
    job_id: int,
    company_name: str,
    job_name: str,
) -> None:
    """求人を削除する前の確認を表示する。"""

    pending_job_id = st.session_state.get(
        JOB_DELETE_CONFIRM_KEY
    )

    if pending_job_id != job_id:
        return

    st.warning(
        f"「{company_name}／{job_name}」を"
        "求人一覧から削除しますか？"
    )

    st.caption(
        "削除した求人は通常の一覧には"
        "表示されなくなります。"
    )

    confirm_col, cancel_col = st.columns(2)

    with confirm_col:
        if st.button(
            "削除する",
            key=f"confirm_delete_job_{job_id}",
            type="primary",
            width="stretch",
        ):
            deleted = delete_job_data(
                job_id
            )

            if deleted:
                st.session_state[
                    JOB_DELETE_CONFIRM_KEY
                ] = None

                st.toast(
                    "求人を削除しました。"
                )

                st.rerun()

            else:
                st.error(
                    "求人を削除できませんでした。"
                )

    with cancel_col:
        if st.button(
            "キャンセル",
            key=f"cancel_delete_job_{job_id}",
            width="stretch",
        ):
            st.session_state[
                JOB_DELETE_CONFIRM_KEY
            ] = None

            st.rerun()


def render_job_table_header() -> None:
    """求人一覧の列見出しを表示する。"""

    (
        compare_col,
        job_col,
        work_col,
        evaluation_col,
        status_col,
        action_col,
    ) = st.columns(
        [
            0.35,
            3.4,
            2.0,
            1.55,
            2.35,
            1.7,
        ],
        gap="medium",
    )

    headings = (
        (
            compare_col,
            "比較",
        ),
        (
            job_col,
            "会社名 / 求人名",
        ),
        (
            work_col,
            "職種 / 勤務地",
        ),
        (
            evaluation_col,
            "AI評価",
        ),
        (
            status_col,
            "応募状況 / 紹介元",
        ),
        (
            action_col,
            "求人票の編集・削除",
        ),
    )

    for column, heading in headings:
        with column:
            st.markdown(
                '<div class="job-row-table-heading">'
                f'{escape(heading)}'
                '</div>',
                unsafe_allow_html=True,
            )


def render_job_card(
    job_id: int,
    job,
    evaluation,
    decision,
) -> bool:
    """求人1件分をコンパクトな一覧行として表示する。"""

    sources = load_job_sources(
        job_id
    )

    company_name = (
        job.company_name
        or "会社名未入力"
    )

    job_name = (
        job.job_title
        or job.occupation
        or "求人名未入力"
    )

    occupation_text = (
        job.occupation
        or "職種未入力"
    )

    location_parts = [
        value
        for value in (
            job.prefecture,
            job.municipality,
        )
        if value
    ]

    location_text = (
        "".join(location_parts)
        or "勤務地未入力"
    )

    evaluation_coverage_text = ""

    if evaluation is not None and evaluation.evaluation_status in {"queued", "running"}:
        evaluation_text = "AI評価中"
        evaluation_class = "is-pending"
    elif evaluation is not None and evaluation.evaluation_status == "failed":
        evaluation_text = "評価に失敗"
        evaluation_class = "is-pending"
    elif evaluation is not None and evaluation.is_stale:
        evaluation_text = "再評価待ち"
        evaluation_class = "is-pending"

    elif (
        evaluation is not None
        and evaluation.overall_score
        is not None
    ):
        if evaluation.is_provisional:
            evaluation_text = (
                f"暫定 {evaluation.overall_score}点"
            )

        else:
            evaluation_text = (
                f"{evaluation.overall_score}点"
            )

        evaluation_class = "is-scored"

        if (
            evaluation.evaluation_coverage
            is not None
        ):
            evaluation_coverage_text = (
                "評価情報 "
                f"{evaluation.evaluation_coverage}%"
            )

    else:
        evaluation_text = "未評価"
        evaluation_class = "is-unrated"

    if (
        decision is not None
        and decision.decision_status
    ):
        decision_text = (
            decision.decision_status
        )

    else:
        decision_text = "未対応"

    if decision_text == "未対応":
        decision_class = "is-unhandled"

    elif decision_text == "応募する":
        decision_class = "is-positive"

    elif "応募しない" in decision_text:
        decision_class = "is-negative"

    elif "保留" in decision_text:
        decision_class = "is-hold"

    else:
        decision_class = "is-other"

    if sources:
        first_source = sources[0][1]

        source_text = (
            first_source.source_name
            or "名称未入力"
        )

        if (
            first_source.source_type
            and first_source.source_name
        ):
            source_text = (
                f"{first_source.source_type}／"
                f"{first_source.source_name}"
            )

        if len(sources) > 1:
            source_text = (
                f"{source_text} "
                f"ほか{len(sources) - 1}件"
            )

    else:
        source_text = "紹介元未入力"

    coverage_html = ""

    if evaluation_coverage_text:
        coverage_html = (
            '<p class="job-row-ai-coverage">'
            f'{escape(evaluation_coverage_text)}'
            '</p>'
        )

    with st.container(
        border=True,
        key=f"job_row_card_{job_id}",
    ):
        st.markdown(
            '<span class="job-row-marker">'
            '</span>',
            unsafe_allow_html=True,
        )

        (
            compare_col,
            job_col,
            work_col,
            evaluation_col,
            status_col,
            action_col,
        ) = st.columns(
            [
                0.35,
                3.4,
                2.0,
                1.55,
                2.35,
                1.7,
            ],
            gap="medium",
            vertical_alignment="center",
        )

        with compare_col:
            selected = st.checkbox(
                "比較対象に選択",
                key=f"compare_job_{job_id}",
                label_visibility="collapsed",
                disabled=not is_job_match_evaluation_ready(evaluation),
            )

        with job_col:
            # 求人詳細は評価を開始する入口でもあるため、AI評価の状態に
            # かかわらず会社名から開けるようにする。評価完了を必要とする
            # のは比較対象への選択だけとする。
            company_html = (
                '<a class="job-row-company-link" '
                f'href="?page=job_detail&job_id={job_id}" '
                'target="_self">'
                f'{escape(str(company_name))}'
                '</a>'
            )

            job_html = (
                company_html
                + '<p class="job-row-job-name">'
                f'{escape(str(job_name))}'
                '</p>'
            )

            st.markdown(
                job_html,
                unsafe_allow_html=True,
            )

        with work_col:
            work_html = (
                '<p class="job-row-primary">'
                f'{escape(str(occupation_text))}'
                '</p>'
                '<p class="job-row-secondary">'
                f'{escape(str(location_text))}'
                '</p>'
            )

            st.markdown(
                work_html,
                unsafe_allow_html=True,
            )

        with evaluation_col:
            evaluation_html = (
                '<span class="job-row-ai '
                f'{evaluation_class}">'
                f'{escape(str(evaluation_text))}'
                '</span>'
                f'{coverage_html}'
            )

            st.markdown(
                evaluation_html,
                unsafe_allow_html=True,
            )

        with status_col:
            status_html = (
                '<span class="job-row-decision '
                f'{decision_class}">'
                f'{escape(str(decision_text))}'
                '</span>'
                '<p class="job-row-source">'
                f'{escape(str(source_text))}'
                '</p>'
            )

            st.markdown(
                status_html,
                unsafe_allow_html=True,
            )

        with action_col:
            edit_col, delete_col = (
                st.columns(
                    2,
                    gap="small",
                )
            )

            with edit_col:
                if st.button(
                    "編集",
                    key=f"edit_job_{job_id}",
                    width="stretch",
                ):
                    st.session_state[
                        JOB_FORM_RETURN_PAGE_KEY
                    ] = "job_list"

                    load_job_for_edit(
                        job_id
                    )

                    move_to_page(
                        "job_registration"
                    )

            with delete_col:
                if st.button(
                    "削除",
                    key=f"delete_job_{job_id}",
                    width="stretch",
                ):
                    st.session_state[
                        JOB_DELETE_CONFIRM_KEY
                    ] = job_id

                    st.rerun()

        render_delete_confirmation(
            job_id=job_id,
            company_name=company_name,
            job_name=job_name,
        )

    return selected


def get_salary_minimum(
    job,
) -> int:
    """年収下限を並び替え用の数値に変換する。"""

    salary_text = (
        job.expected_salary_min
        or job.annual_salary
        or ""
    )

    number_text = "".join(
        character
        for character in str(salary_text)
        if character.isdigit()
    )

    if not number_text:
        return 0

    try:
        return int(number_text)

    except ValueError:
        return 0


def render_recommendation_candidate(
    rank: int,
    job_id: int,
    job,
    evaluation,
) -> str:
    """AIおすすめ求人のカードを表示する。"""

    company_name = escape(
        str(
            job.company_name
            or "会社名未入力"
        )
    )

    job_name = escape(
        str(
            job.job_title
            or job.occupation
            or "求人名未入力"
        )
    )

    overall_score = (
        evaluation.overall_score
        if evaluation.overall_score
        is not None
        else 0
    )

    star_fill_percentage = max(
        0,
        min(
            100,
            int(overall_score),
        ),
    )

    def build_category_html(
        category_name: str,
        category_score,
    ) -> str:
        """カテゴリごとの点数行を作成する。"""

        if category_score is None:
            score_text = "未評価"
            score_class = (
                "job-recommendation-category-score "
                "is-unrated"
            )

        else:
            score_text = (
                f"{category_score}点"
            )
            score_class = (
                "job-recommendation-category-score"
            )

        return (
            '<div class="job-recommendation-category">'
            '<span class="'
            'job-recommendation-category-name'
            '">'
            f'{escape(category_name)}'
            '</span>'
            f'<span class="{score_class}">'
            f'{escape(score_text)}'
            '</span>'
            '</div>'
        )

    category_html = "".join(
        [
            build_category_html(
                "希望条件",
                evaluation.hope_condition_score,
            ),
            build_category_html(
                "就活の軸",
                evaluation.work_value_score,
            ),
            build_category_html(
                "職務経歴・スキル",
                evaluation.career_skill_score,
            ),
            build_category_html(
                "必須条件",
                evaluation.required_condition_score,
            ),
        ]
    )

    provisional_html = ""

    if evaluation.is_provisional:
        provisional_html = (
            '<span class="'
            'job-recommendation-provisional'
            '">'
            '暫定評価'
            '</span>'
        )

    coverage = (
        evaluation.evaluation_coverage
        if evaluation.evaluation_coverage
        is not None
        else 0
    )

    if coverage < 100:
        coverage_description = (
            "プロフィール・希望条件の入力で"
            "評価範囲が広がります。"
        )

    else:
        coverage_description = (
            "登録済みの評価情報を"
            "すべて使用しています。"
        )

    detail_url = (
        f"?page=job_detail&job_id={job_id}"
    )

    info_icon_uri = svg_data_uri("info.svg")

    card_html = (
        '<div class="job-recommendation-card">'
        '<div class="job-recommendation-header">'
        '<span class="job-recommendation-rank">'
        f'{rank}位'
        '</span>'
        f'{provisional_html}'
        '</div>'
        '<p class="job-recommendation-company">'
        f'{company_name}'
        '</p>'
        '<p class="job-recommendation-name">'
        f'{job_name}'
        '</p>'
        '<div class="job-recommendation-score-area">'
        '<div class="job-recommendation-score-label">'
        'AI総合マッチ度'
        '</div>'
        '<div class="job-recommendation-score">'
        f'{overall_score}点'
        '<span class="job-recommendation-score-max">'
        '/ 100'
        '</span>'
        '</div>'
        '<div class="job-recommendation-stars" '
        'aria-label="AIマッチ度">'
        '<span>★★★★★</span>'
        '<span class="job-recommendation-stars-fill" '
        f'style="width:{star_fill_percentage}%;">'
        '★★★★★'
        '</span>'
        '</div>'
        '</div>'
        '<div class="job-recommendation-categories">'
        f'{category_html}'
        '</div>'
        '<div class="job-recommendation-coverage">'
        '<p class="job-recommendation-coverage-title">'
        '<img class="job-inline-info-icon" '
        f'src="{info_icon_uri}" alt="">'
        '<span>評価できた情報 '
        f'{coverage}%'
        '</span>'
        '</p>'
        '<p class="'
        'job-recommendation-coverage-description'
        '">'
        f'{escape(coverage_description)}'
        '</p>'
        '</div>'
        '<a class="job-recommendation-detail" '
        f'href="{detail_url}" '
        'target="_self">'
        '詳細を見る'
        '</a>'
        '</div>'
    )

    return card_html


def show_page() -> None:
    """求人一覧画面を表示する。"""

    render_job_navigation(
        "job_list"
    )

    info_icon_uri = svg_data_uri("info.svg")
    guide_icon_uri = svg_data_uri("guide.svg")
    notification_icon_uri = svg_data_uri("notification.svg")
    plus_icon_uri = svg_data_uri("plus.svg")
    chevron_left_uri = svg_data_uri("chevron-left.svg")
    chevron_right_uri = svg_data_uri("chevron-right.svg")

    if (
        JOB_DELETE_CONFIRM_KEY
        not in st.session_state
    ):
        st.session_state[
            JOB_DELETE_CONFIRM_KEY
        ] = None

    if (
        JOB_COMPARE_SELECTED_KEY
        not in st.session_state
    ):
        st.session_state[
            JOB_COMPARE_SELECTED_KEY
        ] = []

    if (
        JOB_LIST_PAGE_KEY
        not in st.session_state
    ):
        st.session_state[
            JOB_LIST_PAGE_KEY
        ] = 1

    stale_job_ids = (
        load_current_user_stale_job_ids()
    )

    stale_signature = tuple(
        stale_job_ids
    )

    previous_stale_signature = (
        st.session_state.get(
            JOB_STALE_REFRESH_SIGNATURE_KEY
        )
    )

    if (
        stale_job_ids
        and previous_stale_signature
        != stale_signature
    ):
        st.session_state[
            JOB_STALE_REFRESH_SIGNATURE_KEY
        ] = stale_signature

        queued_count = enqueue_stale_job_evaluations()
        if queued_count > 0:
            st.info(
                f"{queued_count}件の求人についてAIがマッチ度を確認しています。"
                "ほかの操作を続けられます。"
            )

    if not stale_job_ids:
        st.session_state[
            JOB_STALE_REFRESH_SIGNATURE_KEY
        ] = ()

    jobs = load_jobs()

    evaluations = (
        load_job_match_evaluations()
    )

    for evaluated_job_id, current_evaluation in evaluations.items():
        if current_evaluation.evaluation_status == "failed":
            retry_col, retry_button_col = st.columns([5, 1.4], vertical_alignment="center")
            with retry_col:
                st.warning(
                    "AI評価を完了できませんでした。求人情報は保存されています。"
                )
            with retry_button_col:
                if st.button(
                    "再試行",
                    key=f"retry_ai_result_{evaluated_job_id}",
                    use_container_width=True,
                ):
                    enqueue_job_evaluation(evaluated_job_id, retry=True)
                    st.rerun()

    decisions = (
        load_job_application_decisions()
    )

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1380px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e4eaf2;
            border-radius: 12px;
            padding: 16px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #ffffff;
            border-color: #dfe6f0;
            border-radius: 12px;
        }

        .stButton > button[kind="primary"] {
            background: #1268f3;
            border-color: #1268f3;
        }
        .job-pending-notice {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            margin: 12px 0 14px;
            padding: 20px 24px;
            background: #fffaf0;
            border: 1px solid #f6c85f;
            border-radius: 12px;
        }

        .job-pending-notice-main {
            display: flex;
            align-items: flex-start;
            gap: 14px;
        }

        .job-pending-notice-icon {
            display: flex;
            flex: 0 0 30px;
            align-items: center;
            justify-content: center;
            color: #f59e0b;
            font-size: 21px;
            line-height: 1;
        }

        .job-pending-notice-title {
            margin: 0 0 6px;
            color: #c45a05;
            font-size: 18px;
            font-weight: 800;
        }

        .job-pending-notice-description {
            margin: 0;
            color: #53627a;
            font-size: 14px;
        }

        .job-pending-notice-count {
            min-width: 100px;
            padding-left: 20px;
            color: #c45a05;
            border-left: 1px solid #f6d994;
            text-align: center;
            white-space: nowrap;
        }

        .job-pending-notice-count strong {
            display: block;
            font-size: 28px;
            line-height: 1.2;
        }

        .job-pending-notice-count span {
            font-size: 12px;
        }
                .job-detail-link {
            color: #1268f3 !important;
            font-weight: 700;
            line-height: 1.5;
            text-decoration: none !important;
        }

        .job-detail-link:hover {
            color: #0759d9 !important;
            text-decoration: underline !important;
        }

        /* 求人一覧画面全体 */
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: #f7f9fc;
        }

        .stApp {
            font-family:
                "Yu Gothic",
                "YuGothic",
                "Hiragino Kaku Gothic ProN",
                "Hiragino Sans",
                "Meiryo",
                sans-serif;
            color: #10213d;
        }

        [data-testid="stHeader"] {
            background: rgba(247, 249, 252, 0.92);
        }

        /* AIおすすめ求人カード */
        .job-recommendation-card {
            height: 100%;
            min-height: 470px;
            display: flex;
            flex-direction: column;
            padding: 20px;
            overflow: hidden;
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 14px;
            box-shadow:
                0 6px 18px rgba(16, 33, 61, 0.06);
        }

        .job-recommendation-card:hover {
            border-color: #b8cdf2;
            box-shadow:
                0 10px 24px rgba(18, 104, 243, 0.10);
            transform: translateY(-2px);
            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease,
                transform 0.2s ease;
        }

        .job-recommendation-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 14px;
        }

        .job-recommendation-rank {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 28px;
            height: 28px;
            padding: 0 8px;
            background: #ffb21c;
            border-radius: 7px;
            color: #ffffff;
            font-size: 13px;
            font-weight: 700;
            line-height: 1;
        }

        .job-recommendation-provisional {
            display: inline-flex;
            align-items: center;
            min-height: 24px;
            padding: 2px 9px;
            background: #eef5ff;
            border: 1px solid #cfe1ff;
            border-radius: 999px;
            color: #356697;
            font-size: 11px;
            font-weight: 700;
        }

        .job-recommendation-company {
            margin: 0 0 5px;
            color: #10213d;
            font-size: 17px;
            font-weight: 700;
            line-height: 1.5;
        }

        .job-recommendation-name {
            min-height: 42px;
            margin: 0 0 14px;
            color: #7b8798;
            font-size: 13px;
            line-height: 1.6;
        }

        .job-recommendation-score-area {
            padding: 12px 14px 11px;
            margin-bottom: 14px;
            background: #f8fbff;
            border: 1px solid #dce8fa;
            border-radius: 11px;
            text-align: center;
        }

        .job-recommendation-score-label {
            margin-bottom: 2px;
            color: #536177;
            font-size: 12px;
            font-weight: 600;
        }

        .job-recommendation-score {
            color: #1268f3;
            font-size: 36px;
            font-weight: 750;
            letter-spacing: -1px;
            line-height: 1.15;
        }

        .job-recommendation-score-max {
            margin-left: 3px;
            color: #7b8798;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0;
        }

        /* マッチ度を示す星。お気に入りボタンではない */
        .job-recommendation-stars {
            position: relative;
            display: inline-block;
            margin-top: 5px;
            color: #d9e1ec;
            font-size: 18px;
            line-height: 1;
            letter-spacing: 2px;
            white-space: nowrap;
        }

        .job-recommendation-stars-fill {
            position: absolute;
            top: 0;
            left: 0;
            display: block;
            overflow: hidden;
            color: #1268f3;
            white-space: nowrap;
        }

        .job-recommendation-categories {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 14px;
        }

        .job-recommendation-category {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            padding-bottom: 7px;
            border-bottom: 1px solid #edf1f6;
        }

        .job-recommendation-category:last-child {
            padding-bottom: 0;
            border-bottom: 0;
        }

        .job-recommendation-category-name {
            color: #657187;
            font-size: 12px;
            line-height: 1.4;
        }

        .job-recommendation-category-score {
            flex-shrink: 0;
            color: #26334d;
            font-size: 13px;
            font-weight: 700;
        }

        .job-recommendation-category-score.is-unrated {
            color: #a3adba;
            font-weight: 500;
        }

        .job-recommendation-coverage {
            padding: 9px 10px;
            margin-top: auto;
            margin-bottom: 12px;
            background: #eef6ff;
            border: 1px solid #d8eaff;
            border-radius: 9px;
        }

        .job-recommendation-coverage-title {
            display: flex;
            align-items: center;
            gap: 5px;
            margin: 0 0 3px;
            color: #1268f3;
            font-size: 12px;
            font-weight: 700;
        }

        .job-inline-info-icon {
            display: block;
            flex: 0 0 16px;
            width: 16px;
            height: 16px;
        }

        .job-recommendation-coverage-description {
            margin: 0;
            color: #52647e;
            font-size: 11px;
            line-height: 1.55;
        }

        .job-recommendation-detail {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 40px;
            padding: 8px 14px;
            box-sizing: border-box;
            background: #1268f3;
            border: 1px solid #1268f3;
            border-radius: 8px;
            color: #ffffff !important;
            font-size: 13px;
            font-weight: 700;
            text-decoration: none !important;
            box-shadow:
                0 4px 10px rgba(18, 104, 243, 0.20);
        }

        .job-recommendation-detail:hover {
            background: #0759d9;
            border-color: #0759d9;
            color: #ffffff !important;
            text-decoration: none !important;
            box-shadow:
                0 6px 14px rgba(18, 104, 243, 0.28);
        }

        @media (max-width: 900px) {
            .job-recommendation-card {
                min-height: auto;
            }
        }

        /* 求人一覧カード */
        .job-list-card-marker {
            display: block;
            width: 0;
            height: 0;
            overflow: hidden;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-list-card-marker
        ) {
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 13px;
            box-shadow:
                0 3px 12px rgba(16, 33, 61, 0.045);
            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-list-card-marker
        ):hover {
            border-color: #bfd1ee;
            box-shadow:
                0 7px 18px rgba(16, 33, 61, 0.075);
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-list-card-marker
        ) label[data-testid="stWidgetLabel"] {
            color: #536177;
            font-size: 12px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-list-card-marker
        ) .stButton > button {
            min-height: 36px;
            border-color: #d5deea;
            border-radius: 8px;
            background: #ffffff;
            color: #41516b;
            font-size: 12px;
            font-weight: 600;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-list-card-marker
        ) .stButton > button:hover {
            border-color: #9db8e5;
            background: #f5f9ff;
            color: #0759d9;
        }

        .job-list-company-link {
            display: inline-block;
            margin-bottom: 5px;
            color: #1268f3 !important;
            font-size: 15px;
            font-weight: 750;
            line-height: 1.5;
            text-decoration: none !important;
        }

        .job-list-company-link:hover {
            color: #0759d9 !important;
            text-decoration: underline !important;
        }

        .job-list-id {
            margin: 0;
            color: #98a3b2;
            font-size: 11px;
            line-height: 1.4;
        }

        .job-list-primary-value {
            margin: 0 0 5px;
            color: #1c2b45;
            font-size: 14px;
            font-weight: 650;
            line-height: 1.5;
        }

        .job-list-secondary-value {
            margin: 0;
            color: #7b8798;
            font-size: 12px;
            line-height: 1.55;
        }

        .job-list-source-list {
            margin: 0 0 8px;
            color: #465570;
            font-size: 12px;
            line-height: 1.55;
        }

        .job-list-source-item {
            margin-bottom: 2px;
        }

        .job-list-ai-score {
            display: inline-flex;
            align-items: center;
            min-height: 26px;
            padding: 3px 9px;
            margin-top: 6px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 750;
            line-height: 1;
        }

        .job-list-ai-score.is-scored {
            background: #eaf3ff;
            color: #1268f3;
        }

        .job-list-ai-score.is-pending {
            background: #fff6df;
            color: #a86100;
        }

        .job-list-ai-score.is-unrated {
            background: #f0f2f5;
            color: #7f8a99;
        }

        .job-list-decision {
            display: inline-flex;
            align-items: center;
            min-height: 26px;
            padding: 3px 9px;
            border: 1px solid transparent;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            line-height: 1;
        }

        .job-list-decision.is-unhandled {
            background: #fff6df;
            border-color: #ffe0a3;
            color: #a86100;
        }

        .job-list-decision.is-positive {
            background: #e8f8ef;
            border-color: #bee8ce;
            color: #138847;
        }

        .job-list-decision.is-negative {
            background: #fff0f1;
            border-color: #f5c8cc;
            color: #c43742;
        }

        .job-list-decision.is-hold {
            background: #eaf3ff;
            border-color: #c7dcfb;
            color: #1268f3;
        }

        .job-list-decision.is-other {
            background: #f1efff;
            border-color: #d7d1ff;
            color: #6554c0;
        }

        .job-list-table-heading {
            color: #7b8798;
            font-size: 11px;
            font-weight: 650;
            letter-spacing: 0.01em;
        }

        @media (max-width: 900px) {
            .job-list-company-link {
                font-size: 14px;
            }
        }
                /* コンパクトな求人一覧 */
        .job-row-marker {
            display: block;
            width: 0;
            height: 0;
            overflow: hidden;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) {
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 12px;
            box-shadow:
                0 2px 9px rgba(16, 33, 61, 0.04);
            transition:
                border-color 0.2s ease,
                box-shadow 0.2s ease;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ):hover {
            border-color: #b8cdf2;
            box-shadow:
                0 6px 15px rgba(16, 33, 61, 0.07);
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) div[data-testid="stVerticalBlock"] {
            gap: 0.45rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) .stButton > button {
            min-height: 34px;
            padding: 4px 8px;
            border-color: #d7dfe9;
            border-radius: 7px;
            background: #ffffff;
            color: #465570;
            font-size: 11px;
            font-weight: 650;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) .stButton > button:hover {
            border-color: #9db8e5;
            background: #f5f9ff;
            color: #0759d9;
        }

        .job-row-table-heading {
            padding-bottom: 3px;
            color: #7b8798;
            font-size: 11px;
            font-weight: 650;
            letter-spacing: 0.01em;
            white-space: nowrap;
        }

        .job-row-company-link {
            display: block;
            margin: 0 0 4px;
            color: #1268f3 !important;
            font-size: 14px;
            font-weight: 750;
            line-height: 1.45;
            text-decoration: none !important;
        }

        .job-row-company-link:hover {
            color: #0759d9 !important;
            text-decoration: underline !important;
        }

        .job-row-company-link.is-disabled,
        .job-row-company-link.is-disabled:hover {
            color: #6f7c90 !important;
            cursor: default;
            text-decoration: none !important;
        }

        .job-row-job-name {
            display: -webkit-box;
            margin: 0;
            overflow: hidden;
            color: #6f7c90;
            font-size: 11px;
            line-height: 1.5;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 2;
        }

        .job-row-primary {
            margin: 0 0 3px;
            color: #22314a;
            font-size: 13px;
            font-weight: 650;
            line-height: 1.45;
        }

        .job-row-secondary {
            margin: 0;
            color: #7b8798;
            font-size: 11px;
            line-height: 1.45;
        }

        .job-row-salary {
            margin: 0;
            color: #22314a;
            font-size: 13px;
            font-weight: 650;
            line-height: 1.45;
        }

        .job-row-ai {
            display: inline-flex;
            align-items: center;
            min-height: 25px;
            padding: 3px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 750;
            line-height: 1;
            white-space: nowrap;
        }

        .job-row-ai.is-scored {
            background: #eaf3ff;
            color: #1268f3;
        }

        .job-row-ai.is-pending {
            background: #fff6df;
            color: #a86100;
        }

        .job-row-ai.is-unrated {
            background: #f0f2f5;
            color: #7f8a99;
        }

        .job-row-decision {
            display: inline-flex;
            align-items: center;
            min-height: 25px;
            max-width: 100%;
            padding: 3px 8px;
            overflow: hidden;
            border: 1px solid transparent;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            line-height: 1;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .job-row-decision.is-unhandled {
            background: #fff6df;
            border-color: #ffe0a3;
            color: #a86100;
        }

        .job-row-decision.is-positive {
            background: #eef5ff;
            border-color: #cfe1ff;
            color: #285f9b;
        }

        .job-row-decision.is-negative {
            background: #fff0f1;
            border-color: #f5c8cc;
            color: #c43742;
        }

        .job-row-decision.is-hold {
            background: #eaf3ff;
            border-color: #c7dcfb;
            color: #1268f3;
        }

        .job-row-decision.is-other {
            background: #f1efff;
            border-color: #d7d1ff;
            color: #6554c0;
        }

        .job-row-source {
            margin: 5px 0 0;
            overflow: hidden;
            color: #7b8798;
            font-size: 10px;
            line-height: 1.4;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        @media (max-width: 900px) {
            .job-row-table-heading {
                white-space: normal;
            }

            .job-row-company-link {
                font-size: 13px;
            }
        }
                /* 求人一覧画面の表示密度を基準UIへ近づける */
        .block-container {
            max-width: 1320px;
            padding-top: 1.25rem;
            padding-bottom: 2.5rem;
        }

        .stApp h1 {
            margin-bottom: 0.2rem;
            color: #10213d;
            font-size: 34px !important;
            font-weight: 750;
            letter-spacing: -0.03em;
            line-height: 1.25;
        }

        .stApp h2 {
            color: #10213d;
            font-size: 24px !important;
            font-weight: 750;
            letter-spacing: -0.02em;
            line-height: 1.35;
        }

        .stApp h3 {
            margin-top: 0.5rem;
            margin-bottom: 0.2rem;
            color: #10213d;
            font-size: 22px !important;
            font-weight: 750;
            letter-spacing: -0.02em;
            line-height: 1.35;
        }

        .stApp [data-testid="stCaptionContainer"] {
            color: #7b8798;
            font-size: 11px;
            line-height: 1.5;
        }

        /* 管理通知をコンパクト化 */
        .job-pending-notice {
            gap: 18px;
            margin: 10px 0 22px;
            padding: 14px 18px;
            border-radius: 10px;
        }

        .job-pending-notice-main {
            gap: 11px;
        }

        .job-pending-notice-icon {
            font-size: 22px;
        }

        .job-pending-notice-title {
            margin-bottom: 3px;
            font-size: 14px;
            font-weight: 750;
        }

        .job-pending-notice-description {
            font-size: 12px;
            line-height: 1.5;
        }

        .job-pending-notice-count {
            min-width: 82px;
            padding-left: 16px;
        }

        .job-pending-notice-count strong {
            font-size: 23px;
        }

        .job-pending-notice-count span {
            font-size: 10px;
        }

        /* TOP3カードの表示密度 */
        .job-recommendation-card {
            min-height: 405px;
            padding: 15px;
            border-radius: 10px;
            box-shadow:
                0 3px 12px rgba(16, 33, 61, 0.05);
        }

        .job-recommendation-card:hover {
            box-shadow:
                0 7px 17px rgba(18, 104, 243, 0.09);
        }

        .job-recommendation-header {
            margin-bottom: 10px;
        }

        .job-recommendation-rank {
            min-width: 25px;
            height: 25px;
            padding: 0 7px;
            border-radius: 6px;
            font-size: 11px;
        }

        .job-recommendation-provisional {
            min-height: 21px;
            padding: 1px 7px;
            font-size: 10px;
        }

        .job-recommendation-company {
            margin-bottom: 3px;
            font-size: 14px;
            line-height: 1.45;
        }

        .job-recommendation-name {
            min-height: 34px;
            margin-bottom: 10px;
            font-size: 11px;
            line-height: 1.5;
        }

        .job-recommendation-score-area {
            padding: 9px 12px 8px;
            margin-bottom: 10px;
            border-radius: 9px;
        }

        .job-recommendation-score-label {
            font-size: 10px;
        }

        .job-recommendation-score {
            font-size: 32px;
            letter-spacing: -1px;
        }

        .job-recommendation-score-max {
            font-size: 10px;
        }

        .job-recommendation-stars {
            margin-top: 3px;
            font-size: 16px;
            letter-spacing: 1.5px;
        }

        .job-recommendation-categories {
            gap: 4px;
            margin-bottom: 9px;
        }

        .job-recommendation-category {
            padding-bottom: 5px;
        }

        .job-recommendation-category-name {
            font-size: 10.5px;
        }

        .job-recommendation-category-score {
            font-size: 11px;
        }

        .job-recommendation-coverage {
            padding: 7px 8px;
            margin-bottom: 9px;
            border-radius: 8px;
        }

        .job-recommendation-coverage-title {
            margin-bottom: 2px;
            font-size: 10.5px;
        }

        .job-recommendation-coverage-description {
            font-size: 10px;
            line-height: 1.45;
        }

        .job-recommendation-detail {
            min-height: 34px;
            padding: 6px 12px;
            border-radius: 7px;
            font-size: 11px;
        }

        /* 検索・絞り込み */
        div[data-testid="stTextInput"] label,
        div[data-testid="stSelectbox"] label {
            color: #536177;
            font-size: 11px;
            font-weight: 650;
        }

        div[data-testid="stTextInput"] input {
            min-height: 37px;
            padding-top: 6px;
            padding-bottom: 6px;
            background: #f1f4f8;
            border-color: #e1e7ef;
            font-size: 12px;
        }

        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height: 37px;
            background: #f1f4f8;
            border-color: #e1e7ef;
            font-size: 12px;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #1268f3;
            box-shadow:
                0 0 0 1px #1268f3;
        }

        /* 通常ボタンの高さ */
        .stButton > button {
            min-height: 36px;
            border-radius: 7px;
            font-size: 12px;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-top: 1rem;
            }

            .stApp h1 {
                font-size: 30px !important;
            }

            .job-recommendation-card {
                min-height: auto;
            }
        }
                /* TOP3カードの高さを統一 */
        .job-recommendation-card {
            height: 420px;
            min-height: 420px;
            box-sizing: border-box;
        }

        .job-recommendation-name {
            display: -webkit-box;
            height: 34px;
            min-height: 34px;
            overflow: hidden;
            overflow-wrap: anywhere;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 2;
        }

        /* 通常一覧では求人名を省略しない */
        .job-row-job-name {
            display: block;
            overflow: visible;
            overflow-wrap: anywhere;
            color: #6f7c90;
            white-space: normal;
            -webkit-box-orient: initial;
            -webkit-line-clamp: initial;
        }

        /* 紹介元も省略せずに折り返す */
        .job-row-source {
            margin-top: 6px;
            overflow: visible;
            overflow-wrap: anywhere;
            color: #7b8798;
            white-space: normal;
            text-overflow: initial;
        }

        .job-row-decision {
            margin-bottom: 1px;
        }

        /* 各列の情報が接近しすぎないようにする */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) div[data-testid="column"] {
            min-width: 0;
        }

        @media (max-width: 900px) {
            .job-recommendation-card {
                height: auto;
                min-height: auto;
            }
        }
                /* TOP3を高さが揃うHTMLグリッドにする */
        .job-recommendation-grid {
            display: grid;
            grid-template-columns:
                repeat(3, minmax(0, 1fr));
            align-items: stretch;
            gap: 16px;
            width: 100%;
        }

        .job-recommendation-card {
            width: 100%;
            height: 100%;
            min-height: 0;
            box-sizing: border-box;
            overflow: visible;
        }

        .job-recommendation-name {
            display: -webkit-box;
            height: auto;
            min-height: 50px;
            max-height: 50px;
            overflow: hidden;
            overflow-wrap: anywhere;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 3;
        }

        .job-recommendation-coverage {
            margin-top: auto;
        }

        .job-recommendation-coverage-title {
            font-size: 10px;
            line-height: 1.35;
        }

        .job-recommendation-coverage-description {
            font-size: 9.5px;
            line-height: 1.4;
        }

        /* 通常一覧の文字階層を再調整 */
        .job-row-company-link {
            margin-bottom: 5px;
            font-size: 14px;
            font-weight: 750;
        }

        .job-row-job-name {
            color: #526177;
            font-size: 12px;
            font-weight: 500;
            line-height: 1.5;
        }

        .job-row-primary {
            margin-bottom: 4px;
            color: #17233c;
            font-size: 13px;
            font-weight: 700;
        }

        .job-row-secondary {
            color: #718096;
            font-size: 11px;
            line-height: 1.45;
        }

        .job-row-salary {
            color: #17233c;
            font-size: 13px;
            font-weight: 700;
        }

        /* AI評価を現在より強調 */
        .job-row-ai {
            min-height: 30px;
            padding: 5px 11px;
            font-size: 12px;
            font-weight: 800;
        }

        .job-row-decision {
            min-height: 27px;
            padding: 4px 9px;
            font-size: 11px;
        }

        .job-row-source {
            margin-top: 7px;
            color: #657187;
            font-size: 11px;
            line-height: 1.45;
        }

        /* 編集・削除を必ず横書きにする */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) .stButton > button {
            min-width: 0;
            min-height: 34px;
            padding: 4px 6px;
            font-size: 11px;
            line-height: 1;
            word-break: keep-all !important;
            white-space: nowrap !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) .stButton > button p {
            word-break: keep-all !important;
            white-space: nowrap !important;
        }

        @media (max-width: 900px) {
            .job-recommendation-grid {
                grid-template-columns: 1fr;
            }

            .job-recommendation-name {
                min-height: auto;
                max-height: none;
            }
        }
                /* TOP3の求人名を全文表示する */
        .job-recommendation-name {
            display: block;
            height: auto;
            min-height: 52px;
            max-height: none;
            overflow: visible;
            overflow-wrap: anywhere;
            white-space: normal;
            -webkit-box-orient: initial;
            -webkit-line-clamp: initial;
        }

        /* 求人一覧カードの余白を縮める */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) {
            border-radius: 9px;
            box-shadow: none;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) > div[data-testid="stVerticalBlock"] {
            gap: 0.25rem;
            padding: 0.7rem 0.8rem;
        }

        .job-row-company-link {
            margin-bottom: 3px;
            font-size: 14px;
            line-height: 1.35;
        }

        .job-row-job-name {
            margin: 0;
            color: #526177;
            font-size: 11.5px;
            font-weight: 500;
            line-height: 1.4;
        }

        .job-row-primary {
            margin-bottom: 2px;
            font-size: 12.5px;
            line-height: 1.35;
        }

        .job-row-secondary {
            font-size: 10.5px;
            line-height: 1.35;
        }

        .job-row-ai {
            min-height: 31px;
            padding: 5px 11px;
            font-size: 13px;
        }

        .job-row-ai-coverage {
            margin: 5px 0 0;
            color: #657187;
            font-size: 10px;
            font-weight: 600;
            line-height: 1.3;
            white-space: nowrap;
        }

        .job-row-decision {
            min-height: 26px;
            padding: 4px 9px;
            font-size: 11px;
        }

        .job-row-source {
            margin-top: 5px;
            color: #657187;
            font-size: 10.5px;
            line-height: 1.35;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) .stButton > button {
            min-height: 32px;
            padding: 3px 6px;
            font-size: 11px;
            word-break: keep-all !important;
            white-space: nowrap !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) .stButton > button p {
            word-break: keep-all !important;
            white-space: nowrap !important;
        }
                /* 説明文を読める大きさへ戻す */
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] p {
            color: #718096 !important;
            font-size: 12px !important;
            font-weight: 400 !important;
            line-height: 1.55 !important;
        }

        /* 求人一覧の列見出し */
        .job-row-table-heading {
            color: #657187 !important;
            font-size: 11.5px !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
        }

        /* 最重要情報：会社名 */
        .job-row-company-link {
            margin: 0 0 4px !important;
            color: #1268f3 !important;
            font-size: 15px !important;
            font-weight: 750 !important;
            line-height: 1.4 !important;
        }

        /* 補足情報：求人名 */
        .job-row-job-name {
            margin: 0 !important;
            color: #526177 !important;
            font-size: 12px !important;
            font-weight: 450 !important;
            line-height: 1.45 !important;
        }

        /* 職種 */
        .job-row-primary {
            margin: 0 0 3px !important;
            color: #1c2b45 !important;
            font-size: 12.5px !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
        }

        /* 勤務地 */
        .job-row-secondary {
            margin: 0 !important;
            color: #718096 !important;
            font-size: 11.5px !important;
            font-weight: 400 !important;
            line-height: 1.4 !important;
        }

        /* AI評価：会社名に次ぐ重要情報 */
        .job-row-ai {
            min-height: 31px !important;
            padding: 5px 11px !important;
            font-size: 13px !important;
            font-weight: 800 !important;
            line-height: 1 !important;
        }

        .job-row-ai-coverage {
            margin: 5px 0 0 !important;
            color: #657187 !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            line-height: 1.35 !important;
        }

        /* 応募状況 */
        .job-row-decision {
            min-height: 27px !important;
            padding: 4px 9px !important;
            font-size: 11.5px !important;
            font-weight: 700 !important;
            line-height: 1 !important;
        }

        /* 紹介元 */
        .job-row-source {
            margin: 6px 0 0 !important;
            color: #657187 !important;
            font-size: 11px !important;
            font-weight: 400 !important;
            line-height: 1.4 !important;
        }

        /* 編集・削除 */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(
            .job-row-marker
        ) .stButton > button {
            min-height: 32px !important;
            font-size: 11.5px !important;
            font-weight: 600 !important;
        }

        /* TOP3の会社名と求人名も同じ階層へ統一 */
        .job-recommendation-company {
            color: #10213d !important;
            font-size: 15px !important;
            font-weight: 750 !important;
            line-height: 1.4 !important;
        }

        .job-recommendation-name {
            color: #657187 !important;
            font-size: 12px !important;
            font-weight: 450 !important;
            line-height: 1.5 !important;
        }
                /* 求人一覧画面：タイポグラフィ最終調整 */

        /* ページタイトルや各セクションの説明文 */
        /* ページやセクションの説明文 */
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] p {
            color: #5f6f86 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            line-height: 1.6 !important;
        }

        /* TOP3：カテゴリ名 */
        .job-recommendation-category-name {
            color: #657187 !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            line-height: 1.45 !important;
        }

        /* TOP3：カテゴリの点数・未評価 */
        .job-recommendation-category-score {
            color: #26334d !important;
            font-size: 12px !important;
            font-weight: 700 !important;
            line-height: 1.45 !important;
        }

        .job-recommendation-category-score.is-unrated {
            color: #8d99aa !important;
            font-weight: 500 !important;
        }

        /* TOP3：評価カバー率の見出し */
        .job-recommendation-coverage-title {
            color: #1268f3 !important;
            font-size: 12.5px !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
        }

        /* TOP3：評価カバー率の説明文 */
        .job-recommendation-coverage-description {
            color: #52647e !important;
            font-size: 12px !important;
            font-weight: 400 !important;
            line-height: 1.5 !important;
        }

        /* 通常一覧：列見出し */
        .job-row-table-heading {
            color: #657187 !important;
            font-size: 12.5px !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
        }

        /* 通常一覧：求人名 */
        .job-row-job-name {
            margin: 0 !important;
            color: #526177 !important;
            font-size: 12.5px !important;
            font-weight: 500 !important;
            line-height: 1.5 !important;
        }

        /* 通常一覧：職種 */
        .job-row-primary {
            margin: 0 0 4px !important;
            color: #1c2b45 !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            line-height: 1.45 !important;
        }

        /* 通常一覧：勤務地 */
        .job-row-secondary {
            margin: 0 !important;
            color: #657187 !important;
            font-size: 12px !important;
            font-weight: 400 !important;
            line-height: 1.45 !important;
        }

        /* 通常一覧：評価カバー率 */
        .job-row-ai-coverage {
            margin: 6px 0 0 !important;
            color: #526987 !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            line-height: 1.4 !important;
        }

        /* 通常一覧：紹介元 */
        .job-row-source {
            margin: 6px 0 0 !important;
            color: #657187 !important;
            font-size: 12px !important;
            font-weight: 400 !important;
            line-height: 1.45 !important;
        }
            /* keyを使って求人一覧カードを白背景に固定する */
        div[class*="st-key-job_row_card_"] {
            background: #ffffff !important;
            background-color: #ffffff !important;
            background-image: none !important;
        }

        div[class*="st-key-job_row_card_"]
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[class*="st-key-job_row_card_"]
        div[data-testid="stVerticalBlock"],
        div[class*="st-key-job_row_card_"]
        div[data-testid="stHorizontalBlock"],
        div[class*="st-key-job_row_card_"]
        div[data-testid="column"] {
            background: #ffffff !important;
            background-color: #ffffff !important;
            background-image: none !important;
        }

        /* ページ外周はトップ画面と同じ背景色を維持する */
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background-color: #f7f9fc !important;
        }
                /* 求人一覧の最下部に表示する使い方案内 */
        .job-list-usage-guide {
            display: flex;
            align-items: flex-start;
            gap: 14px;
            margin: 0 0 28px;
            padding: 18px 20px;
            background: #ffffff;
            border: 1px solid #dfe6f0;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(16, 33, 61, 0.04);
        }

        .job-list-usage-guide-icon {
            display: flex;
            flex: 0 0 34px;
            align-items: center;
            justify-content: center;
            min-height: 34px;
            color: #f59e0b;
            font-size: 23px;
            line-height: 1;
        }

        .job-list-usage-guide-body {
            min-width: 0;
        }

        .job-list-usage-guide-title {
            margin: 0 0 5px;
            color: #1c2b45;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.5;
        }

        .job-list-usage-guide-description {
            margin: 0;
            color: #657187;
            font-size: 12.5px;
            font-weight: 400;
            line-height: 1.65;
        }
        /* 応募判断の変更場所を分かりやすい案内帯で表示する */
        .job-list-decision-help {
            display: flex;
            align-items: center;
            gap: 9px;
            margin: 6px 0 14px;
            padding: 10px 13px;
            color: #254b7c;
            background: #eef6ff;
            border: 1px solid #cfe1ff;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            line-height: 1.5;
        }

        .job-list-decision-help-icon {
            display: inline-flex;
            flex: 0 0 22px;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            color: #1268f3;
            background: #ffffff;
            border: 1px solid #b9d3ff;
            border-radius: 50%;
            font-size: 13px;
            font-weight: 700;
            line-height: 1;
        }

        /* Streamlitが見出しへ自動追加するリンク記号は表示しない */
        [data-testid="stHeaderActionElements"],
        .stApp h1 a,
        .stApp h2 a,
        .stApp h3 a {
            display: none !important;
        }

        .job-list-usage-guide-icon img,
        .job-pending-notice-icon img {
            display: block;
            width: 26px;
            height: 26px;
        }

        .job-list-decision-help-icon img {
            display: block;
            width: 16px;
            height: 16px;
        }

        .job-list-back-home {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 7px;
            min-height: 38px;
            padding: 0 15px;
            color: #1268f3 !important;
            background: #ffffff;
            border: 1px solid #8db7ff;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 700;
            line-height: 1;
            text-decoration: none !important;
            transition: background-color 0.18s ease, border-color 0.18s ease;
        }

        .job-list-back-home:hover {
            color: #0759d9 !important;
            background: #f5f9ff;
            border-color: #6fa3ff;
            text-decoration: none !important;
        }

        .job-list-back-home img {
            display: block;
            width: 17px;
            height: 17px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <style>
        .st-key-job_list_registration button::before,
        .st-key-job_list_previous_page button::before,
        .st-key-job_list_next_page button::after,
        .st-key-job_list_back_home button::before {{
            content: "";
            display: inline-block;
            flex: 0 0 17px;
            width: 17px;
            height: 17px;
            background-color: currentColor;
            mask-position: center;
            mask-repeat: no-repeat;
            mask-size: contain;
        }}

        .st-key-job_list_registration button::before {{
            mask-image: url("{plus_icon_uri}");
        }}

        .st-key-job_list_previous_page button::before,
        .st-key-job_list_back_home button::before {{
            mask-image: url("{chevron_left_uri}");
        }}

        .st-key-job_list_next_page button::after {{
            mask-image: url("{chevron_right_uri}");
        }}

        .st-key-job_list_registration button,
        .st-key-job_list_previous_page button,
        .st-key-job_list_next_page button,
        .st-key-job_list_back_home button {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 7px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    header_col, register_col = st.columns(
        [4, 1]
    )

    with header_col:
        st.title("求人一覧")

        st.caption(
            "登録した求人を管理し、"
            "AIマッチ度や比較結果を確認できます。"
        )

    with register_col:
        if st.button(
            "求人を登録する",
            key="job_list_registration",
            type="primary",
            width="stretch",
        ):
            start_new_job_registration()

            move_to_page(
                "job_registration"
            )

    pending_count = sum(
        1
        for job_id, _ in jobs
        if (
            job_id not in decisions
            or not decisions[
                job_id
            ].decision_status.strip()
        )
    )

    pending_notice_html = (
        '<div class="job-pending-notice">'
        '<div class="job-pending-notice-main">'
        '<div class="job-pending-notice-icon" '
        'aria-hidden="true">'
        f'<img src="{notification_icon_uri}" alt="">'
        '</div>'
        '<div>'
        '<p class="job-pending-notice-title">'
        f'応募判断未対応の求人が'
        f'{pending_count}件あります'
        '</p>'
        '<p class="job-pending-notice-description">'
        '求人一覧から内容を確認し、'
        '応募判断を行いましょう。'
        '</p>'
        '</div>'
        '</div>'
        '<div class="job-pending-notice-count">'
        f'<strong>{pending_count}件</strong>'
        '<span>未対応</span>'
        '</div>'
        '</div>'
    )

    if pending_count > 0:
        st.markdown(
            pending_notice_html,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="job-list-usage-guide">
            <div
                class="job-list-usage-guide-icon"
                aria-hidden="true"
            >
                <img src="{guide_icon_uri}" alt="">
            </div>
            <div class="job-list-usage-guide-body">
                <p class="job-list-usage-guide-title">
                    求人一覧の使い方
                </p>
                <p class="job-list-usage-guide-description">
                    会社名を押すと、求人の詳細と
                    AIマッチング結果を確認できます。<br>
                    比較したい求人にチェックを入れると、
                    2～3件の求人を並べて比較できます。
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("AIマッチ度の高い求人")

    st.caption(
        "AI評価が完了している求人から、"
        "総合マッチ度が高い順に3件表示しています。"
    )

    jobs_by_id = {
        job_id: job
        for job_id, job in jobs
    }

    recommendation_evaluations = sorted(
        (
            evaluation
            for job_id, evaluation
            in evaluations.items()
            if (
                job_id in jobs_by_id
                and is_job_match_evaluation_ready(evaluation)
            )
        ),
        key=lambda evaluation: (
            evaluation.overall_score
        ),
        reverse=True,
    )[:3]

    if recommendation_evaluations:
        recommendation_cards = []

        for index, evaluation in enumerate(
            recommendation_evaluations,
            start=1,
        ):
            job_id = evaluation.job_id
            job = jobs_by_id[job_id]

            recommendation_cards.append(
                render_recommendation_candidate(
                    rank=index,
                    job_id=job_id,
                    job=job,
                    evaluation=evaluation,
                )
            )

        recommendation_grid_html = (
            '<div class="job-recommendation-grid">'
            + "".join(recommendation_cards)
            + '</div>'
        )

        st.markdown(
            recommendation_grid_html,
            unsafe_allow_html=True,
        )

    else:
        st.info(
            "AI評価済みの求人はまだありません。"
        )

    st.subheader("求人検索・絞り込み")

    search_keyword = st.text_input(
        "求人を検索",
        placeholder="会社名・求人名・職種・キーワードで検索",
        key="job_list_search_keyword",
    )

    (
        filter_col1,
        filter_col2,
        filter_col3,
        filter_col4,
        decision_filter_col,
        sort_col,
    ) = st.columns(6)

    prefectures = sorted(
        {
            job.prefecture
            for _, job in jobs
            if job.prefecture
        }
    )

    industries = sorted(
        {
            job.industry
            for _, job in jobs
            if job.industry
        }
    )

    source_names = sorted(
        {
            source.source_name
            for job_id, _ in jobs
            for _, source in load_job_sources(job_id)
            if source.source_name
        }
    )

    selected_prefecture_value = st.session_state.get(
        "job_list_filter_prefecture",
        "すべて",
    )
    municipalities = sorted(
        {
            job.municipality
            for _, job in jobs
            if job.municipality
            and (
                selected_prefecture_value == "すべて"
                or job.prefecture == selected_prefecture_value
            )
        }
    )
    if st.session_state.get("job_list_filter_municipality", "すべて") not in [
        "すべて",
        *municipalities,
    ]:
        st.session_state["job_list_filter_municipality"] = "すべて"

    with filter_col1:
        selected_prefecture = st.selectbox(
            "都道府県",
            ["すべて"] + prefectures,
            key="job_list_filter_prefecture",
        )

    with filter_col2:
        selected_municipality = st.selectbox(
            "市区町村",
            ["すべて"] + municipalities,
            key="job_list_filter_municipality",
        )

    with filter_col3:
        selected_industry = st.selectbox(
            "業種",
            ["すべて"] + industries,
            key="job_list_filter_industry",
        )

    with filter_col4:
        selected_source_name = st.selectbox(
            "紹介元",
            ["すべて"] + source_names,
            key="job_list_filter_source_name",
        )

    with decision_filter_col:
        selected_decision = st.selectbox(
            "応募判断",
            [
                "すべて",
                "未対応",
                *APPLICATION_DECISION_OPTIONS,
            ],
            key="job_list_filter_decision",
        )

    with sort_col:
        selected_sort = st.selectbox(
            "並び替え",
            [
                "AIマッチ度順",
                "未対応・登録が古い順",
                "登録が新しい順",
                "登録が古い順",
                "年収下限が高い順",
                "会社名順",
            ],
            key="job_list_sort",
        )

    filtered_jobs = jobs

    if search_keyword.strip():
        keyword = search_keyword.strip().lower()

        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if keyword in (
                f"{job.company_name} "
                f"{job.job_title} "
                f"{job.occupation} "
                f"{job.industry} "
                f"{job.prefecture} "
                f"{job.municipality}"
            ).lower()
        ]

    if selected_prefecture != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if job.prefecture == selected_prefecture
        ]

    if selected_municipality != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if job.municipality == selected_municipality
        ]

    if selected_industry != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if job.industry == selected_industry
        ]

    if selected_source_name != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if any(
                source.source_name == selected_source_name
                for _, source in load_job_sources(job_id)
            )
        ]

    if selected_decision == "未対応":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if (
                job_id not in decisions
                or not decisions[
                    job_id
                ].decision_status.strip()
            )
        ]

    elif selected_decision != "すべて":
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if (
                job_id in decisions
                and decisions[
                    job_id
                ].decision_status
                == selected_decision
            )
        ]

    if (
        selected_sort
        == "未対応・登録が古い順"
    ):
        filtered_jobs = [
            (job_id, job)
            for job_id, job in filtered_jobs
            if (
                job_id not in decisions
                or not decisions[
                    job_id
                ].decision_status.strip()
            )
        ]

        filtered_jobs = list(
            reversed(filtered_jobs)
        )

    elif selected_sort == "AIマッチ度順":
        filtered_jobs = sorted(
            filtered_jobs,
            key=lambda item: (
                evaluations[
                    item[0]
                ].overall_score
                if (
                    item[0] in evaluations
                    and not evaluations[
                        item[0]
                    ].is_stale
                    and evaluations[
                        item[0]
                    ].overall_score
                    is not None
                )
                else -1
            ),
            reverse=True,
        )

    elif selected_sort == "登録が古い順":
        filtered_jobs = list(
            reversed(filtered_jobs)
        )

    elif selected_sort == "年収下限が高い順":
        filtered_jobs = sorted(
            filtered_jobs,
            key=lambda item: get_salary_minimum(
                item[1]
            ),
            reverse=True,
        )

    elif selected_sort == "会社名順":
        filtered_jobs = sorted(
            filtered_jobs,
            key=lambda item: (
                item[1].company_name
                or ""
            ).casefold(),
        )

    st.subheader("求人一覧")

    st.markdown(
        f"""
        <div class="job-list-decision-help">
            <span
                class="job-list-decision-help-icon"
                aria-hidden="true"
            >
                <img src="{info_icon_uri}" alt="">
            </span>
            <span>
                応募判断を変更する場合は、会社名を押して
                求人確認画面を開いてください。
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_job_count = len(
        filtered_jobs
    )

    total_pages = max(
        1,
        (
            total_job_count
            + JOB_LIST_PAGE_SIZE
            - 1
        )
        // JOB_LIST_PAGE_SIZE,
    )

    current_page = st.session_state[
        JOB_LIST_PAGE_KEY
    ]

    current_page = max(
        1,
        min(
            current_page,
            total_pages,
        ),
    )

    st.session_state[
        JOB_LIST_PAGE_KEY
    ] = current_page

    page_start = (
        current_page - 1
    ) * JOB_LIST_PAGE_SIZE

    page_end = (
        page_start
        + JOB_LIST_PAGE_SIZE
    )

    visible_jobs = filtered_jobs[
        page_start:page_end
    ]

    if not jobs:
        render_empty_state()

    elif not filtered_jobs:
        st.info(
            "検索条件に一致する求人はありません。"
        )

    else:
        display_start = page_start + 1

        display_end = min(
            page_end,
            total_job_count,
        )

        st.caption(
            f"全{total_job_count}件中 "
            f"{display_start}～{display_end}件を"
            "表示しています。"
        )

        render_job_table_header()

        for job_id, job in visible_jobs:
            render_job_card(
                job_id=job_id,
                job=job,
                evaluation=(
                    evaluations.get(job_id)
                ),
                decision=(
                    decisions.get(job_id)
                ),
            )

        if total_pages > 1:
            (
                previous_col,
                page_col,
                next_col,
            ) = st.columns(
                [1, 3, 1]
            )

            with previous_col:
                if st.button(
                    "前へ",
                    key="job_list_previous_page",
                    width="stretch",
                    disabled=(
                        current_page <= 1
                    ),
                ):
                    st.session_state[
                        JOB_LIST_PAGE_KEY
                    ] = (
                        current_page - 1
                    )

                    st.rerun()

            with page_col:
                st.markdown(
                    (
                        f"<div style='"
                        "text-align:center;"
                        "padding-top:8px;"
                        "'>"
                        f"{current_page} / "
                        f"{total_pages}ページ"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

            with next_col:
                if st.button(
                    "次へ",
                    key="job_list_next_page",
                    width="stretch",
                    disabled=(
                        current_page
                        >= total_pages
                    ),
                ):
                    st.session_state[
                        JOB_LIST_PAGE_KEY
                    ] = (
                        current_page + 1
                    )

                    st.rerun()

    selected_job_ids = [
        job_id
        for job_id, _ in jobs
        if (
            st.session_state.get(
                f"compare_job_{job_id}",
                False,
            )
            and is_job_match_evaluation_ready(
                evaluations.get(job_id)
            )
        )
    ]

    st.session_state[
        JOB_COMPARE_SELECTED_KEY
    ] = selected_job_ids

    if selected_job_ids:
        with st.container(border=True):
            action_col, clear_col, compare_col = st.columns(
                [2, 1, 2]
            )

            with action_col:
                st.write(
                    f"比較対象：{len(selected_job_ids)}件選択中"
                )

                st.caption(
                    "選択した求人を比較できます。"
                )

            with clear_col:
                if st.button(
                    "選択をクリア",
                    key="job_list_clear_compare",
                    width="stretch",
                ):
                    for job_id, _ in jobs:
                        checkbox_key = f"compare_job_{job_id}"

                        if checkbox_key in st.session_state:
                            st.session_state[
                                checkbox_key
                            ] = False

                    st.session_state[
                        JOB_COMPARE_SELECTED_KEY
                    ] = []

                    st.rerun()

            with compare_col:
                compare_disabled = (
                    len(selected_job_ids) < 2
                    or len(selected_job_ids) > 3
                )

                if st.button(
                    f"比較する（{len(selected_job_ids)}件）",
                    key="job_list_compare",
                    type="primary",
                    width="stretch",
                    disabled=compare_disabled,
                ):
                    save_general_activity(
                        get_current_user_id(),
                        "job_comparison",
                        f"{len(selected_job_ids)}件の求人を比較しました",
                        target_page="job_list",
                        icon_name="compare.svg",
                    )
                    st.session_state[
                        JOB_COMPARE_SELECTED_KEY
                    ] = selected_job_ids

                    st.query_params["page"] = (
                        "job_comparison"
                    )

                    st.query_params["job_ids"] = (
                        ",".join(
                            str(job_id)
                            for job_id
                            in selected_job_ids
                        )
                    )

                    st.rerun()

                if len(selected_job_ids) > 3:
                    st.caption(
                        "比較対象は3件まで選択できます。"
                    )

    st.divider()

    st.markdown(
        f"""
        <a class="job-list-back-home" href="?" target="_self">
            <img src="{chevron_left_uri}" alt="">
            <span>トップへ戻る</span>
        </a>
        """,
        unsafe_allow_html=True,
    )
