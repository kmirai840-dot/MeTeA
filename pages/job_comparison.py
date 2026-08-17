"""選択した求人の比較結果画面。"""

from html import escape

import streamlit as st

from services.job_evaluation_service import (
    load_job_match_evaluations,
)
from services.job_service import load_jobs
from services.basic_info_service import load_basic_info
from services.hope_condition_service import (
    load_hope_conditions_data,
)
from services.job_commute_service import (
    load_current_job_commute,
)
from services.job_matching_rule_evaluation_service import (
    evaluate_rule_hope_groups,
)
from services.job_matching_rule_service import (
    MATCH,
    MISMATCH,
    NEEDS_CONFIRMATION,
    PARTIAL_MATCH,
)

from pages.job_layout import (
    render_job_navigation,
)


JOB_COMPARE_SELECTED_KEY = (
    "job_compare_selected_ids"
)


def move_to_job_list() -> None:
    """比較状態を維持して求人一覧へ移動する。"""

    selected_job_ids = st.session_state.get(
        JOB_COMPARE_SELECTED_KEY,
        [],
    )

    for job_id in selected_job_ids:
        st.session_state[
            f"compare_job_{job_id}"
        ] = True

    st.query_params["page"] = "job_list"

    if "job_ids" in st.query_params:
        del st.query_params["job_ids"]

    st.rerun()


def display_value(
    value,
) -> str:
    """未入力値を比較画面用に整える。"""

    if value is None:
        return "未入力"

    if isinstance(value, list):
        values = [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

        if not values:
            return "未入力"

        return "\n".join(
            f"・{item}"
            for item in values
        )

    text = str(value).strip()

    return text or "未入力"


def display_location(
    job,
) -> str:
    """勤務地を表示用に整える。"""

    location = "".join(
        value
        for value in (
            job.prefecture,
            job.municipality,
        )
        if value
    )

    return location or "未入力"


def display_salary(
    job,
) -> str:
    """年収を表示用に整える。"""

    if (
        job.expected_salary_min
        or job.expected_salary_max
    ):
        salary_min = (
            job.expected_salary_min
            or "―"
        )

        salary_max = (
            job.expected_salary_max
            or "―"
        )

        return f"{salary_min} ～ {salary_max}"

    return display_value(
        job.annual_salary
    )


def display_evaluation_score(
    evaluations,
    job_id: int,
    field_name: str,
) -> str:
    """AI評価項目を比較画面用に整える。"""

    evaluation = evaluations.get(
        job_id
    )

    if evaluation is None:
        return "未評価"

    score = getattr(
        evaluation,
        field_name,
        None,
    )

    if score is None:
        return "未評価"

    return f"{score}点"


def render_comparison_row(
    label: str,
    values: list[str],
) -> None:
    """比較項目を横並びで表示する。"""

    with st.container(border=True):
        label_col, *value_columns = st.columns(
            [1.2] + [2] * len(values)
        )

        with label_col:
            st.markdown(
                f"**{label}**"
            )

        for column, value in zip(
            value_columns,
            values,
        ):
            with column:
                st.write(value)


def render_comparison_styles() -> None:
    """比較画面専用のデザインを適用する。"""

    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: #f5f8fc;
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 1440px;
            padding-top: 42px;
            padding-bottom: 72px;
        }

        .comparison-page-title {
            margin: 14px 0 4px;
            color: #102743;
            font-size: 38px;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        .comparison-page-description {
            margin: 0 0 24px;
            color: #66758a;
            font-size: 14px;
            line-height: 1.8;
        }

        .comparison-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin: 4px 0 18px;
        }

        .comparison-count {
            color: #102743;
            font-size: 16px;
            font-weight: 700;
        }

        .comparison-count strong {
            color: #1268f3;
            font-size: 22px;
        }

        .comparison-help {
            color: #66758a;
            font-size: 13px;
        }

        .comparison-header-card,
        .comparison-table-card {
            overflow: hidden;
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 14px;
            box-shadow: 0 8px 24px rgba(34, 63, 102, 0.06);
        }

        .comparison-grid {
            display: grid;
            align-items: stretch;
        }

        .comparison-grid > * {
            min-width: 0;
        }

        .comparison-label-cell,
        .comparison-value-cell,
        .comparison-job-cell {
            box-sizing: border-box;
            padding: 16px 18px;
            border-right: 1px solid #e4eaf2;
        }

        .comparison-grid > *:last-child {
            border-right: 0;
        }

        .comparison-header-label {
            display: flex;
            align-items: center;
            color: #52637a;
            background: #f8fafd;
            font-size: 13px;
            font-weight: 700;
        }

        .comparison-job-cell {
            min-height: 218px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .comparison-company-link {
            color: #1268f3 !important;
            font-size: 18px;
            font-weight: 800;
            line-height: 1.45;
            text-decoration: none !important;
        }

        .comparison-company-link:hover {
            text-decoration: underline !important;
        }

        .comparison-job-title {
            min-height: 42px;
            color: #65748a;
            font-size: 13px;
            line-height: 1.65;
        }

        .comparison-score-box {
            margin-top: auto;
            padding: 12px 14px;
            text-align: center;
            background: #f6f9ff;
            border: 1px solid #dce8fb;
            border-radius: 10px;
        }

        .comparison-score-label {
            color: #54657b;
            font-size: 11px;
            font-weight: 700;
        }

        .comparison-score-value {
            margin-top: 2px;
            color: #1268f3;
            font-size: 31px;
            font-weight: 800;
            line-height: 1.15;
        }

        .comparison-score-value small {
            font-size: 11px;
            font-weight: 600;
        }

        .comparison-stars {
            color: #1268f3;
            font-size: 17px;
            letter-spacing: 1px;
        }

        .comparison-meta-row {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 7px;
        }

        .comparison-provisional,
        .comparison-coverage {
            display: inline-flex;
            align-items: center;
            min-height: 24px;
            padding: 3px 9px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
        }

        .comparison-provisional {
            color: #a96400;
            background: #fff7e7;
            border: 1px solid #f2cf8a;
        }

        .comparison-coverage {
            color: #1268f3;
            background: #eaf3ff;
        }

        .comparison-section-heading {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin: 34px 0 14px;
        }

        .comparison-section-number {
            flex: 0 0 28px;
            width: 28px;
            height: 28px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            background: #1268f3;
            border-radius: 50%;
            font-size: 13px;
            font-weight: 800;
        }

        .comparison-section-title {
            margin: 0;
            color: #102743;
            font-size: 23px;
            font-weight: 800;
            line-height: 1.3;
        }

        .comparison-section-description {
            margin: 4px 0 0;
            color: #718096;
            font-size: 13px;
            line-height: 1.6;
        }

        .comparison-row {
            border-top: 1px solid #e4eaf2;
        }

        .comparison-row:first-child {
            border-top: 0;
        }

        .comparison-label-cell {
            color: #243b59;
            background: #f8fafd;
            font-size: 13px;
            font-weight: 700;
            line-height: 1.6;
        }

        .comparison-value-cell {
            position: relative;
            color: #233955;
            font-size: 14px;
            line-height: 1.75;
            overflow-wrap: anywhere;
        }

        .comparison-value-cell.is-best {
            background: #f1fbf5;
        }

        .comparison-best-badge {
            display: inline-flex;
            margin-left: 7px;
            padding: 2px 7px;
            color: #087c43;
            background: #dcf6e7;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 800;
            vertical-align: middle;
        }

        .comparison-value-muted {
            color: #8995a6;
        }
        .comparison-judgment {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            min-height: 24px;
            margin: 0 0 8px;
            padding: 3px 9px;
            border: 1px solid transparent;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 800;
            line-height: 1.35;
        }

        .comparison-judgment::before {
            content: "";
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
        }

        .comparison-judgment.match {
            color: #087c43;
            background: #e8f8ef;
            border-color: #b9e7cc;
        }

        .comparison-judgment.partial {
            color: #a96400;
            background: #fff6e5;
            border-color: #f0d397;
        }

        .comparison-judgment.mismatch {
            color: #cf3340;
            background: #fff0f1;
            border-color: #f2c2c6;
        }

        .comparison-judgment.confirmation {
            color: #31648f;
            background: #eef5fb;
            border-color: #cddfeb;
        }

        .comparison-judgment.excluded {
            color: #748196;
            background: #f1f3f6;
            border-color: #dce1e7;
        }

        .comparison-raw-value {
            display: block;
        }

        .comparison-score-number {
            color: #1268f3;
            font-size: 19px;
            font-weight: 800;
        }

        .comparison-long-text {
            max-height: 132px;
            overflow-y: auto;
            padding-right: 8px;
        }

        .comparison-note {
            margin-top: 14px;
            padding: 12px 16px;
            color: #52637a;
            background: #eef5ff;
            border: 1px solid #d4e5fb;
            border-radius: 10px;
            font-size: 12px;
            line-height: 1.7;
        }

        .comparison-summary-grid {
            display: grid;
            grid-template-columns: repeat(var(--summary-columns), minmax(0, 1fr));
            gap: 14px;
        }

        .comparison-summary-card {
            padding: 18px;
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 14px;
            box-shadow: 0 8px 24px rgba(34, 63, 102, 0.06);
        }

        .comparison-summary-company {
            margin-bottom: 14px;
            color: #13294b;
            font-size: 15px;
            font-weight: 700;
            line-height: 1.45;
        }

        .comparison-summary-counts {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 8px;
        }

        .comparison-summary-count {
            display: grid;
            grid-template-columns: 82px 44px minmax(0, 1fr);
            align-items: center;
            min-height: 58px;
            padding: 10px 12px;
            border-radius: 10px;
            font-size: 12px;
            line-height: 1.4;
        }

        .comparison-summary-count strong {
            display: block;
            margin: 0;
            font-size: 18px;
        }

        .comparison-summary-items {
            display: block;
            min-height: 0;
            margin: 0;
            font-size: 11px;
            font-weight: 600;
            line-height: 1.55;
            overflow-wrap: anywhere;
        }

        .comparison-summary-items.is-empty {
            color: #8995a6;
            font-weight: 500;
        }

        .comparison-summary-count.match {
            color: #087c43;
            background: #e8f8ef;
        }

        .comparison-summary-count.partial {
            color: #a96400;
            background: #fff6e5;
        }

        .comparison-summary-count.mismatch {
            color: #cf3340;
            background: #fff0f1;
        }

        .comparison-summary-count.confirmation {
            color: #31648f;
            background: #eef5fb;
        }

        .comparison-summary-help {
            margin: 14px 0 0;
            color: #67768b;
            font-size: 12px;
            line-height: 1.7;
        }

        [class*="st-key-job_comparison_back_top"] button,
        [class*="st-key-job_comparison_change"] button {
            color: #1268f3 !important;
            background: #ffffff !important;
            border-color: #8ab5fb !important;
        }

        [class*="st-key-job_comparison_back_list"] button {
            color: #ffffff !important;
            background: #1268f3 !important;
            border-color: #1268f3 !important;
        }

        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] {
                min-width: 960px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(
    number: int,
    title: str,
    description: str,
) -> None:
    """番号付きの比較セクション見出しを表示する。"""

    st.markdown(
        (
            '<div class="comparison-section-heading">'
            f'<span class="comparison-section-number">{number}</span>'
            '<div>'
            f'<h2 class="comparison-section-title">{escape(title)}</h2>'
            f'<p class="comparison-section-description">{escape(description)}</p>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def comparison_columns_style(job_count: int) -> str:
    """比較件数に応じた列幅を返す。"""

    return (
        "grid-template-columns: "
        f"180px repeat({job_count}, minmax(0, 1fr));"
    )


def format_html_value(value: str) -> str:
    """比較値を安全なHTMLへ変換する。"""

    text = display_value(value)
    escaped_text = escape(text).replace("\n", "<br>")

    if text in {"未入力", "未評価", "不明"}:
        return (
            '<span class="comparison-value-muted">'
            f'{escaped_text}</span>'
        )

    return escaped_text


def evaluation_value(
    evaluations,
    job_id: int,
    field_name: str,
):
    """評価値を数値またはNoneで取得する。"""

    evaluation = evaluations.get(job_id)

    if evaluation is None:
        return None

    return getattr(evaluation, field_name, None)


def render_job_headers(
    selected_jobs,
    evaluations,
) -> None:
    """比較対象求人のヘッダーをカードで表示する。"""

    comparison_job_ids = ",".join(
        str(job_id)
        for job_id, _ in selected_jobs
    )
    cells = [
        (
            '<div class="comparison-header-label '
            'comparison-label-cell">比較項目</div>'
        )
    ]

    for job_id, job in selected_jobs:
        company_name = job.company_name or "会社名未入力"
        job_title = (
            job.job_title
            or job.occupation
            or "求人名未入力"
        )
        evaluation = evaluations.get(job_id)
        score = (
            evaluation.overall_score
            if evaluation is not None
            else None
        )
        coverage = (
            getattr(evaluation, "evaluation_coverage", 0)
            if evaluation is not None
            else 0
        )
        is_provisional = (
            getattr(evaluation, "is_provisional", True)
            if evaluation is not None
            else True
        )
        numeric_score = score if score is not None else 0
        filled_stars = max(
            0,
            min(5, round(numeric_score / 20)),
        )
        stars = "★" * filled_stars + "☆" * (5 - filled_stars)
        score_text = (
            f'{score}<small>点 / 100</small>'
            if score is not None
            else "未評価"
        )
        meta_parts = []

        if is_provisional:
            meta_parts.append(
                '<span class="comparison-provisional">暫定評価</span>'
            )

        meta_parts.append(
            '<span class="comparison-coverage">'
            f'評価情報 {coverage}%</span>'
        )
        job_link = (
            f'?page=job_detail&amp;job_id={job_id}'
            '&amp;return_page=job_comparison'
            f'&amp;job_ids={comparison_job_ids}'
        )
        cells.append(
            '<div class="comparison-job-cell">'
            f'<a class="comparison-company-link" href="{job_link}" '
            f'target="_self">{escape(company_name)}</a>'
            f'<div class="comparison-job-title">{escape(job_title)}</div>'
            '<div class="comparison-score-box">'
            '<div class="comparison-score-label">AI総合マッチ度</div>'
            f'<div class="comparison-score-value">{score_text}</div>'
            f'<div class="comparison-stars">{stars}</div>'
            f'<div class="comparison-meta-row">{"".join(meta_parts)}</div>'
            '</div>'
            '</div>'
        )

    st.markdown(
        (
            '<div class="comparison-header-card">'
            f'<div class="comparison-grid" style="{comparison_columns_style(len(selected_jobs))}">'
            f'{"".join(cells)}'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def load_rule_comparison_data(selected_jobs):
    """既存の希望条件ルールで求人ごとの判定を取得する。"""

    hope_condition, hope_items = load_hope_conditions_data()
    basic_info = load_basic_info()
    result = {}

    for job_id, job in selected_jobs:
        commute_minutes = None

        if (
            basic_info is not None
            and basic_info.nearest_station_place_id
            and job.nearest_station
        ):
            commute_check = load_current_job_commute(
                job_id=job_id,
                current_origin_station_place_id=(
                    basic_info.nearest_station_place_id
                ),
                current_destination_station_name=(
                    job.nearest_station
                ),
            )

            if commute_check is not None:
                commute_minutes = commute_check.duration_minutes

        grouped_items = evaluate_rule_hope_groups(
            job=job,
            hope_condition=hope_condition,
            hope_items=hope_items,
            commute_minutes=commute_minutes,
        )
        item_map = {}

        for items in grouped_items.values():
            for item in items:
                item_map[item.item_name] = item

        result[job_id] = {
            "items": item_map,
            "commute_minutes": commute_minutes,
        }

    return result


def combine_rule_results(
    rule_data,
    job_id: int,
    item_names,
):
    """複数のルール判定を比較表用の1判定へまとめる。"""

    job_data = rule_data.get(job_id, {})
    item_map = job_data.get("items", {})
    items = [
        item_map[item_name]
        for item_name in item_names
        if item_name in item_map
    ]

    if not items:
        return None

    active_items = [
        item
        for item in items
        if getattr(item, "weight", 0) > 0
    ]

    if not active_items:
        return {
            "judgment": "評価対象外",
            "reason": "利用者がこだわらない、または希望条件が未設定です。",
        }

    judgment_priority = (
        MISMATCH,
        NEEDS_CONFIRMATION,
        PARTIAL_MATCH,
        MATCH,
    )

    for judgment in judgment_priority:
        matched_items = [
            item
            for item in active_items
            if item.judgment == judgment
        ]

        if matched_items:
            return {
                "judgment": judgment,
                "reason": " / ".join(
                    item.reason
                    for item in matched_items
                    if item.reason
                ),
            }

    return None


def render_judgment_badge(result) -> str:
    """希望条件との判定を色付きラベルへ変換する。"""

    if result is None:
        return ""

    judgment = result.get("judgment", "")
    reason = result.get("reason", "")
    badge_map = {
        MATCH: ("match", "希望に一致"),
        PARTIAL_MATCH: ("partial", "一部一致"),
        MISMATCH: ("mismatch", "希望と相違"),
        NEEDS_CONFIRMATION: ("confirmation", "要確認"),
        "評価対象外": ("excluded", "評価対象外"),
    }
    class_name, label = badge_map.get(
        judgment,
        ("excluded", "要確認"),
    )

    return (
        f'<span class="comparison-judgment {class_name}" '
        f'title="{escape(reason)}">{escape(label)}</span>'
    )

def render_comparison_table(
    rows,
    selected_jobs,
) -> None:
    """複数項目を一体型の比較表として表示する。"""

    row_html = []
    job_count = len(selected_jobs)

    for row in rows:
        label = row[0]
        values = row[1]
        numeric_values = row[2] if len(row) > 2 else None
        long_text = row[3] if len(row) > 3 else False
        judgments = row[4] if len(row) > 4 else None
        best_value = None

        if numeric_values:
            available_values = [
                value
                for value in numeric_values
                if value is not None
            ]

            if available_values:
                best_value = max(available_values)

        cells = [
            '<div class="comparison-label-cell">'
            f'{escape(label)}</div>'
        ]

        for index, value in enumerate(values):
            is_best = (
                best_value is not None
                and numeric_values is not None
                and numeric_values[index] is not None
                and numeric_values[index] == best_value
                and len(
                    {
                        item
                        for item in numeric_values
                        if item is not None
                    }
                ) > 1
            )
            class_names = "comparison-value-cell"

            if is_best:
                class_names += " is-best"

            value_html = format_html_value(value)
            judgment_html = (
                render_judgment_badge(judgments[index])
                if judgments is not None
                else ""
            )

            if judgment_html:
                value_html = (
                    f"{judgment_html}"
                    '<span class="comparison-raw-value">'
                    f"{value_html}</span>"
                )

            if numeric_values is not None and value not in {
                "未評価",
                "未入力",
            }:
                value_html = (
                    '<span class="comparison-score-number">'
                    f'{value_html}</span>'
                )

            if long_text:
                value_html = (
                    '<div class="comparison-long-text">'
                    f'{value_html}</div>'
                )

            if is_best:
                value_html += (
                    '<span class="comparison-best-badge">最高</span>'
                )

            cells.append(
                f'<div class="{class_names}">{value_html}</div>'
            )

        row_html.append(
            '<div class="comparison-grid comparison-row" '
            f'style="{comparison_columns_style(job_count)}">'
            f'{"".join(cells)}'
            '</div>'
        )

    st.markdown(
        (
            '<div class="comparison-table-card">'
            f'{"".join(row_html)}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_comparison_summary(
    selected_jobs,
    rule_data,
) -> None:
    """上部の比較表と同じ単位で希望条件の判定を集計する。"""

    summary_definitions = [
        (
            "年収",
            ("年収",),
        ),
        (
            "勤務地",
            ("勤務地",),
        ),
        (
            "雇用形態",
            ("雇用形態",),
        ),
        (
            "転勤条件",
            ("転勤条件",),
        ),
        (
            "電車移動時間",
            ("電車移動時間",),
        ),
        (
            "働き方",
            (
                "シフト勤務",
                "夜勤",
            ),
        ),
        (
            "残業",
            ("残業時間",),
        ),
        (
            "勤務時間",
            (
                "始業時刻",
                "終業時刻",
            ),
        ),
        (
            "休日・休暇",
            ("休日形態",),
        ),
        (
            "年間休日数",
            ("年間休日数",),
        ),
    ]

    cards = []

    for job_id, job in selected_jobs:
        items_by_judgment = {
            MATCH: [],
            PARTIAL_MATCH: [],
            MISMATCH: [],
            NEEDS_CONFIRMATION: [],
        }

        for (
            display_name,
            item_names,
        ) in summary_definitions:
            result = combine_rule_results(
                rule_data=rule_data,
                job_id=job_id,
                item_names=item_names,
            )

            if result is None:
                continue

            judgment = result.get(
                "judgment",
                "",
            )

            if judgment in items_by_judgment:
                items_by_judgment[
                    judgment
                ].append(
                    display_name
                )

        def summary_items_html(
            judgment: str,
        ) -> str:
            """判定項目名を最大3件表示する。"""

            names = items_by_judgment[
                judgment
            ]

            if not names:
                return (
                    '<span class="comparison-summary-items '
                    'is-empty">該当なし</span>'
                )

            visible_names = names[:3]
            text = "・".join(
                escape(name)
                for name in visible_names
            )
            remaining_count = (
                len(names)
                - len(visible_names)
            )

            if remaining_count > 0:
                text += (
                    f"・ほか{remaining_count}件"
                )

            return (
                '<span class="comparison-summary-items">'
                f'{text}</span>'
            )

        cards.append(
            '<div class="comparison-summary-card">'
            '<div class="comparison-summary-company">'
            f'{escape(job.company_name or "会社名未入力")}'
            '</div>'
            '<div class="comparison-summary-counts">'
            '<div class="comparison-summary-count match">'
            '希望に一致'
            f'<strong>{len(items_by_judgment[MATCH])}件</strong>'
            f'{summary_items_html(MATCH)}'
            '</div>'
            '<div class="comparison-summary-count partial">'
            '一部一致'
            f'<strong>{len(items_by_judgment[PARTIAL_MATCH])}件</strong>'
            f'{summary_items_html(PARTIAL_MATCH)}'
            '</div>'
            '<div class="comparison-summary-count mismatch">'
            '希望と相違'
            f'<strong>{len(items_by_judgment[MISMATCH])}件</strong>'
            f'{summary_items_html(MISMATCH)}'
            '</div>'
            '<div class="comparison-summary-count confirmation">'
            '要確認'
            f'<strong>{len(items_by_judgment[NEEDS_CONFIRMATION])}件</strong>'
            f'{summary_items_html(NEEDS_CONFIRMATION)}'
            '</div>'
            '</div>'
            '</div>'
        )

    st.markdown(
        (
            '<div class="comparison-summary-grid" '
            f'style="--summary-columns:{len(selected_jobs)}">'
            f'{"".join(cards)}'
            '</div>'
            '<p class="comparison-summary-help">'
            '一致件数だけで優劣を決めず、'
            '「希望と相違」と「要確認」の内容を確認して、'
            '応募判断に使ってください。'
            '</p>'
        ),
        unsafe_allow_html=True,
    )

def show_page() -> None:
    """求人比較結果を表示する。"""

    render_job_navigation("job_comparison")
    render_comparison_styles()

    selected_job_ids = st.session_state.get(
        JOB_COMPARE_SELECTED_KEY,
        [],
    )
    job_ids_value = st.query_params.get("job_ids", "")

    if job_ids_value:
        restored_job_ids = []

        for job_id_text in str(job_ids_value).split(","):
            try:
                restored_job_ids.append(int(job_id_text))
            except ValueError:
                continue

        if restored_job_ids:
            selected_job_ids = restored_job_ids
            st.session_state[
                JOB_COMPARE_SELECTED_KEY
            ] = selected_job_ids

    all_jobs = dict(load_jobs())
    selected_jobs = [
        (job_id, all_jobs[job_id])
        for job_id in selected_job_ids
        if job_id in all_jobs
    ]

    if st.button(
        "← 求人一覧へ戻る",
        key="job_comparison_back_top",
    ):
        move_to_job_list()

    st.markdown(
        '<h1 class="comparison-page-title">比較結果</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<p class="comparison-page-description">'
            '選択した求人の違いを横並びで確認し、'
            '自分に合う選択肢を整理できます。'
            '</p>'
        ),
        unsafe_allow_html=True,
    )

    if len(selected_jobs) < 2:
        st.warning("比較する求人を2件以上選択してください。")

        if st.button(
            "求人一覧で選択する",
            key="job_comparison_select_jobs",
            type="primary",
        ):
            move_to_job_list()

        return

    if len(selected_jobs) > 3:
        st.warning(
            "一度に比較できる求人は3件までです。"
            "求人一覧へ戻って選択を調整してください。"
        )
        return

    evaluations = load_job_match_evaluations()
    rule_data = load_rule_comparison_data(selected_jobs)

    def rule_judgments(*item_names):
        """表示中の求人順に希望条件との判定を返す。"""

        return [
            combine_rule_results(
                rule_data=rule_data,
                job_id=job_id,
                item_names=item_names,
            )
            for job_id, _ in selected_jobs
        ]

    st.markdown(
        (
            '<div class="comparison-toolbar">'
            '<div class="comparison-count">比較対象：'
            f'<strong>{len(selected_jobs)}</strong>件</div>'
            '<div class="comparison-help">会社名を押すと、求人確認画面を開けます。</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )
    render_job_headers(selected_jobs, evaluations)

    render_section_heading(
        1,
        "AIマッチング比較",
        "現在のプロフィールと求人情報から算出したカテゴリ別の評価です。",
    )
    ai_fields = [
        ("希望条件", "hope_condition_score"),
        ("就活の軸", "work_value_score"),
        ("職務経歴・スキル", "career_skill_score"),
        ("必須条件", "required_condition_score"),
    ]
    ai_rows = []

    for label, field_name in ai_fields:
        numeric_values = [
            evaluation_value(evaluations, job_id, field_name)
            for job_id, _ in selected_jobs
        ]
        ai_rows.append(
            (
                label,
                [
                    f"{value}点" if value is not None else "未評価"
                    for value in numeric_values
                ],
                numeric_values,
            )
        )

    render_comparison_table(ai_rows, selected_jobs)
    st.markdown(
        (
            '<div class="comparison-note">'
            '点数だけで応募先を決めるのではなく、評価情報の割合や、'
            '求人票で確認できない項目もあわせて確認してください。'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    render_section_heading(
        2,
        "基本条件",
        "年収・勤務地・雇用形態など、応募前に確認したい基本情報です。",
    )
    salary_values = [
        display_salary(job)
        for _, job in selected_jobs
    ]
    salary_numbers = []

    for _, job in selected_jobs:
        try:
            salary_numbers.append(
                float(job.expected_salary_min)
                if job.expected_salary_min
                else None
            )
        except (TypeError, ValueError):
            salary_numbers.append(None)

    render_comparison_table(
        [
            (
                "年収",
                salary_values,
                salary_numbers,
                False,
                rule_judgments("年収"),
            ),
            (
                "勤務地",
                [display_location(job) for _, job in selected_jobs],
                None,
                False,
                rule_judgments("勤務地"),
            ),
            (
                "雇用形態",
                [display_value(job.employment_type) for _, job in selected_jobs],
                None,
                False,
                rule_judgments("雇用形態"),
            ),
            (
                "転勤条件",
                [display_value(job.transfer_required) for _, job in selected_jobs],
                None,
                False,
                rule_judgments("転勤条件"),
            ),
            (
                "電車移動時間",
                [
                    (
                        f"{rule_data.get(job_id, {}).get('commute_minutes')}分"
                        if rule_data.get(job_id, {}).get("commute_minutes")
                        is not None
                        else "未確認"
                    )
                    for job_id, _ in selected_jobs
                ],
                None,
                False,
                rule_judgments("電車移動時間"),
            ),
        ],
        selected_jobs,
    )

    render_section_heading(
        3,
        "勤務条件",
        "働き方や勤務時間、休日条件の違いを確認できます。",
    )
    holiday_numbers = []

    for _, job in selected_jobs:
        try:
            holiday_numbers.append(
                float(job.annual_holidays)
                if job.annual_holidays
                else None
            )
        except (TypeError, ValueError):
            holiday_numbers.append(None)

    render_comparison_table(
        [
            (
                "働き方",
                [display_value(job.work_style) for _, job in selected_jobs],
                None,
                False,
                rule_judgments("シフト勤務", "夜勤"),
            ),
            (
                "フレックスタイム",
                [display_value(job.flextime) for _, job in selected_jobs],
            ),
            (
                "残業",
                [display_value(job.overtime) for _, job in selected_jobs],
                None,
                False,
                rule_judgments("残業時間"),
            ),
            (
                "勤務時間",
                [
                    (
                        f"{job.start_time or '―'} ～ {job.end_time or '―'}"
                        if job.start_time or job.end_time
                        else "未入力"
                    )
                    for _, job in selected_jobs
                ],
                None,
                False,
                rule_judgments("始業時刻", "終業時刻"),
            ),
            (
                "休日・休暇",
                [display_value(job.holidays) for _, job in selected_jobs],
                None,
                False,
                rule_judgments("休日形態"),
            ),
            (
                "年間休日数",
                [
                    (
                        f"{job.annual_holidays}日"
                        if job.annual_holidays
                        else "未入力"
                    )
                    for _, job in selected_jobs
                ],
                holiday_numbers,
                False,
                rule_judgments("年間休日数"),
            ),
        ],
        selected_jobs,
    )

    render_section_heading(
        4,
        "仕事内容・福利厚生",
        "業務内容と制度面は、優劣ではなく違いを確認してください。",
    )
    render_comparison_table(
        [
            (
                "仕事内容",
                [display_value(job.job_summary) for _, job in selected_jobs],
                None,
                True,
            ),
            (
                "福利厚生",
                [
                    "\n".join(
                        f"・{value}"
                        for value in (
                            job.social_insurance,
                            job.commuting_allowance,
                            job.housing_allowance,
                            job.retirement_plan,
                            job.qualification_support,
                        )
                        if value
                    )
                    or "未入力"
                    for _, job in selected_jobs
                ],
                None,
                True,
            ),
        ],
        selected_jobs,
    )

    render_section_heading(
        5,
        "比較のまとめ",
        "希望条件に対する判定件数を、求人ごとに整理しています。",
    )
    render_comparison_summary(selected_jobs, rule_data)

    st.markdown("<div style=\"height:24px\"></div>", unsafe_allow_html=True)
    action_left, action_right = st.columns([1, 1.4])

    with action_left:
        if st.button(
            "比較対象を変更する",
            key="job_comparison_change",
            width="stretch",
        ):
            move_to_job_list()

    with action_right:
        if st.button(
            "求人一覧へ戻る",
            key="job_comparison_back_list",
            type="primary",
            width="stretch",
        ):
            move_to_job_list()