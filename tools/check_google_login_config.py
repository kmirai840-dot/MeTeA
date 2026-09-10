"""秘密値を出力せずローカルのGoogleログイン設定を検査する。"""
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.google_auth_service import validate_login_settings, LoginConfigurationError


def main() -> int:
    path = ROOT / ".streamlit" / "secrets.toml"
    if not path.exists():
        print(".streamlit/secrets.tomlがありません。docs/google_login_setup.mdを参照してください。")
        return 1
    try:
        settings = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError:
        print("設定ファイルのTOML構文を確認してください。")
        return 1
    auth = settings.get("auth", {})
    google = auth.get("google", {}) if isinstance(auth, dict) else {}
    if not isinstance(google, dict):
        print("auth.googleの設定形式を確認してください。")
        return 1
    missing = [key for key in ("client_id", "client_secret") if not google.get(key)]
    if missing:
        print("未設定: auth.google." + ", auth.google.".join(missing))
        return 1
    try:
        emails = validate_login_settings(settings)
    except LoginConfigurationError as error:
        print(str(error))
        return 1
    print("設定形式は正常です。招待コード方式。Googleへの実ログインは別途確認してください。" if emails is None else f"設定形式は正常です。許可メール {len(emails)} 件。Googleへの実ログインは別途確認してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
