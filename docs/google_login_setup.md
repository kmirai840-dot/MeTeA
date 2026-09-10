# Googleログインの設定・確認手順

> 最新状況（2026-09-10）：Google認証・Neon保存・運営者機能を公開環境へ反映済み。本人ログイン、保存、公開サーバー再起動後の復元を確認。2人目の実アカウント検証は未実施。以下の過去の「公開未反映」記録から進捗があるため、[公開反映・受入確認](public_release_status.md)を現在の確認状況の正とする。

更新日：2026年9月10日

## 現在の状態

Google Cloudの「My First Project」（project-55a29075-e6e7-4f8d-a36）で、運営者によるポリシー同意・MeTeAの初期設定を完了。外部・テスト中を確認し、許可された本人アカウント1名をGoogle側テストユーザーに登録済み。
ウェブ用OAuthクライアント「MeTeA test users」を作成し、以下のローカル・公開用リダイレクトURIを登録済み。クライアントID・シークレットの実値は文書へ記載しない。

ダウンロードしたOAuth JSONのプロジェクトと2つのリダイレクトURIを照合し、Git管理対象外の`.streamlit/secrets.toml`へ反映済み。既存のCookie署名値を保持し、設定確認ツールで形式正常・許可メール1件を確認。実ログイン前のSQLiteバックアップと整合性も確認済み。
実Googleログインは成功し、ローカルのホーム画面を表示。招待アカウントが内部ID 2として登録され、既存ID 1を保持したこととDB整合性正常を確認。画面再読み込み、ログアウト後の再ログインでホームへ復帰し、同一の内部ID 2を維持することを確認。入力内容の再ログイン時復元、別ユーザー・公開環境の検証は未完了。公開環境のSecrets変更・GitHubへのpushは実施していない。

## 1. Google CloudでOAuthクライアントを作る

1. [Google Cloudの認証情報](https://console.cloud.google.com/apis/credentials)へ、自分のGoogleアカウントでログインする。
2. MeTeA用のプロジェクトを選ぶ。既存プロジェクトを使う場合は、他用途の設定を変更しない。
3. Google Auth Platform（またはOAuth同意画面）の設定を行う。アプリ名はMeTeA、サポート・連絡先メールは運営者のアドレスを指定する。組織内限定ではなく知人を招待する場合は外部ユーザー向けとし、最初はテスト用設定で進める。
4. Google側にテストユーザー指定欄がある場合は、利用するアカウントを登録する。これはMeTeA側の許可リストとは別の設定。
5. クライアントを作成し、種類は「ウェブ アプリケーション」を選ぶ。
6. 承認済みリダイレクトURIに以下を登録する。末尾のスラッシュを追加せず、使用するURLと完全一致させる。

```text
http://localhost:8501/oauth2callback
https://metea-job-support.streamlit.app/oauth2callback
```

7. 発行されたクライアントIDとシークレットをローカル設定へ保存する。チャット、GitHub、設計図へ貼らない。GoogleのクライアントJSONを保存した場合もGit管理対象外の場所に置く。

使用する権限は本人確認のopenid・profile・emailのみ。Gmail、Drive等の読み取り権限は追加しない。

## 2. ローカルへ設定する

対象は開発フォルダの`.streamlit/secrets.toml`。Git管理対象外で、許可メールとランダムなcookie_secretを設定済み。
既存の値を保ち、次の空欄だけを埋める。

```toml
[auth.google]
client_id = "Googleで発行したクライアントID"
client_secret = "Googleで発行したクライアントシークレット"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

設定例全体は`.streamlit/secrets.toml.example`を参照。exampleには実値を保存しない。

```powershell
.\.venv\Scripts\python.exe tools\check_google_login_config.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

設定確認ツールは秘密情報の値を表示せず、不足している設定だけを表示する。設定を変えたらアプリを再起動する。

既存の`.env`等にMETEA_AUTH_MODEがある場合はそちらが優先されるため、`google`であることを確認する。Googleモードでは共通パスワードだけで入れず、架空データも投入しない。

## 3. ローカルで確認する

- 招待したGoogleアカウントでログインできる。
- 初回ログインで新規の内部IDが発行される。既存ID 1のデータは自動的に引き継がれない。
- 基本情報または下書きを保存し、ログアウト後の再ログインで復元できる。
- 招待していないアカウントでは、アプリのデータ画面を利用できない。
- 2人目の許可メールを追加し、別ブラウザ・別Googleアカウントでデータが混ざらない。
- users.is_active=0のアカウントを拒否する。DBの確認や更新は対象を確認してから行い、既存データを無断で移管しない。

Googleへの遷移、本人確認、戻り先、Cookie復元は、モックを使った自動テストとは別に実ブラウザで確認する。

## 4. 公開環境へ反映する段階

現在は公開への反映前。コードの反映と、Streamlit管理画面のSecrets設定が両方必要になる。

- METEA_AUTH_MODEはgoogle、METEA_REQUIRE_AUTHはtrueにする。
- auth.redirect_uriを公開URLのoauth2callbackへ変更する。
- auth.googleの設定とaccess.allowed_emailsを追加する。
- 既存のOPENAI_API_KEY、GOOGLE_MAPS_API_KEY等を消さずに設定する。
- ローカルと公開でCookie署名用の秘密値を分け、32文字以上のランダム値を使用する。
- Google側の許可リダイレクトURIとの一致を確認する。

ローカルではNeonへの移行・接続切替を完了した。公開環境にもMETEA_DATABASE_BACKEND="postgresql"と[storage] postgres_urlの設定が必要。SQLiteをCommunity Cloudへ置いたままでは継続利用の永続性を保証できない。テストユーザーへの提供開始は、PostgreSQL等の外部永続DB、運営者の閲覧・出力、データ利用説明、公開環境での再起動・分離テストの完了後とする。

参考：[Streamlit st.login](https://docs.streamlit.io/develop/api-reference/user/st.login)、[Google OIDC](https://developers.google.com/identity/openid-connect/openid-connect)


## 2026年9月10日：保存・復元の確認

実Google利用者ID 2で基本情報の下書きを画面から保存し、画面再読み込みとアプリプロセス再起動後の復元を確認した。別プロセスによる2利用者の永続保存・分離・未コミット変更の破棄も自動テストで確認済み。この時点の検証対象はローカルSQLite。以降のPostgreSQL対応・検証結果は保存設計を参照。公開環境の検証は別途必要。
基本情報の下書きは「次へ」の送信で保存される。送信前のキー入力のみの内容は保存保証の対象ではない。詳細とAs-Is／To-Beは[保存・外部DB移行設計](storage_persistence_spec.md)を参照する。

実ブラウザのタブを閉じ、新しいタブで再アクセスした後も下書きを復元できた。ブラウザアプリ全体の終了は未確認。確認用の下書きのみ削除し、確認前の未入力状態に戻した。


## 運営者設定

`[access]`の`admin_emails`に運営者のGoogleメールを配列で設定する。同じメールを`allowed_emails`にも含める。未設定は全員拒否。ローカルのみ設定済みで、公開環境は未反映。ログイン後の設定画面から運営者画面へ進む。詳細は[運営者データ設計](operator_data_spec.md)を参照。


## 初回招待コード方式への変更

メール事前登録から、Googleログイン後の初回招待コード入力へ変更する。通常利用者の所有者チェックと運営者専用権限を維持する。As-Is/To-Beと確認範囲は[招待コード設計](invite_code_spec.md)を参照。
