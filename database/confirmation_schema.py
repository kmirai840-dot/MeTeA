"""確認結果の保存欄を既存データを保持して追加する。"""
def ensure_confirmation_schema(connection):
    if getattr(connection, 'dialect', '') == 'postgresql':
        connection.execute("ALTER TABLE user_job_confirmation_resolutions ADD COLUMN IF NOT EXISTS result_text TEXT NOT NULL DEFAULT ''")
    else:
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(user_job_confirmation_resolutions)').fetchall()}
        if 'result_text' not in columns:
            connection.execute("ALTER TABLE user_job_confirmation_resolutions ADD COLUMN result_text TEXT NOT NULL DEFAULT ''")
