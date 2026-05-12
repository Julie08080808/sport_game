"""
問答遊戲資料模型 (Model)
負責問答題目資料的存取。

【設計考量】
- 題庫總數會隨時間增加,故所有 SQL 不寫死數量
- 抽題模式可選 random / sequential,方便未來擴充
- 答案驗證在後端做(避免前端 JS 被改而作弊)
"""
from config.database import get_qa_db_conn


def fetch_random_questions(count: int = 5):
    """
    隨機抽出 N 題。
    若題庫不足 N 題,自動回傳所有題目。

    回傳給前端的格式不含 correct_answer 與 explanation
    (這兩個會在使用者答完後另外去拿,避免被 F12 偷看答案)。
    """
    sql = """
        SELECT id, question_no, question, option_a, option_b
        FROM quiz_questions
        ORDER BY RANDOM()
        LIMIT %s;
    """
    conn = get_qa_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (count,))
            return cur.fetchall()
    finally:
        conn.close()


def fetch_sequential_questions(count: int = 5, offset: int = 0):
    """
    順序取 N 題,從第 offset 題開始。
    給「按題號順序作答」模式使用,目前未啟用,先預留。
    """
    sql = """
        SELECT id, question_no, question, option_a, option_b
        FROM quiz_questions
        ORDER BY question_no
        LIMIT %s OFFSET %s;
    """
    conn = get_qa_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (count, offset))
            return cur.fetchall()
    finally:
        conn.close()


def check_answer(question_id: int, user_answer: str):
    """
    驗證使用者答案,並回傳正解與解釋。
    user_answer:'A' 或 'B'

    回傳:
        {
            "correct": True/False,
            "correct_answer": "A",
            "explanation": "..."
        }
    若題目不存在則回傳 None。
    """
    sql = """
        SELECT correct_answer, explanation
        FROM quiz_questions
        WHERE id = %s;
    """
    conn = get_qa_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (question_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "correct": user_answer.upper() == row["correct_answer"],
                "correct_answer": row["correct_answer"],
                "explanation": row["explanation"],
            }
    finally:
        conn.close()


def count_total_questions():
    """回傳題庫總題數,前端可用於顯示「目前共有 N 題」。"""
    sql = "SELECT COUNT(*) AS total FROM quiz_questions;"
    conn = get_qa_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()["total"]
    finally:
        conn.close()
