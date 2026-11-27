"""共用密碼雜湊工具，/admin 的系統管理員帳號跟照護中心的照護者帳號都用這套。

格式：pbkdf2_sha256:<迭代次數>:<salt hex>:<hash hex>
（刻意不含 `$`，放進 .env / docker compose 不會被當成變數展開。）
"""
import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 600_000


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256:{iterations}:{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split(":")
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False
