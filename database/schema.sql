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
    nearest_station TEXT NOT NULL DEFAULT '',
    nearest_station_place_id TEXT NOT NULL DEFAULT '',
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
    organizational_culture TEXT NOT NULL DEFAULT '',

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
        source_job_number TEXT NOT NULL DEFAULT '',
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

-- ========================================
-- 求人ごとの電車移動時間
-- ========================================
CREATE TABLE IF NOT EXISTS user_job_commute_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,

    origin_station_name TEXT NOT NULL,
    origin_station_place_id TEXT NOT NULL,
    destination_station_name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'manual',
    checked_at TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users (id),

    FOREIGN KEY (job_id)
        REFERENCES user_jobs (id),

    UNIQUE (
        user_id,
        job_id
    )
);




-- ========================================
-- 求人：AIマッチング評価
-- ========================================
CREATE TABLE IF NOT EXISTS user_job_match_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,

    overall_score INTEGER,
    hope_condition_score INTEGER,
    work_value_score INTEGER,
    career_skill_score INTEGER,
    required_condition_score INTEGER,

    evaluation_coverage INTEGER NOT NULL DEFAULT 0,
    is_provisional INTEGER NOT NULL DEFAULT 1,
    is_stale INTEGER NOT NULL DEFAULT 0,
    stale_reason TEXT NOT NULL DEFAULT '',
    rule_version TEXT NOT NULL DEFAULT '',
    prompt_version TEXT NOT NULL DEFAULT '',
    model_name TEXT NOT NULL DEFAULT '',
    evaluation_result_json TEXT NOT NULL DEFAULT '',
    evaluation_status TEXT NOT NULL DEFAULT 'ready',
    failure_reason TEXT NOT NULL DEFAULT '',
    failed_at TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    result_notice_pending INTEGER NOT NULL DEFAULT 0,
    status_updated_at TEXT,

    matching_points TEXT NOT NULL DEFAULT '',
    concern_points TEXT NOT NULL DEFAULT '',
    confirmation_points TEXT NOT NULL DEFAULT '',
    ai_comment TEXT NOT NULL DEFAULT '',

    evaluated_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,

    FOREIGN KEY (user_id)
        REFERENCES users (id),

    FOREIGN KEY (job_id)
        REFERENCES user_jobs (id),

    UNIQUE (
        user_id,
        job_id
    )
);


-- ========================================
-- 求人：応募判断
-- ========================================
CREATE TABLE IF NOT EXISTS user_job_application_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,

    decision_status TEXT NOT NULL DEFAULT '',
    next_action TEXT NOT NULL DEFAULT '',
    action_deadline TEXT,
    memo TEXT NOT NULL DEFAULT '',

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,

    FOREIGN KEY (user_id)
        REFERENCES users (id),

    FOREIGN KEY (job_id)
        REFERENCES user_jobs (id),

    UNIQUE (
        user_id,
        job_id
    )
);

-- ========================================
-- 求人：確認項目に対する利用者判断
-- ========================================
CREATE TABLE IF NOT EXISTS user_job_confirmation_resolutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    item_key TEXT NOT NULL,
    item_name TEXT NOT NULL DEFAULT '',
    item_reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'not_required',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users (id),

    FOREIGN KEY (job_id)
        REFERENCES user_jobs (id),

    UNIQUE (
        user_id,
        job_id,
        item_key
    )
);

CREATE TABLE IF NOT EXISTS user_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    actual_route TEXT NOT NULL DEFAULT '',
    current_phase TEXT NOT NULL DEFAULT '応募準備',
    phase_category TEXT NOT NULL DEFAULT '応募準備',
    selection_stage TEXT NOT NULL DEFAULT '',
    selection_result TEXT NOT NULL DEFAULT '',
    application_date TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (job_id) REFERENCES user_jobs (id),
    UNIQUE (user_id, job_id, actual_route)
);

CREATE TABLE IF NOT EXISTS application_phase_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    selection_stage TEXT NOT NULL DEFAULT '',
    selection_result TEXT NOT NULL DEFAULT '',
    application_id INTEGER NOT NULL,
    phase_name TEXT NOT NULL,
    phase_category TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES user_applications (id)
);

CREATE TABLE IF NOT EXISTS application_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    milestone_type TEXT NOT NULL,
    detail_name TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    schedule_kind TEXT NOT NULL DEFAULT 'event',
    scheduled_date TEXT,
    start_time TEXT NOT NULL DEFAULT '',
    end_time TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    rescheduled_from_id INTEGER,
    deleted_at TEXT,
    memo TEXT NOT NULL DEFAULT '',
    completed_at TEXT,
    cancelled_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES user_applications (id),
    FOREIGN KEY (rescheduled_from_id) REFERENCES application_milestones (id)
);

CREATE TABLE IF NOT EXISTS application_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    is_automatic INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES user_applications (id)
);

CREATE TABLE IF NOT EXISTS application_preparations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    scope TEXT NOT NULL DEFAULT 'selection',
    selection_type TEXT NOT NULL DEFAULT '',
    theme_key TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    is_completed INTEGER NOT NULL DEFAULT 0,
    is_custom INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES user_applications (id),
    UNIQUE (application_id, scope, selection_type, theme_key)
);

CREATE TABLE IF NOT EXISTS user_preparation_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    theme_key TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    is_completed INTEGER NOT NULL DEFAULT 0,
    is_custom INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE (user_id, theme_key)
);

CREATE TABLE IF NOT EXISTS user_general_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_type TEXT NOT NULL,
    title TEXT NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target_page TEXT NOT NULL DEFAULT 'home',
    target_id INTEGER,
    icon_name TEXT NOT NULL DEFAULT 'user.svg',
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_applications_user_status ON user_applications (user_id, status);
CREATE INDEX IF NOT EXISTS idx_milestones_date ON application_milestones (scheduled_date, status);
CREATE INDEX IF NOT EXISTS idx_activities_application_date ON application_activities (application_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_preparations_application ON application_preparations (application_id, scope, selection_type);
CREATE INDEX IF NOT EXISTS idx_preparation_templates_user ON user_preparation_templates (user_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_general_activities_user_date ON user_general_activities (user_id, occurred_at);
INSERT OR IGNORE INTO users (id)
VALUES (1);
