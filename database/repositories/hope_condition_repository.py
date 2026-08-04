"""希望条件の保存・取得を担当するRepository。"""

from datetime import date

from database.connection import get_connection
from models import HopeCondition, HopeConditionItem


def save_hope_conditions(
    user_id: int,
    hope_condition: HopeCondition,
    items: list[HopeConditionItem],
    draft_form_name: str,
) -> None:
    """希望条件を正式保存し、下書きを削除する。"""

    connection = get_connection()

    try:
        # ------------------------------------------
        # 単一値の希望条件を保存
        # ------------------------------------------

        connection.execute(
            """
            INSERT INTO user_hope_conditions (
                user_id,
                minimum_salary,
                desired_salary,
                ideal_salary,
                commute_minutes,
                transfer_condition,
                commute_priority,
                transfer_priority,
                overtime_limit,
                overtime_priority,
                start_time,
                start_time_priority,
                end_time,
                end_time_priority,
                shift_work,
                shift_work_priority,
                night_work,
                night_work_priority,
                holiday_priority,
                annual_holidays,
                annual_holiday_priority,
                available_date,
                other_jobs,
                other_conditions
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                minimum_salary = excluded.minimum_salary,
                desired_salary = excluded.desired_salary,
                ideal_salary = excluded.ideal_salary,
                commute_minutes = excluded.commute_minutes,
                transfer_condition = excluded.transfer_condition,
                commute_priority = excluded.commute_priority,
                transfer_priority = excluded.transfer_priority,
                overtime_limit = excluded.overtime_limit,
                overtime_priority = excluded.overtime_priority,
                start_time = excluded.start_time,
                start_time_priority = excluded.start_time_priority,
                end_time = excluded.end_time,
                end_time_priority = excluded.end_time_priority,
                shift_work = excluded.shift_work,
                shift_work_priority = excluded.shift_work_priority,
                night_work = excluded.night_work,
                night_work_priority = excluded.night_work_priority,
                holiday_priority = excluded.holiday_priority,
                annual_holidays = excluded.annual_holidays,
                annual_holiday_priority =
                    excluded.annual_holiday_priority,
                available_date = excluded.available_date,
                other_jobs = excluded.other_jobs,
                other_conditions = excluded.other_conditions,
                updated_at = CURRENT_TIMESTAMP,
                deleted_at = NULL
            """,
            (
                user_id,
                hope_condition.minimum_salary,
                hope_condition.desired_salary,
                hope_condition.ideal_salary,
                hope_condition.commute_minutes,
                hope_condition.transfer_condition,
                hope_condition.commute_priority,
                hope_condition.transfer_priority,
                hope_condition.overtime_limit,
                hope_condition.overtime_priority,
                hope_condition.start_time,
                hope_condition.start_time_priority,
                hope_condition.end_time,
                hope_condition.end_time_priority,
                hope_condition.shift_work,
                hope_condition.shift_work_priority,
                hope_condition.night_work,
                hope_condition.night_work_priority,
                hope_condition.holiday_priority,
                hope_condition.annual_holidays,
                hope_condition.annual_holiday_priority,
                (
                    hope_condition.available_date.isoformat()
                    if hope_condition.available_date is not None
                    else None
                ),
                hope_condition.other_jobs,
                hope_condition.other_conditions,
            ),
        )

        # ------------------------------------------
        # 複数値の希望条件を入れ替える
        # ------------------------------------------

        connection.execute(
            """
            DELETE FROM user_hope_condition_items
            WHERE user_id = ?
            """,
            (user_id,),
        )

        if items:
            connection.executemany(
                """
                INSERT INTO user_hope_condition_items (
                    user_id,
                    condition_type,
                    condition_value,
                    priority,
                    rank,
                    detail_value
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        user_id,
                        item.condition_type,
                        item.condition_value,
                        item.priority,
                        item.rank,
                        item.detail_value,
                    )
                    for item in items
                ],
            )

        # ------------------------------------------
        # 正式保存後に下書きを削除
        # ------------------------------------------

        connection.execute(
            """
            DELETE FROM form_drafts
            WHERE user_id = ?
              AND form_name = ?
            """,
            (
                user_id,
                draft_form_name,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_hope_condition(
    user_id: int,
) -> HopeCondition | None:
    """正式保存済みの単一値希望条件を取得する。"""

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                minimum_salary,
                desired_salary,
                ideal_salary,
                commute_minutes,
                transfer_condition,
                commute_priority,
                transfer_priority,
                overtime_limit,
                overtime_priority,
                start_time,
                start_time_priority,
                end_time,
                end_time_priority,
                shift_work,
                shift_work_priority,
                night_work,
                night_work_priority,
                holiday_priority,
                annual_holidays,
                annual_holiday_priority,
                available_date,
                other_jobs,
                other_conditions
            FROM user_hope_conditions
            WHERE user_id = ?
              AND deleted_at IS NULL
            """,
            (user_id,),
        ).fetchone()

    finally:
        connection.close()

    if row is None:
        return None

    available_date = (
        date.fromisoformat(row["available_date"])
        if row["available_date"]
        else None
    )

    return HopeCondition(
        minimum_salary=row["minimum_salary"],
        desired_salary=row["desired_salary"],
        ideal_salary=row["ideal_salary"],
        commute_minutes=row["commute_minutes"],
        transfer_condition=row["transfer_condition"],
        commute_priority=row["commute_priority"],
        transfer_priority=row["transfer_priority"],
        overtime_limit=row["overtime_limit"],
        overtime_priority=row["overtime_priority"],
        start_time=row["start_time"],
        start_time_priority=row["start_time_priority"],
        end_time=row["end_time"],
        end_time_priority=row["end_time_priority"],
        shift_work=row["shift_work"],
        shift_work_priority=row["shift_work_priority"],
        night_work=row["night_work"],
        night_work_priority=row["night_work_priority"],
        holiday_priority=row["holiday_priority"],
        annual_holidays=row["annual_holidays"],
        annual_holiday_priority=(
            row["annual_holiday_priority"]
        ),
        available_date=available_date,
        other_jobs=row["other_jobs"],
        other_conditions=row["other_conditions"],
    )


def get_hope_condition_items(
    user_id: int,
) -> list[HopeConditionItem]:
    """正式保存済みの複数値希望条件を取得する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                condition_type,
                condition_value,
                priority,
                rank,
                detail_value
            FROM user_hope_condition_items
            WHERE user_id = ?
            ORDER BY
                condition_type,
                rank,
                id
            """,
            (user_id,),
        ).fetchall()

    finally:
        connection.close()

    return [
        HopeConditionItem(
            condition_type=row["condition_type"],
            condition_value=row["condition_value"],
            priority=row["priority"],
            rank=row["rank"],
            detail_value=row["detail_value"],
        )
        for row in rows
    ]