"""
資料庫連線設定
透過 python-dotenv 從 .env 讀取連線資訊,避免將密碼硬編碼在程式中。
"""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Installed path: project/config/database.py -> project/.env.
load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)


def get_db_conn():
    """Return a dictionary-row connection with explicit transaction control."""
    password = os.getenv('DB_PASSWORD')
    if not password:
        raise RuntimeError('請設定 DB_PASSWORD 環境變數')
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'sport'),
        user=os.getenv('DB_USER', 'postgres'),
        password=password,
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        connect_timeout=int(os.getenv('DB_CONNECT_TIMEOUT', '10')),
        cursor_factory=RealDictCursor,
    )
    conn.autocommit = False
    return conn


@contextmanager
def db_transaction():
    """One business operation owns one connection and one commit/rollback."""
    conn = get_db_conn()
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
