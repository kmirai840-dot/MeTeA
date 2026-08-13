PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    gender TEXT NOT NULL,
    birth_date TEXT NOT NULL,
    prefecture TEXT NOT NULL,
    municipality TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS user_hope_conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    minimum_salary INTEGER NOT NULL DEFAULT 0,
    desired_salary INTEGER NOT NULL DEFAULT 0,
    ideal_salary INTEGER NOT NULL DEFAULT 0,
    commute_minutes INTEGER NOT NULL DEFAULT 0,
    transfer_condition TEXT NOT NULL,
    commute_priority TEXT NOT NULL,
    transfer_priority TEXT NOT NULL,
    overtime_limit INTEGER NOT NULL DEFAULT 0,
    overtime_priority TEXT NOT NULL,
    start_time TEXT NOT NULL,
    start_time_priority TEXT NOT NULL,
    end_time TEXT NOT NULL,
    end_time_priority TEXT NOT NULL,
    shift_work TEXT NOT NULL,
    shift_work_priority TEXT NOT NULL,
    night_work TEXT NOT NULL,
    night_work_priority TEXT NOT NULL,
    holiday_priority TEXT NOT NULL,
    annual_holidays INTEGER NOT NULL DEFAULT 0,
    annual_holiday_priority TEXT NOT NULL,
    available_date TEXT,
    other_jobs TEXT NOT NULL DEFAULT '',
    other_conditions TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS user_hope_condition_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    condition_type TEXT NOT NULL,
    condition_value TEXT NOT NULL,
    priority TEXT NOT NULL,
    rank INTEGER,
    detail_value TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS user_job_hunting_axes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    axis_title TEXT NOT NULL,
    axis_description TEXT NOT NULL DEFAULT '',
    priority_rank INTEGER NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
    );

CREATE TABLE IF NOT EXISTS form_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    form_name TEXT NOT NULL,
    draft_data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, form_name),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS user_work_value_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question_type TEXT NOT NULL,
    selected_value TEXT NOT NULL,
    priority_rank INTEGER NOT NULL,
    custom_value TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS user_work_value_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    detail_type TEXT NOT NULL,
    detail_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS user_work_style_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question_type TEXT NOT NULL,
    answer_score INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- ========================================
-- 職務経歴：会社
-- ========================================
CREATE TABLE IF NOT EXISTS user_careers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    employment_type TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT '',
    start_year INTEGER NOT NULL,
    start_month INTEGER NOT NULL,
    end_year INTEGER,
    end_month INTEGER,
    is_current INTEGER NOT NULL DEFAULT 0,
    display_order INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- ========================================
-- 職務経歴：部署・役割
-- ========================================
CREATE TABLE IF NOT EXISTS user_career_histories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    career_id INTEGER NOT NULL,
    department TEXT NOT NULL DEFAULT '',
    position TEXT NOT NULL DEFAULT '',
    occupation TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    start_month INTEGER NOT NULL,
    end_year INTEGER,
    end_month INTEGER,
    job_description TEXT NOT NULL DEFAULT '',
    achievements TEXT NOT NULL DEFAULT '',
    display_order INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (career_id) REFERENCES user_careers (id)
);


-- ========================================
-- 求人情報
-- ========================================
CREATE TABLE IF NOT EXISTS user_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,

    -- 情報元
    registration_method TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    source_text TEXT NOT NULL DEFAULT '',
    acquired_at TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT '',

    -- 求人基本情報
    company_name TEXT NOT NULL DEFAULT '',
    job_title TEXT NOT NULL DEFAULT '',
    job_number TEXT NOT NULL DEFAULT '',
    publication_start_date TEXT NOT NULL DEFAULT '',
    publication_end_date TEXT NOT NULL DEFAULT '',
    industry TEXT NOT NULL DEFAULT '',
    business_description TEXT NOT NULL DEFAULT '',
    employee_count_min TEXT NOT NULL DEFAULT '',
    employee_count_max TEXT NOT NULL DEFAULT '',
    employee_count TEXT NOT NULL DEFAULT '',
    established_date TEXT NOT NULL DEFAULT '',
    capital TEXT NOT NULL DEFAULT '',
    listing_status TEXT NOT NULL DEFAULT '',

    -- 募集内容
    occupation TEXT NOT NULL DEFAULT '',
    department TEXT NOT NULL DEFAULT '',
    planned_hires TEXT NOT NULL DEFAULT '',
    recruitment_reason TEXT NOT NULL DEFAULT '',

    -- 仕事内容
    job_summary TEXT NOT NULL DEFAULT '',
    responsibility_scope TEXT NOT NULL DEFAULT '',
    customers TEXT NOT NULL DEFAULT '',
    internal_stakeholders TEXT NOT NULL DEFAULT '',
    external_partners TEXT NOT NULL DEFAULT '',
    goals_kpi TEXT NOT NULL DEFAULT '',
    expected_results TEXT NOT NULL DEFAULT '',

    -- 勤務条件
    employment_type TEXT NOT NULL DEFAULT '',
    probation_period_status TEXT NOT NULL DEFAULT '',
    probation_period_months TEXT NOT NULL DEFAULT '',
    probation_period TEXT NOT NULL DEFAULT '',
    prefecture TEXT NOT NULL DEFAULT '',
    municipality TEXT NOT NULL DEFAULT '',
    nearest_station TEXT NOT NULL DEFAULT '',
    transfer_required TEXT NOT NULL DEFAULT '',
    work_style TEXT NOT NULL DEFAULT '',
    start_time TEXT NOT NULL DEFAULT '',
    end_time TEXT NOT NULL DEFAULT '',
    break_minutes TEXT NOT NULL DEFAULT '',
    scheduled_work_hours TEXT NOT NULL DEFAULT '',
    flextime TEXT NOT NULL DEFAULT '',
    overtime TEXT NOT NULL DEFAULT '',
    holidays TEXT NOT NULL DEFAULT '',
    annual_holidays TEXT NOT NULL DEFAULT '',

    -- 給与・待遇
    wage_type TEXT NOT NULL DEFAULT '',
    monthly_salary_min TEXT NOT NULL DEFAULT '',
    monthly_salary_max TEXT NOT NULL DEFAULT '',
    base_salary_min TEXT NOT NULL DEFAULT '',
    base_salary_max TEXT NOT NULL DEFAULT '',
    fixed_overtime_system TEXT NOT NULL DEFAULT '',
    fixed_overtime_pay_min TEXT NOT NULL DEFAULT '',
    fixed_overtime_pay_max TEXT NOT NULL DEFAULT '',
    overtime_extra_pay TEXT NOT NULL DEFAULT '',

    monthly_salary TEXT NOT NULL DEFAULT '',
    annual_salary TEXT NOT NULL DEFAULT '',
    expected_salary_min TEXT NOT NULL DEFAULT '',
    expected_salary_max TEXT NOT NULL DEFAULT '',
    fixed_overtime_hours TEXT NOT NULL DEFAULT '',
    fixed_overtime_pay TEXT NOT NULL DEFAULT '',
    bonus TEXT NOT NULL DEFAULT '',
    salary_increase TEXT NOT NULL DEFAULT '',
    incentive TEXT NOT NULL DEFAULT '',

    -- 福利厚生
    social_insurance TEXT NOT NULL DEFAULT '',
    commuting_allowance TEXT NOT NULL DEFAULT '',
    housing_allowance TEXT NOT NULL DEFAULT '',
    retirement_plan TEXT NOT NULL DEFAULT '',
    qualification_support TEXT NOT NULL DEFAULT '',
    training_program TEXT NOT NULL DEFAULT '',

    -- 選考情報
    document_screening_status TEXT NOT NULL DEFAULT '',
    document_screening TEXT NOT NULL DEFAULT '',
    interview TEXT NOT NULL DEFAULT '',
    aptitude_test_status TEXT NOT NULL DEFAULT '',
    aptitude_test TEXT NOT NULL DEFAULT '',
    interview_count_min TEXT NOT NULL DEFAULT '',
    interview_count_max TEXT NOT NULL DEFAULT '',
    interview_count TEXT NOT NULL DEFAULT '',
    expected_join_date TEXT NOT NULL DEFAULT '',

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,

    FOREIGN KEY (user_id)
        REFERENCES users (id)
);


-- ========================================
-- 求人情報：複数値項目
-- ========================================
CREATE TABLE IF NOT EXISTS user_job_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,

    item_type TEXT NOT NULL,
    item_value TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,

    FOREIGN KEY (job_id)
        REFERENCES user_jobs (id)
);


-- ========================================
-- 求人情報：紹介経路
-- ========================================
CREATE TABLE IF NOT EXISTS user_job_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,

    source_type TEXT NOT NULL DEFAULT '',
    source_name TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    source_text TEXT NOT NULL DEFAULT '',
    acquired_at TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',

    is_primary INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,

    FOREIGN KEY (job_id)
        REFERENCES user_jobs (id),

    UNIQUE (
        job_id,
        source_type,
        source_name,
        source_url
    )
);

INSERT OR IGNORE INTO users (id)
VALUES (1);