"""
使用者資料模型 (Model)
負責使用者的註冊、登入帳密比對。
依架構圖規範:簡易帳密比對,不需 JWT、不需 Email。
"""
from config.database import get_db_conn
import psycopg2


def verify_user(username: str, password: str):
    """
    驗證帳號密碼是否正確。
    回傳使用者資料 (dict) 或 None。
    """
    sql = "SELECT id, username FROM users WHERE username = %s AND password = %s;"
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (username, password))
            return cur.fetchone()
    finally:
        conn.close()


def create_user(username: str, password: str):
    """
    建立新使用者。
    若帳號重複則回傳 None。
    """
    sql = """
        INSERT INTO users (username, password)
        VALUES (%s, %s)
        RETURNING id, username;
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (username, password))
            new_user = cur.fetchone()
            conn.commit()
            return new_user
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return None
    finally:
        conn.close()
