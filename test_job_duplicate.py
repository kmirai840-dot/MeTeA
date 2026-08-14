from models import Job
from services.job_service import (
    DUPLICATE_DIFFERENT_SOURCE,
    DUPLICATE_EXACT,
    DUPLICATE_NONE,
    DUPLICATE_POSSIBLE,
    check_duplicate_job,
    create_job_data,
)
from database.connection import get_connection


TEST_COMPANY_PREFIX = "MeTeA重複判定テスト"


def delete_test_jobs():
    """今回のテストデータだけを物理削除する。"""

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT id
            FROM user_jobs
            WHERE company_name LIKE ?
            """,
            (f"{TEST_COMPANY_PREFIX}%",),
        ).fetchall()

        job_ids = [
            row["id"]
            for row in rows
        ]

        for job_id in job_ids:
            connection.execute(
                """
                DELETE FROM user_job_sources
                WHERE job_id = ?
                """,
                (job_id,),
            )

            connection.execute(
                """
                DELETE FROM user_job_items
                WHERE job_id = ?
                """,
                (job_id,),
            )

            connection.execute(
                """
                DELETE FROM user_jobs
                WHERE id = ?
                """,
                (job_id,),
            )

        connection.commit()

    finally:
        connection.close()


def run_test(
    name: str,
    job: Job,
    expected: str,
):
    """重複判定結果と期待値を比較する。"""

    actual, job_id = check_duplicate_job(
        job
    )

    result = (
        "OK"
        if actual == expected
        else "NG"
    )

    print(
        f"{result} | "
        f"{name} | "
        f"expected={expected} | "
        f"actual={actual} | "
        f"job_id={job_id}"
    )


try:
    delete_test_jobs()

    # ------------------------------------
    # 基準求人1
    # ------------------------------------

    base_job = Job(
        registration_method="manual",
        company_name=(
            f"{TEST_COMPANY_PREFIX}A"
        ),
        job_title="Process Improvement",
        occupation="Process Improvement",
        job_summary="Improve internal processes",
        job_number="AGENT-A-001",
        source_type="Agent",
        source_name="AgentA",
        source_url="https://example.com/test/a",
    )

    base_job_id, errors = create_job_data(
        base_job
    )

    if errors:
        raise RuntimeError(errors)

    # ------------------------------------
    # EXACT
    # ------------------------------------

    run_test(
        "EXACT",
        Job(
            company_name=(
                f"{TEST_COMPANY_PREFIX}A"
            ),
            job_title="Process Improvement",
            occupation="Process Improvement",
            job_summary="Improve internal processes",
            job_number="AGENT-A-001",
            source_type="Agent",
            source_name="AgentA",
        ),
        DUPLICATE_EXACT,
    )

    # ------------------------------------
    # DIFFERENT SOURCE
    # ------------------------------------

    run_test(
        "DIFFERENT_SOURCE",
        Job(
            company_name=(
                f"{TEST_COMPANY_PREFIX}A"
            ),
            job_title="Process Improvement",
            occupation="Process Improvement",
            job_summary="Improve internal processes",
            source_url="https://example.com/test/a",
            job_number="AGENT-B-999",
            source_type="Agent",
            source_name="AgentB",
        ),
        DUPLICATE_DIFFERENT_SOURCE,
    )

    # ------------------------------------
    # POSSIBLE
    # ------------------------------------

    run_test(
        "POSSIBLE",
        Job(
            company_name=(
                f"{TEST_COMPANY_PREFIX}A"
            ),
            job_title="Process Improvement",
            occupation="Different Occupation",
            job_summary="Different work",
            job_number="OTHER-001",
            source_type="Agent",
            source_name="AgentC",
        ),
        DUPLICATE_POSSIBLE,
    )

    # ------------------------------------
    # NONE
    # ------------------------------------

    run_test(
        "NONE",
        Job(
            company_name=(
                f"{TEST_COMPANY_PREFIX}A"
            ),
            job_title="Completely Different",
            occupation="HR",
            job_summary="Recruit employees",
            job_number="OTHER-999",
            source_type="Agent",
            source_name="AgentD",
        ),
        DUPLICATE_NONE,
    )

    # ------------------------------------
    # POSSIBLE より SAME を優先
    # ------------------------------------

    possible_first_job = Job(
        registration_method="manual",
        company_name=(
            f"{TEST_COMPANY_PREFIX}B"
        ),
        job_title="Target Role",
        occupation="HR",
        job_summary="Recruit employees",
        job_number="AGENT-X-001",
        source_type="Agent",
        source_name="AgentX",
    )

    possible_first_id, errors = create_job_data(
        possible_first_job
    )

    if errors:
        raise RuntimeError(errors)

    same_later_job = Job(
        registration_method="manual",
        company_name=(
            f"{TEST_COMPANY_PREFIX}B"
        ),
        job_title="Different Title",
        occupation="Business Analyst",
        job_summary="Analyze business processes",
        job_number="AGENT-Z-999",
        source_type="Agent",
        source_name="AgentZ",
    )

    same_later_id, errors = create_job_data(
        same_later_job
    )

    if errors:
        raise RuntimeError(errors)

    run_test(
        "SAME_OVER_POSSIBLE",
        Job(
            company_name=(
                f"{TEST_COMPANY_PREFIX}B"
            ),
            job_title="Target Role",
            occupation="Different Occupation",
            job_summary="Different work",
            job_number="AGENT-Z-999",
            source_type="Agent",
            source_name="AgentZ",
        ),
        DUPLICATE_EXACT,
    )

finally:
    delete_test_jobs()
    print("test data deleted")