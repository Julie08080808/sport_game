"""
登入 session 管理。

/api/assistant/chat 的規格要求 user_id 一律從登入 session 取，不能從請求參數拿
（否則就是 IDOR：把數字改掉就能看到別人的過敏原、慢性病）。
這裡只新增這一條路徑需要的最小機制：登入換一個 token，存進 user_sessions，
之後的請求帶 token 換回 user_id。
"""
import os
import secrets
from datetime import datetime, timedelta, timezone

from config.database import get_db_conn

SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_sessions (token, user_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (token, user_id, expires_at),
            )
        conn.commit()
    finally:
        conn.close()

    return token


def get_user_id_from_token(token: str):
    if not token:
        return None

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id FROM user_sessions
                WHERE token = %s
                  AND revoked_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                """,
                (token,),
            )
            row = cur.fetchone()
            return row["user_id"] if row else None
    finally:
        conn.close()


def revoke_session(token: str) -> None:
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE user_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE token = %s",
                (token,),
            )
        conn.commit()
    finally:
        conn.close()
