"""
使用者資料模型 (Model) - 遊戲數據初始化版
"""

import bcrypt
import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor

from config.database import get_db_conn


def verify_user(username: str, password: str):
    sql = """
        SELECT user_id, username, password_hash
        FROM users
        WHERE username = %s;
    """
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (username,))
            row = cur.fetchone()

            if not row:
                return None

            password_bytes = password.encode("utf-8")
            hash_bytes = (
                row["password_hash"].encode("utf-8")
                if isinstance(row["password_hash"], str)
                else row["password_hash"]
            )

            if bcrypt.checkpw(password_bytes, hash_bytes):
                return {
                    "user_id": row["user_id"],
                    "username": row["username"]
                }

            return None
    finally:
        conn.close()


def _initialize_user_scenes(cur, user_id: int):
    cur.execute("""
        SELECT scene_id
        FROM scenes
        WHERE is_active = TRUE
        ORDER BY scene_id;
    """)
    scenes = cur.fetchall()

    for scene in scenes:
        cur.execute("""
            INSERT INTO user_scenes (
                user_id,
                scene_id,
                scene_level,
                scene_exp
            )
            VALUES (%s, %s, 1, 0)
            ON CONFLICT (user_id, scene_id) DO NOTHING;
        """, (user_id, scene["scene_id"]))


def _unlock_initial_tasks(cur, user_id: int, player_level: int = 1) -> int:
    cur.execute("""
        INSERT INTO user_task_unlocks (
            user_id,
            task_id,
            unlock_reason,
            unlocked_at
        )
        SELECT
            %s,
            t.task_id,
            'initial',
            CURRENT_TIMESTAMP
        FROM tasks t
        WHERE t.is_active = TRUE
          AND t.is_initial_unlock = TRUE
          AND COALESCE(t.required_player_level, 1) <= %s
        ON CONFLICT (user_id, task_id) DO NOTHING
        RETURNING task_id;
    """, (user_id, player_level))

    return len(cur.fetchall())


def create_user_with_stats(username, password):
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(
        password_bytes,
        salt
    ).decode("utf-8")

    conn = get_db_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO users (
                    username,
                    password_hash
                )
                VALUES (%s, %s)
                RETURNING user_id;
            """, (username, hashed_password))

            user_id = cur.fetchone()["user_id"]
            initial_player_level = 1

            cur.execute("""
                INSERT INTO user_stats (
                    user_id,
                    player_level,
                    player_exp,
                    money
                )
                VALUES (%s, %s, 0, 0);
            """, (user_id, initial_player_level))

            _initialize_user_scenes(cur, user_id)

            unlocked_task_count = _unlock_initial_tasks(
                cur,
                user_id,
                initial_player_level
            )

            conn.commit()

            print(
                f"[註冊初始化成功] user_id={user_id}, "
                f"initial_tasks={unlocked_task_count}"
            )

            return {
                "user_id": user_id,
                "username": username,
                "initial_unlocked_task_count": unlocked_task_count
            }

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
    conn = get_db_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE user_scenes
                SET
                    scene_exp = (scene_exp + %s) %% 500,
                    scene_level =
                        scene_level
                        + floor((scene_exp + %s) / 500)::int
                WHERE user_id = %s
                  AND scene_id = %s
                RETURNING scene_level, scene_exp;
            """, (
                exp_gained,
                exp_gained,
                user_id,
                b_type
            ))

            b_res = cur.fetchone()

            if not b_res:
                conn.rollback()
                return {
                    "success": False,
                    "message": "找不到玩家對應的景點資料"
                }

            cur.execute("""
                UPDATE user_stats
                SET
                    player_exp = (player_exp + %s) %% 1000,
                    player_level =
                        player_level
                        + floor((player_exp + %s) / 1000)::int,
                    money = money + 10
                WHERE user_id = %s
                RETURNING player_level, player_exp, money;
            """, (
                exp_gained,
                exp_gained,
                user_id
            ))

            u_res = cur.fetchone()

            if not u_res:
                conn.rollback()
                return {
                    "success": False,
                    "message": "找不到玩家狀態資料"
                }

            conn.commit()

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
        return {
            "success": False,
            "message": str(e)
        }

    finally:
        conn.close()
