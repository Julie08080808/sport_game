"""
NPC 對話與任務模型 (Model)
負責從候選對話中排除已失效的一次性事件，並隨機抽選一筆回傳。
"""
import random
from config.database import get_db_conn
from psycopg2.extras import RealDictCursor


def get_random_dialogue(user_id: int, npc_id: str):
    """
    回傳指定 NPC 的一筆隨機對話/任務。
    排除規則：非重複型 (is_repeatable = FALSE) 且玩家已完成/放棄過的，不再列入候選。
    """
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT d.* FROM npc_dialogues d
                WHERE d.npc_id = %s
                AND (
                    d.is_repeatable = TRUE
                    OR NOT EXISTS (
                        SELECT 1 FROM user_task_history h
                        WHERE h.user_id = %s AND h.dialogue_id = d.dialogue_id
                        AND h.status IN ('completed', 'abandoned', 'rewarded')
                    )
                );
            """, (npc_id, user_id))
            candidates = cur.fetchall()
            if not candidates:
                return None
            return random.choice(candidates)
    finally:
        conn.close()


def record_task_response(user_id: int, dialogue_id: int, status: str):
    """
    記錄玩家對某筆對話/任務的處理結果 (accepted / abandoned)。
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_task_history (user_id, dialogue_id, status)
                VALUES (%s, %s, %s);
            """, (user_id, dialogue_id, status))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"[Database Error] 任務歷史寫入失敗: {e}")
        return False
    finally:
        conn.close()
