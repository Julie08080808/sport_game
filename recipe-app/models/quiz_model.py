"""
問答遊戲資料模型 (Model)
負責問答題目資料的存取。

【設計考量】
- 題庫總數會隨時間增加,故所有 SQL 不寫死數量
- 抽題模式可選 random / sequential,方便未來擴充
- 支援依題型篩選(text 文字題 / image 圖片題),供 demo 展示使用
- 答案驗證在後端做(避免前端 JS 被改而作弊)
"""
from config.database import get_db_conn

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

    conn = get_db_conn()
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

    conn = get_db_conn()
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
    conn = get_db_conn()
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

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params) if params else None)
            return cur.fetchone()["total"]
    finally:
        conn.close()


# 對齊規格書獎勵比例:益智遊戲「經驗值少量、金幣中等」
EXP_PER_CORRECT = 10
COIN_PER_CORRECT = 20


def grant_quiz_reward(user_id: int, correct_count: int):
    """
    依答對題數發放獎勵到 user_stats(只動玩家整體數值,不碰任何建築/場景)。
    等級公式沿用其他遊戲功能:玩家每 1000 經驗升 1 級。
    """
    exp_gained = correct_count * EXP_PER_CORRECT
    coin_gained = correct_count * COIN_PER_CORRECT

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE user_stats SET
                player_exp = (player_exp + %s) %% 1000,
                player_level = player_level + floor((player_exp + %s) / 1000)::int,
                money = money + %s
                WHERE user_id = %s
                RETURNING player_level, player_exp, money;
            """, (exp_gained, exp_gained, coin_gained, user_id))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None

            conn.commit()
            return {
                "exp_gained": exp_gained,
                "coin_gained": coin_gained,
                "player_level": row["player_level"],
                "player_exp": row["player_exp"],
                "money": row["money"],
            }
    except Exception as e:
        conn.rollback()
        print(f"[Database Error] 問答獎勵發放失敗: {e}")
        return None
    finally:
        conn.close()
