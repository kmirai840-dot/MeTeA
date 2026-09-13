"""ランダムな一時スキーマでのみ実行する取得改善のPostgreSQL回帰検証。"""
from test_postgres_integration import PostgresFixture
import test_scoped_screen_reads as scoped
import test_operator as operator


class PostgresScopedReadTest(PostgresFixture, scoped.ScopedReadTest):
    pass


class PostgresOperatorReadTest(PostgresFixture, operator.OperatorTest):
    pass
