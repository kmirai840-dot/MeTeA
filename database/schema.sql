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

INSERT OR IGNORE INTO users (id)
VALUES (1);