# MeTeA（就活伴走アプリ）

自己理解、求人比較、応募後の選考管理、選考実績の振り返りを一つの流れで支援するStreamlitアプリです。

## ローカル起動

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py
```

AI評価と駅検索を使用する場合は、プロジェクト直下の`.env`へ次を設定します。

```dotenv
OPENAI_API_KEY=
GOOGLE_MAPS_API_KEY=
```

## Googleログインによる招待制利用（設定作業中）

個別ログイン、許可メール、内部利用者ID、ユーザー別データ分離のコードを実装しています。
設定手順は[docs/google_login_setup.md](docs/google_login_setup.md)、設計は[docs/account_access_spec.md](docs/account_access_spec.md)を参照してください。

1. Google CloudでウェブアプリのOAuthクライアントを作成します。
2. `.streamlit/secrets.toml.example`を参考に、Git管理対象外の`.streamlit/secrets.toml`へ認証設定と許可メールを設定します。
3. `METEA_AUTH_MODE = "google"`で起動します。設定不足・未招待・無効アカウントは利用できません。
4. Cloudへ反映する場合は管理画面のSecretsへ設定し、redirect_uriを公開URLの`/oauth2callback`に変更します。既存APIキーは保持してください。

既存の共通パスワード付きデモを使う場合だけ`METEA_AUTH_MODE = "legacy"`、`APP_ENV = "demo"`を指定します。これは個別ユーザー向け提供ではありません。Googleモードではデモデータを自動生成しません。

実際のAPIキー、OAuthクライアントシークレット、Cookie署名値、許可メール、SQLite DBはGitへ登録しません。

## データについて

保存先は`METEA_DATABASE_BACKEND`でSQLiteまたはPostgreSQLを明示選択します。SQLiteでは`database/metea.db`へ保存します。外部接続はSecretsの`[storage] postgres_url`を設定し、移行を終えてから`postgresql`へ切り替えます。手順・バックアップ・検証範囲は[保存設計](docs/storage_persistence_spec.md)を参照してください。Community Cloud上のSQLiteはデモ用途であり、再起動・再デプロイ時に初期化される可能性があります。ローカルではNeonへの移行と全件照合を完了しました。テストユーザーへの提供には公開環境の切替・保存検証、運営者の閲覧・CSV出力、データ利用説明がまだ必要です。


### 運営者による確認・出力

Googleログインの運営者は設定画面から利用者別の保存内容を確認し、CSV・JSONのZIPを出力できます。Secretsの`access.admin_emails`と`access.allowed_emails`の両方に登録が必要です。ローカル実装・検証済みで、公開環境は未反映です。ログイン前と設定画面には保存情報・利用目的を表示します。詳細は[運営者データ設計](docs/operator_data_spec.md)を参照してください。
