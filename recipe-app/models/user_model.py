"""
使用者資料模型 (Model) - 遊戲數據初始化版
負責使用者註冊、登入帳密比對，以及自動建立初始經驗、等級與建築場景資料。
"""
import bcrypt
from config.database import get_db_conn
from psycopg2.extras import RealDictCursor
import psycopg2
import psycopg2.errors


def verify_user(username: str, password: str):
    """
    驗證帳號密碼是否正確。
    """
    sql = "SELECT user_id, username, password_hash FROM users WHERE username = %s;"
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (username,))
            row = cur.fetchone()

            if not row:
                return None

            password_bytes = password.encode('utf-8')
            hash_bytes = row['password_hash'].encode(
                'utf-8') if isinstance(row['password_hash'], str) else row['password_hash']

            if bcrypt.checkpw(password_bytes, hash_bytes):
                return {"user_id": row['user_id'], "username": row['username']}

            return None
    finally:
        conn.close()


def create_user_with_stats(username, password):
    """
    建立新使用者，並同步初始化經驗值與建築數據。
    【對齊規格書】：等級 1、初始金幣為 0、動態綁定 user_scenes 的 5 個景點。
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. 寫入玩家帳號表
            sql_user = "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING user_id;"
            cur.execute(sql_user, (username, hashed_password))
            user_id = cur.fetchone()['user_id']

            # 2. 初始化玩家數據表 (user_stats) -> 等級 1, 經驗 0, 金幣為 0
            sql_stats = """
                INSERT INTO user_stats (user_id, player_level, player_exp, money) 
                VALUES (%s, 1, 0, 0);
            """
            cur.execute(sql_stats, (user_id,))

            # 3. 💡 精準對齊規格書：將資料表改為 user_scenes，欄位改為 scene_id, scene_level, scene_exp
            try:
                cur.execute("SELECT scene_id FROM scenes;")
                scenes = cur.fetchall()
            except Exception:
                scenes = None

            if scenes:
                for row in scenes:
                    sql_building = """
                        INSERT INTO user_scenes (user_id, scene_id, scene_level, scene_exp)
                        VALUES (%s, %s, 1, 0);
                    """
                    cur.execute(sql_building, (user_id, row['scene_id']))
            else:
                # 🔥 【強效防呆】若 scenes 基礎資料表為空，自動初始化 1~5 號場景景點
                for s_id in range(1, 6):
                    sql_building = """
                        INSERT INTO user_scenes (user_id, scene_id, scene_level, scene_exp)
                        VALUES (%s, %s, 1, 0);
                    """
                    cur.execute(sql_building, (user_id, s_id))

            conn.commit()
            return {"user_id": user_id, "username": username}

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return None
    except Exception as e:
        conn.rollback()
        print(f"[Database Error] 註冊初始化失敗: {e}")
        return None
    finally:
        conn.close()


def update_game_exp(user_id, b_type, exp_gained):
    """
    更新景點與玩家經驗值，並同步回傳給前端。
    """
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 💡 精準對齊規格書：更新 user_scenes 表中的 scene_exp 與 scene_level
            cur.execute("""
                UPDATE user_scenes SET 
                scene_exp = (scene_exp + %s) %% 500,
                scene_level = scene_level + floor((scene_exp + %s) / 500)::int
                WHERE user_id = %s AND scene_id = %s RETURNING scene_level, scene_exp;
            """, (exp_gained, exp_gained, user_id, b_type))
            b_res = cur.fetchone()

            # 更新玩家經驗 & 增加金錢 (user_stats)
            cur.execute("""
                UPDATE user_stats SET 
                player_exp = (player_exp + %s) %% 1000,
                player_level = player_level + floor((player_exp + %s) / 1000)::int,
                money = money + 10
                WHERE user_id = %s RETURNING player_level, player_exp, money;
            """, (exp_gained, exp_gained, user_id))
            u_res = cur.fetchone()

            conn.commit()

            # 打包成符合 Unity 前端 GameDataSchema 解析的 JSON 格式
            return {
                "success": True,
                "player": {
                    "player_level": u_res["player_level"],
                    "player_exp": u_res["player_exp"],
                    "money": u_res["money"],
                    "expToNextLevel": 1000
                },
                "building": {
                    "level": b_res["scene_level"],
                    "currentExp": b_res["scene_exp"]
                }
            }
    except Exception as e:
        conn.rollback()
        print(f"經驗值同步錯誤: {e}")
        return {"success": False, "message": str(e)}
    finally:
        conn.close()
