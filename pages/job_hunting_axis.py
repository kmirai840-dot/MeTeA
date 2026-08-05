"""就活の軸画面の表示を担当するモジュール。"""

import streamlit as st

from models import JobHuntingAxis
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

        st.session_state[AXES_STATE_KEY] = [
            dict_to_axis(axis_data)
            for axis_data in draft_axes
            if isinstance(axis_data, dict)
        ]

    else:
        st.session_state[AXES_STATE_KEY] = (
            load_job_hunting_axis_data()
        )

    st.session_state[AXES_LOADED_KEY] = True

    if ADD_FORM_VISIBLE_KEY not in st.session_state:
        st.session_state[ADD_FORM_VISIBLE_KEY] = False

    if EDITING_INDEX_KEY not in st.session_state:
        st.session_state[EDITING_INDEX_KEY] = None

    if DELETE_CONFIRM_INDEX_KEY not in st.session_state:
        st.session_state[DELETE_CONFIRM_INDEX_KEY] = None


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

    if len(description) > 200:
        errors.append(
            "補足説明は200文字以内で入力してください。"
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

    save_errors = save_job_hunting_axis_data(
        updated_axes
    )

    if save_errors:
        return save_errors

    st.session_state[AXES_STATE_KEY] = updated_axes
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

    if len(description) > 200:
        errors.append(
            "補足説明は200文字以内で入力してください。"
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

    save_errors = save_job_hunting_axis_data(
        updated_axes
    )

    if save_errors:
        return save_errors

    st.session_state[AXES_STATE_KEY] = updated_axes
    st.session_state[EDITING_INDEX_KEY] = None

    return []


def render_job_hunting_axis_page() -> None:
    """就活の軸画面を表示する。"""

    initialize_job_hunting_axis_state()

    if st.button(
        "← トップ画面へ戻る",
        key="job_hunting_axis_back_top",
    ):
        st.query_params.clear()
        st.rerun()

    st.title("就活の軸")

    st.write(
        "仕事選びで大切にしたい判断基準を、"
        "優先順位の高い順に整理してください。"
    )

    st.progress(
        3 / 6,
        text="入力のステップ 3 / 6",
    )

    st.info(
        "就活の軸は最大3件まで登録できます。\n\n"
        "初期版では自由入力で登録し、"
        "AIによる提案機能は後から追加します。"
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
        with st.container(border=True):

            if (
                st.session_state.get(
                    EDITING_INDEX_KEY
                )
                == index
            ):
                st.markdown(
                     f"### {axis.priority_rank}位を編集中"
                )

                edit_title = st.text_input(
                    "軸の名称",
                     value=axis.axis_title,
                      max_chars=50,
                      key=f"job_hunting_axis_edit_title_{index}",
                )

                edit_description = st.text_area(
                    "補足説明（任意）",
                    value=axis.axis_description,
                    max_chars=200,
                    key=(
                        "job_hunting_axis_edit_description_"
                        f"{index}"
                    ),
                )

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
                             for error in errors:
                                 st.error(error)

                        else:
                            st.session_state[MESSAGE_KEY] = (
                                "就活の軸を保存しました。"
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
                    f"### {axis.priority_rank}位　"
                    f"{axis.axis_title}"
                )

                if axis.axis_description:
                    st.write(
                        axis.axis_description
                    )

                st.caption(
                    "本人入力"
                    if axis.source_type == "manual"
                    else "AI提案"
                )

                control_columns = st.columns(
                    [1, 1, 1.4, 1.4]
                )

                with control_columns[0]:
                    if index > 0:
                        if st.button(
                            "↑",
                            key=f"job_hunting_axis_up_{index}",
                            use_container_width=True,
                        ):

                            updated_axes = move_axis_up(
                                axes,
                                index,
                            )

                            save_errors = save_job_hunting_axis_data(
                                updated_axes
                            )

                            if save_errors:
                                for error in save_errors:
                                    st.error(error)

                            else:
                                st.session_state[AXES_STATE_KEY] = updated_axes
                                st.session_state[MESSAGE_KEY] = (
                                    "優先順位を保存しました。"
                                )

                                st.rerun()



                with control_columns[1]:
                    if index < len(axes) - 1:
                        if st.button(
                            "↓",
                            key=f"job_hunting_axis_down_{index}",
                            use_container_width=True,
                        ):
                            updated_axes = move_axis_down(
                                axes,
                                index,
                            )

                            save_errors = save_job_hunting_axis_data(
                                updated_axes
                            )

                            if save_errors:
                                for error in save_errors:
                                    st.error(error)
                            else:
                                st.session_state[AXES_STATE_KEY] = updated_axes
                                st.session_state[MESSAGE_KEY] = (
                                    "優先順位を保存しました。"
                                )
                                st.rerun()


                with control_columns[2]:
                    if st.button(
                        "編集",
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

                            save_errors = save_job_hunting_axis_data(
                                updated_axes
                            )

                            if save_errors:
                                for error in save_errors:
                                    st.error(error)
                                st.stop()

                            st.session_state[AXES_STATE_KEY] = updated_axes

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

    if len(axes) >= MAX_AXIS_COUNT:
        st.warning(
            "登録できる就活の軸は最大3件です。"
            "追加する場合は既存の軸を削除してください。"
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

            axis_title = st.text_input(
                "軸の名称",
                max_chars=50,
                placeholder="例）転勤がないこと",
                key="job_hunting_axis_new_title",
            )

            axis_description = st.text_area(
                "補足説明（任意）",
                max_chars=200,
                placeholder=(
                    "例）福岡県内で長期的に"
                    "働ける環境を重視する"
                ),
                key="job_hunting_axis_new_description",
            )

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
                        for error in errors:
                            st.error(error)

                    else:
                        st.session_state[MESSAGE_KEY] = (
                            "就活の軸を追加しました。"
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
            "← トップ画面へ戻る",
            key="job_hunting_axis_back_bottom",
            use_container_width=True,
        ):
            st.query_params.clear()
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
            "保存する",
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
                    for error in errors:
                        st.error(error)

                else:
                    st.session_state[MESSAGE_KEY] = (
                        "就活の軸を保存しました。"
                    )
                    st.rerun()

            except Exception as error:
                st.error(
                    "保存に失敗しました。"
                    f"\n\n{error}"
                )

    message = st.session_state.get(
        MESSAGE_KEY
    )

    if message:
        st.success(message)

    st.caption(
        "正式保存が完了すると、"
        "一時保存データは削除されます。"
    )