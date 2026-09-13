"""既存の確認判断を保持して結果保存欄を追加する。"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def apply():
    from services.runtime_config import configure_runtime_secrets
    from database.connection import get_connection
    from database.confirmation_schema import ensure_confirmation_schema
    configure_runtime_secrets()
    connection = get_connection()
    try:
        before = connection.execute('SELECT COUNT(*) FROM user_job_confirmation_resolutions').fetchone()[0]
        ensure_confirmation_schema(connection)
        after = connection.execute('SELECT COUNT(*) FROM user_job_confirmation_resolutions').fetchone()[0]
        assert before == after
        connection.commit()
        print('Confirmation result column ready; existing row count unchanged.')
    except Exception as error:
        connection.rollback()
        print('Migration failed:', type(error).__name__)
        raise SystemExit(1) from None
    finally:
        connection.close()

if __name__ == '__main__':
    apply()
