"""公開デモ環境用の匿名サンプルデータを作成する。"""

from __future__ import annotations

from datetime import date, timedelta

from database.connection import get_connection


DEMO_JOBS = (
    (
        "サンプルテクノロジー株式会社",
        "カスタマーサクセス",
        "SaaS・ソフトウェア",
        "東京都千代田区",
        "企業採用ページ",
        "一次面接予定",
        "選考中",
        "一次面接",
    ),
    (
        "みらい業務支援株式会社",
        "業務企画・オペレーション改善",
        "人材・BPO",
        "福岡県福岡市博多区",
        "転職エージェント",
        "書類選考結果待ち",
        "選考中",
        "書類選考",
    ),
    (
        "ブルーリーフ株式会社",
        "カスタマーサポート運営",
        "IT・通信",
        "福岡県福岡市中央区",
        "求人サイト",
        "応募準備",
        "応募準備",
        "",
    ),
    (
        "オレンジワークス株式会社",
        "営業支援・データ分析",
        "広告・メディア",
        "フルリモート",
        "知人紹介",
        "内定",
        "内定",
        "最終面接",
    ),
)


def seed_demo_data() -> None:
    """利用者データがない場合に限り、架空のデモデータを投入する。"""

    connection = get_connection()

    try:
        existing_jobs = connection.execute(
            "SELECT COUNT(*) FROM user_jobs"
        ).fetchone()[0]
        if existing_jobs:
            return

        connection.execute("INSERT OR IGNORE INTO users (id) VALUES (1)")
        connection.execute(
            """
            INSERT OR IGNORE INTO user_profiles (
                user_id, last_name, first_name, gender, birth_date,
                prefecture, municipality, nearest_station
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, "サンプル", "利用者", "未回答", "1995-01-01", "福岡県", "福岡市", "博多駅"),
        )

        today = date.today()
        for index, job in enumerate(DEMO_JOBS, start=1):
            company, title, industry, location, route, phase, category, stage = job
            prefecture, municipality = (
                ("福岡県", location.replace("福岡県", ""))
                if location.startswith("福岡県")
                else ("東京都", "千代田区")
                if location.startswith("東京都")
                else ("", location)
            )
            cursor = connection.execute(
                """
                INSERT INTO user_jobs (
                    user_id, registration_method, source_type, source_name,
                    company_name, job_title, industry, occupation,
                    job_summary, employment_type, prefecture, municipality,
                    work_style, annual_salary, holidays
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1, "manual", "demo", route, company, title, industry, title,
                    "公開デモ用に作成した架空の求人情報です。", "正社員",
                    prefecture, municipality, "ハイブリッド勤務", "400万円〜600万円",
                    "完全週休2日制",
                ),
            )
            job_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO user_job_application_decisions (
                    user_id, job_id, decision_status, next_action, memo
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (1, job_id, "応募する", "選考状況を確認する", "公開デモ用データ"),
            )
            app_cursor = connection.execute(
                """
                INSERT INTO user_applications (
                    user_id, job_id, actual_route, current_phase,
                    phase_category, selection_stage, selection_result,
                    application_date, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1, job_id, route, phase, category, stage,
                    "通過" if category == "内定" else "",
                    (today - timedelta(days=7 * index)).isoformat(),
                    "active", "公開デモ用データ",
                ),
            )
            application_id = app_cursor.lastrowid
            connection.execute(
                """
                INSERT INTO application_phase_history (
                    application_id, phase_name, phase_category,
                    selection_stage, selection_result
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (application_id, phase, category, stage, ""),
            )

            if category not in {"内定"}:
                scheduled = today + timedelta(days=index + 1)
                connection.execute(
                    """
                    INSERT INTO application_milestones (
                        application_id, milestone_type, title,
                        schedule_kind, scheduled_date, status, memo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        application_id, "その他", "次の対応を確認",
                        "task", scheduled.isoformat(), "pending", "公開デモ用データ",
                    ),
                )

        connection.commit()
    finally:
        connection.close()
