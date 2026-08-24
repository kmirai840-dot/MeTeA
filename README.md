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

## Streamlit Community Cloud

1. GitHubリポジトリと`app.py`を指定してアプリを作成します。
2. Advanced settingsのSecretsへ`.streamlit/secrets.toml.example`と同じキーを登録します。
3. 公開デモでは`APP_ENV = "demo"`を設定します。初回起動時に架空のデモデータが生成されます。
4. `APP_PASSWORD`を設定すると、アプリ本体を開く前に閲覧用パスワードを要求します。

実際のAPIキーや`.streamlit/secrets.toml`、SQLite DBはGitへ登録しません。

## データについて

ローカル版は`database/metea.db`へ保存します。Community Cloud上のSQLiteはデモ用途であり、再起動・再デプロイ時に初期化される可能性があります。一般公開時は認証とユーザー単位のデータ分離を備えた外部DBへ移行する前提です。
