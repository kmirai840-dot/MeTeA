"""既存DBへ独立スキル表だけを追加する。既存データは変更しない。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def apply():
    from services.runtime_config import configure_runtime_secrets
    from database.connection import get_connection
    configure_runtime_secrets()
    connection = get_connection()
    try:
        connection.execute((ROOT / "database/user_skills.sql").read_text(encoding="utf-8"))
        connection.commit()
        print("user_skills table ready")
    except Exception as error:
        connection.rollback()
        print("Migration failed:", type(error).__name__)
        raise SystemExit(1) from None
    finally:
        connection.close()


if __name__ == "__main__":
    apply()
