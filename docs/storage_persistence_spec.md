# 保存・PostgreSQL移行設計

> 最新状況（2026-09-10）：Google認証・Neon保存・運営者機能を公開環境へ反映済み。本人ログイン、保存、公開サーバー再起動後の復元を確認。2人目の実アカウント検証は未実施。以下の過去の「公開未反映」記録から進捗があるため、[公開反映・受入確認](public_release_status.md)を現在の確認状況の正とする。

更新日：2026年9月10日

## As-Is / To-Beと確認状況

| 項目 | 変更前 | 今回実装した構成 | 確認状況 |
|---|---|---|---|
| 保存先 | ローカルSQLiteのみ | SQLite / Neon PostgreSQLを明示選択 | PostgreSQLへの接続成功、クライアントTLS確認済み |
| ユーザー識別 | Google subと内部ID | 同じ方式を保持 | 実PostgreSQLで同時登録・再ログイン・失効を確認 |
| データ分離 | Repositoryで本人・親の所有者確認 | 同じ検査を両DBで実行 | 実PostgreSQLの25テーブルで分離テスト成功 |
| 採番 | SQLiteの自動採番 | PostgreSQL IDENTITY / RETURNING | 移行テストで既存IDより後の採番を確認 |
| 移行 | 手順のみ | 空の移行先限定・全件照合・1トランザクション | テストデータと実データ25テーブル1,276件で照合成功 |
| バックアップ | SQLiteファイル | PostgreSQLの一貫した読取からSQLiteアーカイブ | テストデータ・移行済み実データでバックアップ照合成功 |
| 運営者機能 | バックアップCLIのみ | 利用者別閲覧・CSV/JSON ZIP出力を追加 | 公開環境への反映・実機確認 |
| 公開環境 | 従来の構成 | 今後PostgreSQLへ接続設定する | 公開への反映・受入検証は未実施 |

## 接続とトランザクション

- `METEA_DATABASE_BACKEND=sqlite`が既定値。`postgresql`を明示すると外部DBへ接続する。不明な値は拒否する。
- 接続文字列は環境変数`METEA_POSTGRES_URL`、またはSecretsの`[storage] postgres_url`から取得。URLをブラウザへ渡さない。接続失敗時にSQLiteへ自動で戻さない。
- NeonのMeTeAプロジェクト（tiny-dawn-99737932）、Singapore、PostgreSQL 18、DB名metea。Freeプランを使用。Googleログインを維持し、Neon Authは使用しない。
- ドライバはpsycopg 3、プロセス内プールの接続数上限は6。Neon側のConnection poolingも使用する。各トランザクションの開始時にsearch_path、UTC、30秒のSQLタイムアウトを設定する。
- `database/postgres.py`でパラメータ記法、行形式、INSERT結果のIDを統一する。値をSQL文字列へ連結しない。SQLite専用DDLは翻訳せず、`schema_postgres.sql`を使う。
- 通常の起動ではスキーマバージョン1を確認するだけで、全テーブルの作成・移行を繰り返さない。
- Googleの同時初回登録はスキーマ単位のトランザクションロックとメール・認証主体の一意制約で制御する。既存ID 1をGoogle利用者ID 2へ自動移管しない。

## 日時・旧データ

更新日時はUTCのTEXT形式を維持する。ホームの活動時刻は明示的な日本時間へ変換する。時刻を含む値を移行時に勝手に変換せず、原値で照合する。
旧DBだけに存在したuser_jobsのtrain_commute_minutes / train_commute_checked_at / train_commute_source_typeも両スキーマに保持する。

## 移行手順

アプリを停止し、移行元への書込みを止めてからSQLiteバックアップを取る。そのスナップショットを入力にする。

```powershell
.\.venv\Scripts\python.exe tools\migrate_to_postgres.py --source backups\snapshot.db --report backups\preflight.json
.\.venv\Scripts\python.exe tools\migrate_to_postgres.py --source backups\snapshot.db --report backups\migration.json --apply
```

--applyなしは事前確認のみ。移行先が空でない場合は停止する。25テーブルと全列を照合してからIDを保持してコピーし、列名順・ID順の内容ハッシュを照合する。採番位置を最大IDへ合わせ、すべて成功した場合だけコミットする。失敗した場合はロールバックする。
移行・照合・バックアップが成功してから、Secretsの保存先をpostgresqlへ変更し、アプリを再起動する。既存のSQLiteを削除しない。切替後に書込みが発生した場合、古いSQLiteへの単純な設定戻しはデータを欠落させるため行わない。

## 運営者バックアップ

```powershell
.\.venv\Scripts\python.exe tools\backup_postgres.py --output backups\metea_postgres_YYYYMMDD_HHMMSS.db
```

REPEATABLE READの読取専用トランザクションで25テーブルを読み、SQLiteへ保存して件数・内容・整合性を検査する。既存の出力ファイルは上書きしない。これは運営者用の全体バックアップであり、一般利用者がアクセスする画面には置かない。復元は空のPostgreSQLスキーマへの移行ツールで行う。
バックアップには個人データが含まれる。Gitへ登録せず、運営者が保管する。定期実行はまだ設定していない。Neonの履歴保持だけを唯一のバックアップにしない。

## 検証範囲と残作業

- SQLiteでは、実Google利用者ID 2の基本情報下書きが再読み込み・アプリプロセス再起動・タブ再アクセスで復元することを確認済み。ブラウザアプリ全体の終了は未確認。
- 基本情報は「次へ」の送信時に下書き保存する。送信前のキー入力だけの内容は保存を保証しない。
- PostgreSQLの実テストは`tests/test_postgres_integration.py`。明示したテスト接続URLとランダムな専用スキーマだけを使い、publicにはテストデータを作らない。
- 自動テストの模擬Googleアカウント2人と、実Googleアカウント2人による検証は別。後者は未実施。
- 公開環境のSecrets・コード反映、再デプロイ後の保存・運営者出力確認は残作業。運営者画面と保存情報・利用目的・外部AI送信説明はローカル実装済み。

参考：[psycopgのトランザクション](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)、[PostgreSQL IDENTITY](https://www.postgresql.org/docs/current/ddl-identity-columns.html)、[Neon料金](https://neon.com/pricing)。無料プランの制限は管理画面で確認する。

## 実行結果（2026年9月10日）

- 通常テスト57件成功。実DBを指定しない実行ではPostgreSQL用テストをスキップする。Python85ファイルの構文を確認。
- 実PostgreSQLテスト28件成功（認証12、データ分離13、パラメータ・ロールバック1、別プロセス復元1、移行・バックアップ1）。制御文字への対応後、関連2件を再実行して成功。
- 既存SQLiteの25テーブル1,276件をpublicスキーマへ移行し、全件の内容ハッシュを照合。既存ID 1とGoogle利用者ID 2を保持。
- 原文のNUL文字で最初の移行が停止したが、トランザクションはロールバック。NULを含む文字列はタグ付きBase64で可逆保存し、読取・バックアップ時に復号する対応後、全件照合に成功した。タグ自体で始まる通常文字列も包んで衝突を避ける。通常の文字列はそのまま保存する。DB管理画面では一部の原文が符号化表示になるが、アプリ・バックアップでは元の内容を使用する。
- ローカルSecretsのMETEA_DATABASE_BACKENDをpostgresqlへ切替済み。Google認証設定・Cookie署名値は保持。実Google利用者ID 2で画面からNeonへの下書き保存を確認。アプリプロセスを再起動して再読み込みした後も、同じ下書きが画面へ復元された。確認用下書きだけを条件付きで削除し、DB・再読み込み後の画面ともに残っていないことを確認した。
- 移行前バックアップ：backups/metea_before_postgres_20260910_213746.db
- 移行照合記録：backups/postgres_migration_20260910_213746.json
- 移行後バックアップ：backups/metea_postgres_verified_20260910_213746.db
- GitHubへのpushとStreamlit公開環境の変更は未実施。公開URLで今回の機能が使える状態とはまだ判断しない。


## 2026年9月10日：運営者確認・出力とデータ説明

As-Is：本人用画面とバックアップCLI。今回：通常利用者の分離を維持したまま、運営者に限り利用者別の保存データ確認・CSV/JSON出力を追加した。この機能の保存内容も対象となる。ログイン前・設定画面に保存情報と利用目的、外部送信の説明を追加した。To-Be：公開設定の反映と、別の実Googleアカウントを含む受入確認。詳細は[運営者データ設計](operator_data_spec.md)を参照。


## 2026-09-10：接続切れ時のエラー修正

公開利用中、初期化後の接続close内rollbackでOperationalErrorが出る報告を受けた。接続が切れた直接の契機（休止・ネットワーク等）は未特定。コードには接続プールの貸出時検査がなく、rollback失敗時にプールへ返却されない不具合があった。
貸出時にConnectionPool.check_connectionを実行し、切れた接続の後片付けは元の例外を上書きせず、必ず返却してプールに破棄・補充させる。ログイン初期化中に通信エラーが残る場合は再試行案内を表示する。書込み・commitの自動再送やSQLiteへの切替はしない。
Neonへの実接続で、この検証プロセス自身の接続だけを切断し、貸出時の交換・切断後のclose・次のSELECT成功を確認。業務データは変更していない。公開環境の長時間休止後の再発有無は継続して確認が必要。
参考：[psycopg接続プールの生存確認](https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-quality)。
