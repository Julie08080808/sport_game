"""
資料庫連線設定
透過 python-dotenv 從 .env 讀取連線資訊,避免將密碼硬編碼在程式中。
此檔案不使用 SQLAlchemy,直接使用 psycopg2 連線 PostgreSQL。
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 從環境變數讀取連線參數(若未設定則使用預設值)
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "123456"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}


def get_db_conn():
    """
    建立並回傳一個資料庫連線。
    使用 RealDictCursor 讓查詢結果以 dict 形式回傳,方便轉成 JSON。
    """
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
# 在 load_dotenv() 之後加上這行
print(f"DEBUG: 正在嘗試連線到資料庫：{os.getenv('DB_NAME')}")