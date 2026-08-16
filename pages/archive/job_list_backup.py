"""登録済み求人の一覧画面。"""

import streamlit as st

from pages.job_registration import (
    JOB_FORM_RETURN_PAGE_KEY,
    load_job_for_edit,
)
from services.job_service import (
    delete_job_data,
    load_jobs,
    load_job_sources,
)


JOB_DELETE_CONFIRM_KEY = (
    "job_list_delete_confirm_id"
)


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
            move_to_page("job_registration")


def format_empty(
    value: str,
) -> str:
    """空の値を画面表示用に整える。"""

    cleaned_value = str(value or "").strip()

    return cleaned_value or "未入力"


def format_location(
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


def format_salary(
    job,
) -> str:
    """想定年収を表示用に整える。"""

    if job.annual_salary:
        return job.annual_salary

    if (
        job.expected_salary_min
        and job.expected_salary_max
    ):
        return (
            f"{job.expected_salary_min}〜"
            f"{job.expected_salary_max}"
        )

    if job.expected_salary_min:
        return f"{job.expected_salary_min}〜"

    if job.expected_salary_max:
        return f"〜{job.expected_salary_max}"

    return "未入力"


def format_date_text(
    value: object,
) -> str:
    """日付を一覧表示用の文字列に整える。"""

    if value is None:
        return "未入力"

    text = str(value).strip()

    if text == "":
        return "未入力"

    return text[:10]


def format_sources(
    job_id: int,
    job,
) -> str:
    """紹介経路を / 区切りで表示する。"""

    sources = load_job_sources(job_id)

    source_names = []

    for _, source in sources:
        source_label = (
            source.source_name
            or source.source_type
        ).strip()

        if source_label:
            source_names.append(source_label)

    if not source_names:
        fallback_source = (
            job.source_name
            or job.source_type
        ).strip()

        if fallback_source:
            source_names.append(fallback_source)

    if not source_names:
        return "未入力"

    return " / ".join(source_names)


def matches_search_word(
    job_id: int,
    job,
    search_word: str,
) -> bool:
    """検索語に求人が一致するか判定する。"""

    cleaned_word = search_word.strip().casefold()

    if not cleaned_word:
        return True

    target_text = "\n".join(
        [
            job.company_name,
            job.job_title,
            job.occupation,
            format_sources(job_id, job),
        ]
    ).casefold()

    return cleaned_word in target_text


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


def render_job_row(
    job_id: int,
    job: Job,
) -> None:
    """求人一覧の1行を表示する。"""

    cols = st.columns(
        [1.8, 2.0, 1.2, 1.2, 1.2, 1.7, 0.8, 0.8, 0.8]
    )

    with cols[0]:
        st.write(format_empty(job.company_name))

    with cols[1]:
        st.write(format_empty(job.job_title))

    with cols[2]:
        st.write(format_empty(job.occupation))

    with cols[3]:
        st.write(format_location(job))

    with cols[4]:
        st.write(format_salary(job))

    with cols[5]:
        st.write(format_sources(job_id, job))

    with cols[6]:
        if st.button(
            "詳細",
            key=f"detail_job_{job_id}",
            width="stretch",
        ):
            st.query_params["page"] = "job_detail"
            st.query_params["job_id"] = str(job_id)
            st.rerun()

    with cols[7]:
        if st.button(
            "編集",
            key=f"edit_job_{job_id}",
            width="stretch",
        ):
            st.session_state[
                JOB_FORM_RETURN_PAGE_KEY
            ] = "job_list"

            load_job_for_edit(job_id)

            move_to_page("job_registration")

    with cols[8]:
        if st.button(
            "削除",
            key=f"delete_job_{job_id}",
            width="stretch",
        ):
            st.session_state[
                JOB_DELETE_CONFIRM_KEY
            ] = job_id

            st.rerun()


def show_page() -> None:
    """求人一覧画面を表示する。"""

    st.title("求人一覧")

    render_delete_confirmation()

    jobs = load_jobs()

    if not jobs:
        st.info("登録されている求人はありません。")
        return

    if JOB_LIST_SEARCH_KEY not in st.session_state:
        st.session_state[JOB_LIST_SEARCH_KEY] = ""

    search_word = st.session_state[JOB_LIST_SEARCH_KEY]

    if st.session_state.get(JOB_SEARCH_RESET_KEY):
        st.session_state[JOB_LIST_SEARCH_KEY] = ""
        st.session_state[JOB_SEARCH_RESET_KEY] = False
        search_word = ""
    else:
        search_word = st.text_input(
            "検索",
            placeholder="会社名・求人名・職種・紹介経路で検索",
            key=JOB_LIST_SEARCH_KEY,
        )

    filtered_jobs = [
        (job_id, job)
        for job_id, job in jobs
        if matches_search_word(job_id, job, search_word)
    ]

    st.caption(
        f"{len(filtered_jobs)}件 / 全{len(jobs)}件"
    )

    header_cols = st.columns(
        [1.8, 2.0, 1.2, 1.2, 1.2, 1.7, 0.8, 0.8, 0.8]
    )

    headers = (
        "会社名",
        "求人名",
        "職種",
        "勤務地",
        "想定年収",
        "紹介経路",
        "詳細",
        "編集",
        "削除",
    )

    for col, header in zip(header_cols, headers):
        with col:
            st.markdown(f"**{header