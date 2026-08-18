"""就活の軸画面の表示を担当するモジュール。"""

from html import escape
import streamlit as st

from pages.self_discovery_theme import apply_self_discovery_theme

from models import JobHuntingAxis
from services.job_hunting_axis_suggestion_service import (
    suggest_job_hunting_axes,
)
from services.job_hunting_axis_service import (
    MAX_AXIS_COUNT,
    delete_axis,
    load_job_hunting_axis_data,
    load_job_hunting_axis_draft,
    move_axis_down,
    move_axis_up,
    save_job_hunting_axis_data,
    save_job_hunting_axis_draft,
)


AXES_STATE_KEY = "job_hunting_axes"
AXES_LOADED_KEY = "job_hunting_axes_loaded"
ADD_FORM_VISIBLE_KEY = "job_hunting_axis_add_form_visible"
MESSAGE_KEY = "job_hunting_axis_message"
EDITING_INDEX_KEY = "job_hunting_axis_editing_index"
DELETE_CONFIRM_INDEX_KEY = "job_hunting_axis_delete_confirm_index"
REGENERATE_CONFIRM_KEY = "job_hunting_axis_regenerate_confirm"
PAGE_ERRORS_KEY = "job_hunting_axis_page_errors"
FIELD_ERRORS_KEY = "job_hunting_axis_field_errors"


def axis_to_dict(
    axis: JobHuntingAxis,
) -> dict[str, object]:
    """JobHuntingAxisを画面保存用の辞書へ変換する。"""

    return {
        "axis_title": axis.axis_title,
        "axis_description": axis.axis_description,
        "priority_rank": axis.priority_rank,
        "source_type": axis.source_type,
    }


def dict_to_axis(
    axis_data: dict[str, object],
) -> JobHuntingAxis:
    """辞書をJobHuntingAxisへ変換する。"""

    return JobHuntingAxis(
        axis_title=str(
            axis_data.get(
                "axis_title",
                "",
            )
        ),
        axis_description=str(
            axis_data.get(
                "axis_description",
                "",
            )
        ),
        priority_rank=int(
            axis_data.get(
                "priority_rank",
                1,
            )
        ),
        source_type=str(
            axis_data.get(
                "source_type",
                "manual",
            )
        ),
    )


def initialize_job_hunting_axis_state() -> None:
    """下書きまたは正式保存データを画面へ復元する。"""

    if st.session_state.get(AXES_LOADED_KEY):
        return

    draft_data = load_job_hunting_axis_draft()

    if draft_data:
        draft_axes = draft_data.get(
            "axes",
            [],
        )

        restored_axes = [
            dict_to_axis(axis_data)
            for axis_data in draft_axes
            if isinstance(axis_data, dict)
        ]
        st.session_state[AXES_STATE_KEY] = (
            restored_axes
            if restored_axes
            else suggest_job_hunting_axes()
        )

    else:
        saved_axes = load_job_hunting_axis_data()
        st.session_state[AXES_STATE_KEY] = (
            saved_axes
            if saved_axes
            else suggest_job_hunting_axes()
        )

    st.session_state[AXES_LOADED_KEY] = True

    if ADD_FORM_VISIBLE_KEY not in st.session_state:
        st.session_state[ADD_FORM_VISIBLE_KEY] = False

    if EDITING_INDEX_KEY not in st.session_state:
        st.session_state[EDITING_INDEX_KEY] = None

    if DELETE_CONFIRM_INDEX_KEY not in st.session_state:
        st.session_state[DELETE_CONFIRM_INDEX_KEY] = None

    if REGENERATE_CONFIRM_KEY not in st.session_state:
        st.session_state[REGENERATE_CONFIRM_KEY] = False

    if PAGE_ERRORS_KEY not in st.session_state:
        st.session_state[PAGE_ERRORS_KEY] = []

    if FIELD_ERRORS_KEY not in st.session_state:
        st.session_state[FIELD_ERRORS_KEY] = {}


def collect_job_hunting_axis_draft(
) -> dict[str, object]:
    """現在の軸一覧を下書き保存用データへ変換する。"""

    axes = st.session_state.get(
        AXES_STATE_KEY,
        [],
    )

    return {
        "axes": [
            axis_to_dict(axis)
            for axis in axes
        ]
    }


def update_axis_draft_state(axes: list[JobHuntingAxis]) -> None:
    """画面上の軸を更新し、正式保存せず下書きだけへ保存する。"""

    st.session_state[AXES_STATE_KEY] = axes
    save_job_hunting_axis_draft(
        {"axes": [axis_to_dict(axis) for axis in axes]}
    )


def add_axis(
    axis_title: str,
    axis_description: str,
) -> list[str]:
    """新しい就活の軸を画面一覧へ追加する。"""

    axes = st.session_state.get(
        AXES_STATE_KEY,
        [],
    )

    title = axis_title.strip()
    description = axis_description.strip()

    errors: list[str] = []

    if not title:
        errors.append(
            "軸の名称を入力してください。"
        )

    if len(title) > 50:
        errors.append(
            "軸の名称は50文字以内で入力してください。"
        )

    if not description:
        errors.append(
            "具体的な判断基準を入力してください。"
        )

    if len(description) > 200:
        errors.append(
            "具体的な判断基準は200文字以内で入力してください。"
        )

    if len(axes) >= MAX_AXIS_COUNT:
        errors.append(
            "登録できる就活の軸は最大3件です。"
        )

    normalized_title = title.casefold()

    if any(
        axis.axis_title.strip().casefold()
        == normalized_title
        for axis in axes
    ):
        errors.append(
            f"「{title}」はすでに登録されています。"
        )

    if errors:
        return errors

    new_axis = JobHuntingAxis(
        axis_title=title,
        axis_description=description,
        priority_rank=len(axes) + 1,
        source_type="manual",
    )

    updated_axes = [
        *axes,
        new_axis,
    ]

    update_axis_draft_state(updated_axes)
    st.session_state[ADD_FORM_VISIBLE_KEY] = False

    return []


def update_axis(
    target_index: int,
    axis_title: str,
    axis_description: str,
) -> list[str]:
    """指定された就活の軸を編集する。"""

    axes = st.session_state.get(
        AXES_STATE_KEY,
        [],
    )

    if target_index < 0 or target_index >= len(axes):
        return ["編集対象の就活の軸が見つかりません。"]

    title = axis_title.strip()
    description = axis_description.strip()

    errors: list[str] = []

    if not title:
        errors.append(
            "軸の名称を入力してください。"
        )

    if len(title) > 50:
        errors.append(
            "軸の名称は50文字以内で入力してください。"
        )

    if not description:
        errors.append(
            "具体的な判断基準を入力してください。"
        )

    if len(description) > 200:
        errors.append(
            "具体的な判断基準は200文字以内で入力してください。"
        )

    normalized_title = title.casefold()

    if any(
        index != target_index
        and axis.axis_title.strip().casefold()
        == normalized_title
        for index, axis in enumerate(axes)
    ):
        errors.append(
            f"「{title}」はすでに登録されています。"
        )

    if errors:
        return errors

    current_axis = axes[target_index]

    updated_axis = JobHuntingAxis(
        axis_title=title,
        axis_description=description,
        priority_rank=current_axis.priority_rank,
        source_type=current_axis.source_type,
    )

    updated_axes = list(axes)
    updated_axes[target_index] = updated_axis

    update_axis_draft_state(updated_axes)
    st.session_state[EDITING_INDEX_KEY] = None

    return []


def render_axis_error_summary() -> None:
    """共通形式で画面上部へエラー一覧を表示する。"""

    errors = st.session_state.get(PAGE_ERRORS_KEY, [])
    if not errors:
        return
    items = "".join(
        f"<li>{escape(message)}</li>"
        for message in dict.fromkeys(errors)
    )
    st.markdown(
        '<div class="metea-axis-error-summary" role="alert">'
        '<span>!</span><div><strong>入力内容を確認してください</strong>'
        f'<ul>{items}</ul></div></div>',
        unsafe_allow_html=True,
    )


def render_axis_field_error(field_key: str) -> None:
    """入力欄直下へ個別エラーを表示する。"""

    message = st.session_state.get(FIELD_ERRORS_KEY, {}).get(field_key)
    if message:
        st.markdown(
            f'<p class="metea-axis-field-error">{escape(message)}</p>',
            unsafe_allow_html=True,
        )


def set_axis_form_errors(
    errors: list[str],
    title_key: str | None = None,
    description_key: str | None = None,
) -> None:
    """エラー一覧と各入力欄のエラーを共通形式で保持する。"""

    field_errors: dict[str, str] = {}
    for message in errors:
        if title_key and (
            "軸の名称" in message
            or "すでに登録" in message
        ):
            field_errors[title_key] = message
        if description_key and "判断基準" in message:
            field_errors[description_key] = message
    st.session_state[PAGE_ERRORS_KEY] = errors
    st.session_state[FIELD_ERRORS_KEY] = field_errors


def clear_axis_errors() -> None:
    """画面上の入力エラーを消去する。"""

    st.session_state[PAGE_ERRORS_KEY] = []
    st.session_state[FIELD_ERRORS_KEY] = {}


def apply_job_hunting_axis_styles() -> None:
    """自分を知る画面群と共通のレスポンシブ表示を適用する。"""

    error_keys = st.session_state.get(FIELD_ERRORS_KEY, {})
    error_selectors = []
    for key in error_keys:
        error_selectors.extend([
            f'.st-key-{key} [data-baseweb="input"]',
            f'.st-key-{key} [data-baseweb="textarea"]',
        ])
    error_css = ""
    if error_selectors:
        error_css = (
            ",".join(error_selectors)
            + "{border:1.5px solid #ef4444 !important;"
            "box-shadow:0 0 0 1px rgba(239,68,68,.08) !important;}"
        )

    st.markdown(
        f"""
        <span class="metea-axis-page-marker"></span>
        <style>
        [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker){{
          width:calc(100vw - 272px);max-width:none;height:calc(100dvh - 84px);
          margin:66px 28px 18px 244px;padding:12px 30px 16px;
          overflow-y:auto;background:#fff;border:1px solid #d9e4f2;
          border-radius:18px;box-shadow:0 12px 30px rgba(15,43,82,.07);
        }}
        [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker)>
        [data-testid="stVerticalBlock"]{{gap:.62rem;}}
        .metea-axis-guide{{margin:6px 0 24px;padding:8px 12px;display:flex;gap:9px;
          background:#f4f8ff;border:1px solid #b9d3ff;border-radius:12px;color:#29466f;}}
        .metea-axis-guide div{{font-size:.88rem;line-height:1.45;}}
        .metea-axis-guide strong{{display:block;color:#102c53;margin-bottom:3px;}}
        .metea-axis-guide-icon{{display:grid;place-items:center;flex:0 0 28px;height:28px;
          border-radius:50%;background:#1769ff;color:#fff;font-weight:800;}}
        .metea-axis-error-summary{{margin:16px 0;padding:14px 16px;display:flex;gap:12px;
          border:1px solid #ff9b9b;border-radius:12px;background:#fff6f6;color:#dc2626;}}
        .metea-axis-error-summary>span{{display:grid;place-items:center;width:24px;height:24px;
          border:2px solid #ef4444;border-radius:7px;font-weight:800;}}
        .metea-axis-error-summary ul{{margin:7px 0 0;padding-left:20px;}}
        .metea-axis-field-error{{margin:-10px 0 10px;color:#dc2626;font-size:.88rem;font-weight:600;}}
        [data-testid="stExpander"]:has(.metea-axis-card-marker){{
          margin-bottom:4px;overflow:hidden;border:1px solid #cfdaea!important;
          border-radius:12px!important;background:#fff;
          box-shadow:0 4px 12px rgba(31,65,114,.055);
        }}
        [data-testid="stExpander"]:has(.metea-axis-card-marker) details,
        [data-testid="stExpander"]:has(.metea-axis-card-marker) summary{{
          border-radius:11px!important;
        }}
        [data-testid="stExpander"]:has(.metea-axis-card-marker) details[open] summary{{
          border-radius:11px 11px 0 0!important;
        }}
        [data-testid="stExpander"]:has(.metea-axis-card-marker) summary{{
          min-height:44px;padding:8px 10px!important;background:#fff;
        }}
        details:has(.metea-axis-card-marker)[open]>summary{{background:#f5f8fd;}}
        details:has(.metea-axis-card-marker) [data-testid="stVerticalBlock"]{{gap:.48rem;}}
        .metea-axis-card-head{{display:flex;align-items:flex-start;gap:10px;margin:0 0 6px;}}
        .metea-axis-rank{{display:inline-flex;align-items:center;justify-content:center;
          min-width:48px;height:30px;padding:0 10px;border-radius:999px;background:#1769ff;
          color:#fff;font-weight:800;font-size:.88rem;}}
        .metea-axis-card-title{{margin:0;color:#08264d;font-size:1.12rem;font-weight:800;}}
        .metea-axis-source{{display:inline-flex;margin-top:2px;padding:3px 9px;border-radius:999px;
          background:#edf4ff;color:#2463b8;font-size:.76rem;font-weight:700;}}
        .metea-axis-criteria{{padding:9px 12px;margin:3px 0 7px;background:#f7f9fc;
          border:1px solid #e1e8f1;border-radius:10px;color:#213a5b;}}
        .metea-axis-criteria small{{display:block;margin-bottom:4px;color:#70829a;font-weight:700;}}
        .metea-axis-criteria p{{margin:0;line-height:1.65;}}
        div[class*="st-key-job_hunting_axis_up_"] button,
        div[class*="st-key-job_hunting_axis_down_"] button{{color:#1769ff;border-color:#a9c8ff;background:#f5f9ff;}}
        div[class*="st-key-job_hunting_axis_delete_"] button{{color:#dc3545;border-color:#ffc3c8;background:#fff8f8;}}
        .st-key-job_hunting_axis_regenerate button{{
          color:#0c57c7!important;background:#eaf3ff!important;border:1px solid #75aaff!important;
          font-weight:700!important;box-shadow:0 4px 12px rgba(23,105,255,.12)!important;
        }}
        .st-key-job_hunting_axis_regenerate button:hover{{
          background:#dcecff!important;border-color:#438cff!important;
          box-shadow:0 6px 16px rgba(23,105,255,.18)!important;
        }}
        .st-key-job_hunting_axis_regenerate{{margin-top:10px;}}
        .metea-axis-regenerate-notice{{display:flex;gap:10px;align-items:flex-start;
          margin:4px 0 10px;padding:11px 13px;border:1px solid #a9c8ff;
          border-radius:11px;background:#f2f7ff;color:#29466f;line-height:1.55;}}
        .metea-axis-regenerate-notice__icon{{display:grid;place-items:center;flex:0 0 26px;
          height:26px;border-radius:50%;background:#1769ff;color:#fff;font-weight:800;}}
        .metea-axis-regenerate-notice strong{{display:block;margin-bottom:2px;color:#102c53;}}
        [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker) h1{{
          padding:0!important;margin:0 0 .15rem!important;font-size:2.25rem;line-height:1.18;}}
        [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker) h2,
        [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker) h3{{
          padding:0!important;margin:.2rem 0 .65rem!important;line-height:1.25;}}
        [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker) hr{{margin:.55rem 0;}}
        [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker) button{{min-height:38px;}}
        [data-testid="stHorizontalBlock"]:has(.st-key-job_hunting_axis_back_bottom){{
          margin-top:18px;
        }}
        {error_css}
        @media(max-width:1100px){{
          [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker){{
            width:calc(100vw - 228px);margin-left:202px;padding:16px 24px;
          }}
        }}
        @media(max-width:700px){{
          [data-testid="stMainBlockContainer"]:has(.metea-axis-page-marker){{
            width:calc(100vw - 20px);height:auto;min-height:calc(100dvh - 78px);
            margin:70px 10px 12px;padding:16px 14px;border-radius:14px;overflow:visible;
          }}
          .metea-axis-card-head{{gap:9px}}.metea-axis-rank{{min-width:43px}}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_regenerate_controls() -> None:
    """軸一覧の下へ候補再作成の操作を表示する。"""

    if not st.session_state.get(REGENERATE_CONFIRM_KEY, False):
        if st.button(
            "入力内容から候補を作り直す",
            icon=":material/autorenew:",
            key="job_hunting_axis_regenerate",
            use_container_width=True,
        ):
            st.session_state[REGENERATE_CONFIRM_KEY] = True
            st.rerun()
        return

    st.markdown(
        '<div class="metea-axis-regenerate-notice" role="status">'
        '<span class="metea-axis-regenerate-notice__icon">i</span><div>'
        '<strong>候補を作り直す前に確認してください</strong>'
        '現在画面に表示している就活の軸を、最新の希望条件と価値観から作る候補へ置き換えます。'
        '置き換え後も、「この内容で確定して次へ」を押すまでは正式保存されません。'
        '</div></div>',
        unsafe_allow_html=True,
    )
    regenerate_columns = st.columns(2)
    with regenerate_columns[0]:
        if st.button(
            "候補を作り直す",
            icon=":material/autorenew:",
            key="job_hunting_axis_regenerate_execute",
            use_container_width=True,
            type="primary",
        ):
            suggested_axes = suggest_job_hunting_axes()
            if suggested_axes:
                update_axis_draft_state(suggested_axes)
                clear_axis_errors()
                st.session_state[EDITING_INDEX_KEY] = None
                st.session_state[DELETE_CONFIRM_INDEX_KEY] = None
                st.session_state[ADD_FORM_VISIBLE_KEY] = False
                st.session_state[REGENERATE_CONFIRM_KEY] = False
                st.session_state[MESSAGE_KEY] = (
                    "入力内容から軸候補を作り直しました。"
                    "内容を確認し、最後に確定してください。"
                )
                st.rerun()
            st.error(
                "軸候補を作成できませんでした。"
                "希望条件または価値観を入力してから、もう一度お試しください。"
            )

    with regenerate_columns[1]:
        if st.button(
            "キャンセル",
            key="job_hunting_axis_regenerate_cancel",
            use_container_width=True,
        ):
            st.session_state[REGENERATE_CONFIRM_KEY] = False
            st.rerun()


def render_job_hunting_axis_page() -> None:
    """就活の軸画面を表示する。"""

    apply_self_discovery_theme(current_step=4)

    initialize_job_hunting_axis_state()
    apply_job_hunting_axis_styles()

    if st.button(
        "← 価値観へ戻る",
        key="job_hunting_axis_back_top",
    ):
        st.query_params["page"] = "work_values"
        st.rerun()

    st.title("就活の軸")

    st.write(
        "仕事選びで大切にしたい判断基準を、"
        "優先順位の高い順に整理してください。"
    )

    st.progress(
        4 / 5,
        text="自分を知る 4 / 5　就活の軸",
    )

    render_axis_error_summary()

    st.markdown(
        '<div class="metea-axis-guide"><span class="metea-axis-guide-icon">i</span>'
        '<div><strong>提案された内容を確認してください</strong>'
        '希望条件と価値観から、就活の軸を最大3件提案しています。'
        '提案はまだ確定していません。名称と具体的な判断基準を確認し、'
        '必要に応じて編集・削除・並び替えをしてください。</div></div>',
        unsafe_allow_html=True,
    )

    axes = st.session_state.get(
        AXES_STATE_KEY,
        [],
    )

    st.subheader(
        f"登録した就活の軸（{len(axes)} / {MAX_AXIS_COUNT}件）"
    )

    if not axes:
        st.info(
            "まだ就活の軸が登録されていません。"
        )

    for index, axis in enumerate(axes):
        is_open = (
            st.session_state.get(EDITING_INDEX_KEY) == index
            or st.session_state.get(DELETE_CONFIRM_INDEX_KEY) == index
        )
        with st.expander(
            f"{axis.priority_rank}位　{axis.axis_title}",
            expanded=is_open,
        ):
            st.markdown(
                '<span class="metea-axis-card-marker"></span>',
                unsafe_allow_html=True,
            )

            if (
                st.session_state.get(
                    EDITING_INDEX_KEY
                )
                == index
            ):
                st.markdown(
                     f"### {axis.priority_rank}位を編集中"
                )

                edit_title_key = f"job_hunting_axis_edit_title_{index}"
                edit_description_key = f"job_hunting_axis_edit_description_{index}"
                st.markdown("**軸の名称** :red[*]")
                edit_title = st.text_input(
                    "軸の名称（必須）",
                     value=axis.axis_title,
                      max_chars=50,
                      key=edit_title_key,
                      label_visibility="collapsed",
                )
                render_axis_field_error(edit_title_key)

                st.markdown("**具体的な判断基準** :red[*]")
                edit_description = st.text_area(
                    "具体的な判断基準（必須）",
                    value=axis.axis_description,
                    max_chars=200,
                    key=edit_description_key,
                    label_visibility="collapsed",
                )
                render_axis_field_error(edit_description_key)

                edit_columns = st.columns(2)

                with edit_columns[0]:
                    if st.button(
                        "変更を保存",
                        key=f"job_hunting_axis_edit_save_{index}",
                        use_container_width=True,
                    ):
                        errors = update_axis(
                            index,
                            edit_title,
                            edit_description,
                        )

                        if errors:
                            set_axis_form_errors(
                                errors,
                                edit_title_key,
                                edit_description_key,
                            )
                            st.rerun()

                        else:
                            clear_axis_errors()
                            st.session_state[MESSAGE_KEY] = (
                                "就活の軸を下書きへ反映しました。"
                            )
                            st.rerun()

                with edit_columns[1]:
                    if st.button(
                        "キャンセル",
                        key=f"job_hunting_axis_edit_cancel_{index}",
                        use_container_width=True,
                    ):
                        st.session_state[EDITING_INDEX_KEY] = None
                        st.rerun()

            else:
                st.markdown(
                    '<div class="metea-axis-card-head"><div>'
                    f'<span class="metea-axis-source">'
                    f'{"本人が追加" if axis.source_type == "manual" else "入力内容からの提案"}'
                    '</span></div></div>'
                    '<div class="metea-axis-criteria"><small>具体的な判断基準</small>'
                    f'<p>{escape(axis.axis_description)}</p></div>',
                    unsafe_allow_html=True,
                )

                control_columns = st.columns(
                    [1.3, 1.3, 1.4, 1.4]
                )

                with control_columns[0]:
                    if st.button(
                        "上へ",
                        icon=":material/arrow_upward:",
                        key=f"job_hunting_axis_up_{index}",
                        use_container_width=True,
                        disabled=index == 0,
                    ):

                        updated_axes = move_axis_up(
                            axes,
                            index,
                        )

                        update_axis_draft_state(updated_axes)
                        clear_axis_errors()
                        st.session_state[MESSAGE_KEY] = "優先順位を変更しました。"
                        st.rerun()



                with control_columns[1]:
                    if st.button(
                        "下へ",
                        icon=":material/arrow_downward:",
                        key=f"job_hunting_axis_down_{index}",
                        use_container_width=True,
                        disabled=index == len(axes) - 1,
                    ):
                        updated_axes = move_axis_down(axes, index)
                        update_axis_draft_state(updated_axes)
                        clear_axis_errors()
                        st.session_state[MESSAGE_KEY] = "優先順位を変更しました。"
                        st.rerun()


                with control_columns[2]:
                    if st.button(
                        "編集",
                        icon=":material/edit:",
                        key=f"job_hunting_axis_edit_{index}",
                        use_container_width=True,
                    ):
                        st.session_state[
                            EDITING_INDEX_KEY
                        ] = index
                        st.session_state[
                            DELETE_CONFIRM_INDEX_KEY
                        ] = None
                        st.rerun()

                with control_columns[3]:
                    if st.button(
                        "削除",
                        icon=":material/delete_outline:",
                        key=f"job_hunting_axis_delete_{index}",
                        use_container_width=True,
                    ):
                         st.session_state[
                             DELETE_CONFIRM_INDEX_KEY
                         ] = index
                         st.session_state[
                             EDITING_INDEX_KEY
                         ] = None
                         st.rerun()

                if(
                    st.session_state.get(
                        DELETE_CONFIRM_INDEX_KEY
                    )
                    == index
                ):
                    st.warning(
                        f"「{axis.axis_title}」を削除しますか？"
                    )

                    delete_columns = st.columns(2)

                    with delete_columns[0]:
                        if st.button(
                             "削除する",
                             key=(
                                 "job_hunting_axis_delete_confirm_"
                                 f"{index}"
                             ),
                             use_container_width=True,
                        ):

                            updated_axes = delete_axis(
                                axes,
                                index,
                            )

                            update_axis_draft_state(updated_axes)
                            clear_axis_errors()

                            st.session_state[
                                DELETE_CONFIRM_INDEX_KEY
                            ] = None
                            st.session_state[MESSAGE_KEY] = (
                                "就活の軸を削除しました。"
                            )
                            st.rerun()

                    with delete_columns[1]:
                        if st.button(
                            "キャンセル",
                            key=(
                                "job_hunting_axis_delete_cancel_"
                                f"{index}"
                            ),
                            use_container_width=True,
                        ):
                            st.session_state[
                                DELETE_CONFIRM_INDEX_KEY
                            ] = None
                            st.rerun()

    render_regenerate_controls()

    if len(axes) >= MAX_AXIS_COUNT:
        st.caption(
            "就活の軸は最大3件です。追加する場合は、既存の軸を削除してください。"
        )

    else:
        if st.button(
            "＋ 軸を追加する",
            key="job_hunting_axis_show_add_form",
        ):
            st.session_state[
                ADD_FORM_VISIBLE_KEY
            ] = True
            st.rerun()

    if st.session_state.get(
        ADD_FORM_VISIBLE_KEY
    ):
        with st.container(border=True):
            st.subheader("新しい軸を追加")

            new_title_key = "job_hunting_axis_new_title"
            new_description_key = "job_hunting_axis_new_description"
            st.markdown("**軸の名称** :red[*]")
            axis_title = st.text_input(
                "軸の名称（必須）",
                max_chars=50,
                placeholder="例）転勤がないこと",
                key=new_title_key,
                label_visibility="collapsed",
            )
            render_axis_field_error(new_title_key)

            st.markdown("**具体的な判断基準** :red[*]")
            axis_description = st.text_area(
                "具体的な判断基準（必須）",
                max_chars=200,
                placeholder=(
                    "例）福岡県内で長期的に"
                    "働ける環境を重視する"
                ),
                key=new_description_key,
                label_visibility="collapsed",
            )
            render_axis_field_error(new_description_key)

            add_columns = st.columns(2)

            with add_columns[0]:
                if st.button(
                    "追加する",
                    key="job_hunting_axis_add",
                    use_container_width=True,
                ):
                    errors = add_axis(
                        axis_title,
                        axis_description,
                    )

                    if errors:
                        set_axis_form_errors(
                            errors,
                            new_title_key,
                            new_description_key,
                        )
                        st.rerun()

                    else:
                        clear_axis_errors()
                        st.session_state[MESSAGE_KEY] = (
                            "就活の軸を下書きへ追加しました。"
                        )
                        st.rerun()

            with add_columns[1]:
                if st.button(
                    "キャンセル",
                    key="job_hunting_axis_add_cancel",
                    use_container_width=True,
                ):
                    st.session_state[
                        ADD_FORM_VISIBLE_KEY
                    ] = False
                    st.rerun()

    st.divider()

    action_columns = st.columns(3)

    with action_columns[0]:
        if st.button(
            "← 価値観へ戻る",
            key="job_hunting_axis_back_bottom",
            use_container_width=True,
        ):
            st.query_params["page"] = "work_values"
            st.rerun()

    with action_columns[1]:
        if st.button(
            "一時保存",
            key="job_hunting_axis_draft_save",
            use_container_width=True,
        ):
            try:
                draft_data = (
                    collect_job_hunting_axis_draft()
                )

                save_job_hunting_axis_draft(
                    draft_data
                )

                st.session_state[MESSAGE_KEY] = (
                    "入力内容を一時保存しました。"
                )

            except Exception as error:
                st.error(
                    "一時保存に失敗しました。"
                    f"\n\n{error}"
                )

    with action_columns[2]:
        if st.button(
            "この内容で確定して次へ →",
            key="job_hunting_axis_save",
            use_container_width=True,
            type="primary",
        ):
            try:
                current_axes = st.session_state.get(
                    AXES_STATE_KEY,
                    [],
                )
                
                errors = save_job_hunting_axis_data(
                    current_axes
                )

                if errors:
                    set_axis_form_errors(errors)
                    st.rerun()

                else:
                    clear_axis_errors()
                    st.query_params["page"] = "career"
                    st.rerun()

            except Exception as error:
                st.error(
                    "保存に失敗しました。"
                    f"\n\n{error}"
                )

    message = st.session_state.pop(
        MESSAGE_KEY,
        None,
    )

    if message:
        st.toast(message)

    st.caption(
        "正式保存が完了すると、"
        "一時保存データは削除されます。"
    )
