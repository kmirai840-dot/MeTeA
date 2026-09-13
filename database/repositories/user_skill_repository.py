"""利用者ごとのツール・スキルを保存する。"""
from database.access_control import require_user_id
from database.connection import get_connection


def get_user_skills(user_id: int) -> str:
    user_id = require_user_id(user_id)
    connection = get_connection()
    try:
        row = connection.execute("SELECT skills_text FROM user_skills WHERE user_id = ?", (user_id,)).fetchone()
        return row["skills_text"] if row else ""
    finally:
        connection.close()


def save_user_skills(user_id: int, text: str) -> None:
    user_id = require_user_id(user_id)
    connection = get_connection()
    try:
        connection.execute("""INSERT INTO user_skills (user_id, skills_text) VALUES (?, ?)
            ON CONFLICT (user_id) DO UPDATE SET skills_text=excluded.skills_text,
            updated_at=CURRENT_TIMESTAMP""", (user_id, text))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
