"""
資料庫連線設定
透過 python-dotenv 從 .env 讀取連線資訊,避免將密碼硬編碼在程式中。
此檔案不使用 SQLAlchemy,直接使用 psycopg2 連線 PostgreSQL。

【支援雙資料庫】
- 食譜資料庫(預設):透過 get_db_conn() 連接
- 問答資料庫:透過 get_qa_db_conn() 連接
兩者共用同一組帳密、host、port,只有 DB_NAME 不同。
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()


def _build_config(db_name_env_key: str, default_db_name: str) -> dict:
    """共用的設定組裝邏輯,只有 DB 名稱會變。"""
    return {
        "dbname": os.getenv(db_name_env_key, default_db_name),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
    }


# 食譜資料庫設定(沿用原本的 DB_NAME 環境變數,確保向後相容)
RECIPE_DB_CONFIG = _build_config("DB_NAME", "test_rec_0404")

# 問答遊戲資料庫設定
QA_DB_CONFIG = _build_config("DB_NAME_QA", "test_QA_0421")


def get_db_conn():
    """
    建立並回傳食譜資料庫連線(預設行為,沿用舊的呼叫方式)。
    使用 RealDictCursor 讓查詢結果以 dict 形式回傳,方便轉成 JSON。
    """
    return psycopg2.connect(**RECIPE_DB_CONFIG, cursor_factory=RealDictCursor)


def get_qa_db_conn():
    """建立並回傳問答資料庫連線。"""
    return psycopg2.connect(**QA_DB_CONFIG, cursor_factory=RealDictCursor)
