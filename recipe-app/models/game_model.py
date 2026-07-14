from config.database import get_db_conn


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
