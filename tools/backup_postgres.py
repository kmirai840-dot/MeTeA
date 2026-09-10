"""PostgreSQLの一貫したスナップショットを復元可能なSQLiteへ保存する。

運営者のローカルCLI専用。出力には個人データが含まれる。Gitへ登録しない。
"""
import argparse
import os
from pathlib import Path
import re
import sqlite3
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def backup(output: Path, schema='public'):
    from database.postgres import PostgresConnection
    from database.user_account_schema import ensure_user_account_schema
    from tools.migrate_to_postgres import digest
    from psycopg import sql
    output = output.resolve()
    partial = output.with_suffix(output.suffix + '.partial')
    if output.exists() or partial.exists():
        raise RuntimeError('バックアップ出力先が存在します。上書きしません。')
    url = os.getenv('METEA_POSTGRES_URL', '')
    if not url:
        url = tomllib.loads((ROOT / '.streamlit/secrets.toml').read_text(encoding='utf-8-sig'))['storage']['postgres_url']
    os.environ['METEA_POSTGRES_SCHEMA'] = schema
    source = PostgresConnection(url)
    destination = None
    try:
        source.raw.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        source._prepare()
        if source.execute('SELECT version FROM metea_schema_version').fetchone()[0] != 1:
            raise RuntimeError('バックアップ対象のスキーマが一致しません。')
        output.parent.mkdir(parents=True, exist_ok=True)
        partial.touch(exist_ok=False)
        destination = sqlite3.connect(partial)
        destination.executescript((ROOT / 'database/schema.sql').read_text(encoding='utf-8'))
        ensure_user_account_schema(destination)
        destination.execute('DELETE FROM users WHERE id=1')
        destination.execute('PRAGMA defer_foreign_keys=ON')
        tables = re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', (ROOT / 'database/schema.sql').read_text(encoding='utf-8'))
        report = {}
        for table in tables:
            columns = sorted(r[1] for r in destination.execute(f'PRAGMA table_info("{table}")'))
            rows = source.raw.execute(sql.SQL('SELECT {} FROM {} ORDER BY id').format(
                sql.SQL(',').join(map(sql.Identifier, columns)), sql.Identifier(schema, table))).fetchall()
            placeholders = ','.join('?' for _ in columns)
            column_list = ','.join('"' + name + '"' for name in columns)
            destination.executemany(f'INSERT INTO "{table}" ({column_list}) VALUES ({placeholders})', [tuple(row) for row in rows])
            saved = destination.execute(f'SELECT {column_list} FROM "{table}" ORDER BY id').fetchall()
            if digest(rows) != digest(saved):
                raise RuntimeError(f'バックアップの照合に失敗しました: {table}')
            report[table] = {'rows': len(rows), 'sha256': digest(saved)}
        if destination.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('バックアップの参照整合性に問題があります。')
        destination.commit()
        if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('バックアップの整合性に問題があります。')
        destination.close()
        destination = None
        partial.rename(output)
        return report
    finally:
        if destination is not None:
            destination.close()
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--schema', default='public')
    args = parser.parse_args()
    try:
        report = backup(args.output, args.schema)
        print(f'バックアップと全件照合完了: {len(report)} tables')
    except Exception as error:
        print('バックアップを停止しました:', type(error).__name__)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
