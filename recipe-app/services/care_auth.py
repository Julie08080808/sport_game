"""照護中心後台（/care）的登入 session。

跟 /admin 的單一帳號不同，這裡是「多個照護者帳號，各自屬於一個照護中心」，
帳密存在資料庫的 caregiver_accounts（見 models/care_model.py），不是 .env。

- CARE_SESSION_SECRET 放在 .env，用來簽 cookie（至少 32 字元）。
- 簽章金鑰額外混入該照護者目前的密碼雜湊：改密碼後，舊 session 立刻失效。
- 同一個來源連續打錯密碼會被暫時鎖住，邏輯跟 admin_auth 一樣。
"""
import base64
import hmac
import hashlib
import os
import time
from threading import Lock
from urllib.parse import quote

from fastapi import HTTPException, Request

from models import care_model

COOKIE_NAME = "care_session"
COOKIE_PATH = "/care"

MAX_FAILURES = 5
FAILURE_WINDOW = 10 * 60
LOCKOUT_SECONDS = 10 * 60

_failures: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}
_lock = Lock()


def _session_secret() -> str:
    return os.getenv("CARE_SESSION_SECRET", "").strip()


def session_hours() -> int:
    try:
        return max(1, int(os.getenv("CARE_SESSION_HOURS", "12")))
    except ValueError:
        return 12


def cookie_secure() -> bool:
    return os.getenv("ADMIN_COOKIE_SECURE", "false").strip().lower() == "true"


def missing_settings() -> list[str]:
    missing = []
    if len(_session_secret()) < 32:
        missing.append("CARE_SESSION_SECRET (至少 32 字元)")
    return missing


# ------------------------------------------------------------
# 暴力猜密碼保護（跟 admin_auth 同一套邏輯，各自獨立計數）
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
def _signing_key(password_hash: str) -> bytes:
    return hashlib.sha256((_session_secret() + "|" + password_hash).encode("utf-8")).digest()


def _sign(payload: str, password_hash: str) -> str:
    return hmac.new(_signing_key(password_hash), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session_cookie(caregiver: dict) -> str:
    expires = int(time.time()) + session_hours() * 3600
    payload = f"{caregiver['caregiver_id']}|{caregiver['care_center_id']}|{expires}"
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    # 這裡的雜湊是登入當下查到的，簽章用；驗證時會拿「當下」的雜湊重算一次比對。
    return f"{encoded}.{_sign(payload, caregiver['password_hash'])}"


def read_session_cookie(value: str | None):
    """cookie 有效、帳號啟用中，回傳照護者資料 dict；否則回傳 None。"""
    if not value or missing_settings():
        return None
    try:
        encoded, signature = value.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
        caregiver_id_str, center_id_str, expires_str = payload.split("|")
        caregiver_id = int(caregiver_id_str)
        if int(expires_str) < time.time():
            return None
    except (ValueError, TypeError, UnicodeDecodeError):
        return None

    caregiver = care_model.get_caregiver_for_session(caregiver_id)
    if not caregiver or not caregiver["is_active"] or str(caregiver["care_center_id"]) != center_id_str:
        return None

    if not hmac.compare_digest(_sign(payload, caregiver["password_hash"]), signature):
        return None

    return caregiver


def safe_next(path: str | None) -> str:
    if path and path.startswith("/care") and not path.startswith("/care/login") and "//" not in path and "\\" not in path:
        return path
    return "/care"


def require_caregiver(request: Request) -> dict:
    caregiver = read_session_cookie(request.cookies.get(COOKIE_NAME))
    if caregiver:
        request.state.caregiver = caregiver
        return caregiver

    target = "/care"
    if request.method == "GET":
        target = request.url.path
        if request.url.query:
            target += "?" + request.url.query
    raise HTTPException(
        status_code=303,
        detail="Login required",
        headers={"Location": f"/care/login?next={quote(safe_next(target), safe='')}"},
    )
