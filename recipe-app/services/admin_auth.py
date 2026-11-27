"""
管理後台登入。

- 帳號密碼放在 .env：ADMIN_USERNAME、ADMIN_PASSWORD_HASH（用 scripts/set_admin_password.py 產生，
  不存明文密碼）、ADMIN_SESSION_SECRET（簽 cookie 用的隨機字串）。
- 登入成功後發一個簽過名的 cookie（admin_session），只送往 /admin 路徑、JavaScript 讀不到。
- 改密碼或換 ADMIN_SESSION_SECRET，所有已登入的後台 session 會立刻失效。
- 同一個來源連續打錯密碼會被暫時鎖住，避免被暴力猜密碼。

只用 Python 標準函式庫，不需要額外安裝套件。
密碼雜湊格式：pbkdf2_sha256:<迭代次數>:<salt hex>:<hash hex>
（刻意不含 `$`，放進 .env / docker compose 不會被當成變數展開。）
"""
import base64
import hashlib
import hmac
import os
import secrets
import time
from threading import Lock

from fastapi import HTTPException, Request

from services.password_hashing import hash_password, verify_password

COOKIE_NAME = "admin_session"
COOKIE_PATH = "/admin"

# 連續失敗 MAX_FAILURES 次（在 FAILURE_WINDOW 秒內）就鎖 LOCKOUT_SECONDS 秒
MAX_FAILURES = 5
FAILURE_WINDOW = 10 * 60
LOCKOUT_SECONDS = 10 * 60

_failures: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}
_lock = Lock()


# ------------------------------------------------------------
# 設定
# ------------------------------------------------------------
def _username() -> str:
    return os.getenv("ADMIN_USERNAME", "").strip()


def _password_hash() -> str:
    return os.getenv("ADMIN_PASSWORD_HASH", "").strip()


def _session_secret() -> str:
    return os.getenv("ADMIN_SESSION_SECRET", "").strip()


def session_hours() -> int:
    try:
        return max(1, int(os.getenv("ADMIN_SESSION_HOURS", "12")))
    except ValueError:
        return 12


def cookie_secure() -> bool:
    # 伺服器改用 https 後設成 true，cookie 就只會在 https 下傳送。
    return os.getenv("ADMIN_COOKIE_SECURE", "false").strip().lower() == "true"


def missing_settings() -> list[str]:
    """回傳還沒設定的環境變數名稱；空清單代表後台登入可以用。"""
    missing = []
    if not _username():
        missing.append("ADMIN_USERNAME")
    if not _password_hash().startswith("pbkdf2_sha256:"):
        missing.append("ADMIN_PASSWORD_HASH")
    if len(_session_secret()) < 32:
        missing.append("ADMIN_SESSION_SECRET (至少 32 字元)")
    return missing


def check_credentials(username: str, password: str) -> bool:
    if missing_settings():
        return False
    # 帳號和密碼都要算完再判斷，不讓回應時間洩漏帳號對不對。
    user_ok = hmac.compare_digest(username.strip().encode("utf-8"), _username().encode("utf-8"))
    pass_ok = verify_password(password, _password_hash())
    return user_ok and pass_ok


# ------------------------------------------------------------
# 暴力猜密碼保護
# ------------------------------------------------------------
def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def seconds_locked(key: str) -> int:
    with _lock:
        until = _locked_until.get(key, 0)
        remaining = until - time.time()
        if remaining <= 0:
            _locked_until.pop(key, None)
            return 0
        return int(remaining) + 1


def record_failure(key: str) -> None:
    now = time.time()
    with _lock:
        recent = [t for t in _failures.get(key, []) if now - t < FAILURE_WINDOW]
        recent.append(now)
        if len(recent) >= MAX_FAILURES:
            _locked_until[key] = now + LOCKOUT_SECONDS
            recent = []
        _failures[key] = recent


def clear_failures(key: str) -> None:
    with _lock:
        _failures.pop(key, None)
        _locked_until.pop(key, None)


# ------------------------------------------------------------
# Session cookie
# ------------------------------------------------------------
def _signing_key() -> bytes:
    # 把密碼雜湊也放進簽章金鑰：改密碼後舊 cookie 全部失效。
    return hashlib.sha256(
        (_session_secret() + "|" + _password_hash()).encode("utf-8")
    ).digest()


def _sign(payload: str) -> str:
    return hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_cookie(username: str) -> str:
    expires = int(time.time()) + session_hours() * 3600
    payload = f"{username}|{expires}|{secrets.token_hex(8)}"
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    return f"{encoded}.{_sign(payload)}"


def read_session_cookie(value: str | None) -> str | None:
    """cookie 有效就回傳帳號名稱，否則回傳 None。"""
    if not value or missing_settings():
        return None
    try:
        encoded, signature = value.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None

    if not hmac.compare_digest(_sign(payload), signature):
        return None

    try:
        username, expires, _nonce = payload.split("|")
        if int(expires) < time.time():
            return None
    except ValueError:
        return None

    if username != _username():
        return None
    return username


def safe_next(path: str | None) -> str:
    """登入後只能跳回後台內的頁面，避免被當成跳轉到外部網站的跳板。"""
    if path and path.startswith("/admin") and not path.startswith("/admin/login") and "//" not in path and "\\" not in path:
        return path
    return "/admin"


# ------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------
def require_admin(request: Request) -> str:
    username = read_session_cookie(request.cookies.get(COOKIE_NAME))
    if username:
        request.state.admin_username = username
        return username

    from urllib.parse import quote

    # 送出表單時剛好過期的話，登入後回到後台首頁（POST 網址不能直接用 GET 開）。
    target = "/admin"
    if request.method == "GET":
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
    # 用 303 讓瀏覽器直接轉到登入頁
    raise HTTPException(
        status_code=303,
        detail="Login required",
        headers={"Location": f"/admin/login?next={quote(safe_next(target), safe='')}"},
    )
