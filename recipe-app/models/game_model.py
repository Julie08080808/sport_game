from config.database import get_db_conn
from psycopg2.extras import RealDictCursor


# Unity 的 JsonUtility 沒辦法把 JSON null 安全地讀進 C# 的 int 欄位，
# 所以 API 對外一律用 -1 代表「沒有手動覆寫」，NULL 只留在資料庫內部。
NO_DISPLAY_OVERRIDE = -1


def _cap_to_client(display_level_cap):
    return NO_DISPLAY_OVERRIDE if display_level_cap is None else display_level_cap


def get_all_scene_status(user_id: int):
    """
    回傳玩家目前所有場景的等級/完成次數/外觀顯示覆寫，給 Unity 進 MainMap 時同步用。

    會先自動幫這個玩家補齊「scenes 表裡有、但 user_scenes 還沒有」的場景(預設 level 1)，
    這樣以後新增場景/建築(例如寺廟)時，舊帳號不用手動補資料，下次進 MainMap 呼叫這支 API
    就會自動生出新場景的初始紀錄——Unity 那邊完全不用改，因為它本來就是照這支 API 回傳
    幾筆就同步幾棟建築，不是寫死 5 個。
    """
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO user_scenes (user_id, scene_id, scene_level, scene_exp)
                SELECT %s, s.scene_id, 1, 0
                FROM scenes s
                WHERE s.is_active = TRUE
                  AND NOT EXISTS (
                      SELECT 1 FROM user_scenes us
                      WHERE us.user_id = %s AND us.scene_id = s.scene_id
                  );
                """,
                (user_id, user_id),
            )

            cur.execute(
                """
                SELECT scene_id, scene_level, scene_exp, completion_count, display_level_cap
                FROM user_scenes
                WHERE user_id = %s
                ORDER BY scene_id;
                """,
                (user_id,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                r["display_level_cap"] = _cap_to_client(r["display_level_cap"])

            conn.commit()
            return rows
    except Exception as e:
        conn.rollback()
        print(f"[Database Error] 取得場景狀態失敗: {e}")
        return []
    finally:
        conn.close()


def set_scene_display_level(user_id: int, scene_id: int, display_level: int):
    """
    玩家手動把某個場景的建築外觀調到指定等級(display_level <= 該場景目前的 scene_level)。
    display_level 傳 -1 代表清除覆寫，改回自動顯示最新已解鎖階段。
    五個場景各自獨立設定，不會互相影響。
    """
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT scene_level FROM user_scenes WHERE user_id = %s AND scene_id = %s;",
                (user_id, scene_id),
            )
            row = cur.fetchone()
            if not row:
                return {"success": False, "message": "找不到這個場景的玩家資料"}

            if display_level == -1:
                cap = None
            elif 0 <= display_level <= row["scene_level"]:
                cap = display_level
            else:
                return {
                    "success": False,
                    "message": f"display_level 必須介於 0 到 {row['scene_level']}(目前場景等級)之間，或傳 -1 清除覆寫",
                }

            cur.execute(
                """
                UPDATE user_scenes
                SET display_level_cap = %s
                WHERE user_id = %s AND scene_id = %s
                RETURNING scene_level, display_level_cap;
                """,
                (cap, user_id, scene_id),
            )
            result = cur.fetchone()
            conn.commit()

            return {
                "success": True,
                "scene_id": scene_id,
                "scene_level": result["scene_level"],
                "display_level_cap": _cap_to_client(result["display_level_cap"]),
            }
    except Exception as e:
        conn.rollback()
        print(f"[Database Error] 設定場景外觀失敗: {e}")
        return {"success": False, "message": f"設定失敗: {e}"}
    finally:
        conn.close()


def process_task_completion(user_id: int, building_type: int, exp_gained: int):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            # 1. 更新玩家數據 (player_level, player_exp, money)
            # 假設玩家等級公式：每 1000 經驗升一級
            sql_user = """
                UPDATE user_stats 
                SET player_exp = player_exp + %s,
                    money = money + (%s / 10), -- 獎勵金幣為經驗的 1/10
                    player_level = player_level + floor((player_exp + %s) / 1000)::int,
                    player_exp = (player_exp + %s) % 1000
                WHERE user_id = %s
                RETURNING player_level, player_exp, money;
            """
            cur.execute(sql_user, (exp_gained, exp_gained,
                        exp_gained, exp_gained, user_id))
            user_data = cur.fetchone()

            # 2. 更新建築數據 (level, current_exp)
            # 假設建築等級公式：每 500 經驗升一級
            sql_building = """
                UPDATE building_stats 
                SET current_exp = current_exp + %s,
                    level = level + floor((current_exp + %s) / 500)::int,
                    current_exp = (current_exp + %s) % 500
                WHERE user_id = %s AND building_type = %s
                RETURNING level, current_exp;
            """
            cur.execute(sql_building, (exp_gained, exp_gained,
                        exp_gained, user_id, building_type))
            building_data = cur.fetchone()

            # 3. 寫入運動日誌 (exercise_logs)
            sql_log = """
                INSERT INTO exercise_logs (user_id, building_type, exp_gained, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP);
            """
            cur.execute(sql_log, (user_id, building_type, exp_gained))

            conn.commit()
            return {
                "user": user_data,
                "building": building_data
            }
    except Exception as e:
        conn.rollback()
        print(f"Database Error: {e}")
        return None
    finally:
        conn.close()
