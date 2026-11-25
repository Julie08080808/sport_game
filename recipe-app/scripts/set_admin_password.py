"""
設定管理後台的帳號密碼。

用法（在 recipe-app 資料夾裡）：
    .venv\\Scripts\\python.exe scripts\\set_admin_password.py
伺服器（Docker）：
    docker compose exec api python scripts/set_admin_password.py --print-only

會問帳號和密碼（密碼輸入時不會顯示），然後把下面三行寫進 .env：
    ADMIN_USERNAME=...
    ADMIN_PASSWORD_HASH=pbkdf2_sha256:...   （只存雜湊，不存明文密碼）
    ADMIN_SESSION_SECRET=...                （第一次才產生，之後保留）

--print-only：不改 .env，只把這三行印出來，讓你自己貼到伺服器的 .env。
改完 .env 要重啟後端才會生效。
"""
import getpass
import os
import secrets
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from services.admin_auth import hash_password  # noqa: E402

ENV_PATH = os.path.join(BASE_DIR, ".env")
MIN_PASSWORD_LENGTH = 10


def read_env_lines():
    if not os.path.exists(ENV_PATH):
        return []
    with open(ENV_PATH, encoding="utf-8") as f:
        return f.read().splitlines()


def current_value(lines, key):
    for line in lines:
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return ""


def set_values(lines, values):
    remaining = dict(values)
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
        else:
            out.append(line)
    if remaining:
        if out and out[-1].strip():
            out.append("")
        out.append("# 管理後台登入（scripts/set_admin_password.py 產生）")
        for key, value in remaining.items():
            out.append(f"{key}={value}")
    return out


def main():
    print_only = "--print-only" in sys.argv
    lines = read_env_lines()

    default_user = current_value(lines, "ADMIN_USERNAME")
    prompt = f"管理員帳號 [{default_user}]: " if default_user else "管理員帳號: "
    username = input(prompt).strip() or default_user
    if not username or any(c in username for c in "|= \t"):
        sys.exit("帳號不能是空的，也不能有空白、| 或 =")

    password = getpass.getpass(f"新密碼（至少 {MIN_PASSWORD_LENGTH} 個字元）: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"密碼太短，至少要 {MIN_PASSWORD_LENGTH} 個字元")
    if password.lower() in {"password1234", "admin12345", "1234567890"} or password == username:
        sys.exit("這個密碼太容易被猜到，請換一個")
    if getpass.getpass("再輸入一次: ") != password:
        sys.exit("兩次輸入的密碼不一樣")

    secret = current_value(lines, "ADMIN_SESSION_SECRET")
    if len(secret) < 32:
        secret = secrets.token_hex(32)

    values = {
        "ADMIN_USERNAME": username,
        "ADMIN_PASSWORD_HASH": hash_password(password),
        "ADMIN_SESSION_SECRET": secret,
    }

    if print_only:
        print("\n把下面三行貼進 .env（已有的同名設定要取代掉），再重啟後端：\n")
        for key, value in values.items():
            print(f"{key}={value}")
        return

    with open(ENV_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(set_values(lines, values)) + "\n")
    print(f"已更新 {ENV_PATH}。重啟後端後到 /admin/login 登入。")
    print("（改密碼後，所有已登入的後台都會被登出。）")


if __name__ == "__main__":
    main()
