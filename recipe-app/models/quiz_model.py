"""
問答遊戲資料模型 (Model)
負責問答題目資料的存取。

【設計考量】
- 題庫總數會隨時間增加,故所有 SQL 不寫死數量
- 抽題模式可選 random / sequential,方便未來擴充
- 支援依題型篩選(text 文字題 / image 圖片題),供 demo 展示使用
- 答案驗證在後端做(避免前端 JS 被改而作弊)
"""
from config.database import get_qa_db_conn

# 對外開放的題型,controller 會先驗證過再傳進來
VALID_TYPES = ("text", "image")


def _type_filter(question_type):
    """
    依題型組出 WHERE 子句與參數。
    question_type 為 None 或 'all' 時不篩選,回傳空字串。
    使用參數化查詢,不會有 SQL Injection 風險。
    """
    if question_type and question_type in VALID_TYPES:
        return " WHERE question_type = %s", [question_type]
    return "", []


def fetch_random_questions(count: int = 5, question_type: str = None):
    """
    隨機抽出 N 題。
    若題庫不足 N 題,自動回傳所有符合條件的題目。

    question_type:
        None 或 'all' → 文字題與圖片題混合隨機(正式使用)
        'text'        → 只出文字題
        'image'       → 只出圖片題(demo 展示用)

    回傳欄位不含 correct_answer 與 explanation
    (這兩個會在使用者答完後另外去拿,避免被 F12 偷看答案)。
    """
    where_sql, params = _type_filter(question_type)

    sql = f"""
        SELECT id, question_no, question, option_a, option_b,
               image_url, question_type
        FROM quiz_questions
        {where_sql}
        ORDER BY RANDOM()
        LIMIT %s;
    """
    params.append(count)

    conn = get_qa_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()
    finally:
        conn.close()


def fetch_sequential_questions(count: int = 5, offset: int = 0, question_type: str = None):
    """
    順序取 N 題,從第 offset 題開始。
    給「按題號順序作答」模式使用,目前未啟用,先預留。
    """
    where_sql, params = _type_filter(question_type)

    sql = f"""
        SELECT id, question_no, question, option_a, option_b,
               image_url, question_type
        FROM quiz_questions
        {where_sql}
        ORDER BY question_no
        LIMIT %s OFFSET %s;
    """
    params.extend([count, offset])

    conn = get_qa_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
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


def count_total_questions(question_type: str = None):
    """
    回傳題庫總題數,前端可用於顯示「目前共有 N 題」。
    可依題型篩選。
    """
    where_sql, params = _type_filter(question_type)

    sql = f"SELECT COUNT(*) AS total FROM quiz_questions {where_sql};"

    conn = get_qa_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            return cur.fetchone()["total"]
    finally:
        conn.close()
