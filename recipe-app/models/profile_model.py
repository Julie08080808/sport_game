"""
個人檔案資料模型 (Model)
對應 Unity SilverHealth 模組的 IDataService。

重用既有表：user_profiles（name/height/weight/birthday）、
health_conditions + user_health_conditions（後者是「有一列＝有這個狀況」，
沒有 has_condition 布林欄位，覆蓋寫入用刪除重建）。
outfits / achievements / user_settings 是這次新增的表（見 schema_profile.sql）。
等級/經驗一律唯讀鏡射 user_stats，不在這裡寫入（寫入入口仍是 user_model.update_game_exp）。
"""

from config.database import db_transaction
from services.exercise_rules import RuleError


def _require_row(row, message):
    if not row:
        raise RuleError(message)
    return row


# ───────────── 基本資料 ─────────────

def get_profile(user_id: int) -> dict:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.user_id, p.name AS game_name, p.real_name, p.gender,
                       p.height AS height_cm, p.weight AS weight_kg, p.birthday AS birthdate,
                       p.avatar_url, p.equipped_outfit_id,
                       COALESCE(p.is_on_medication, FALSE) AS is_on_medication,
                       COALESCE(p.diet_type, 'None') AS diet_type,
                       COALESCE(acc.is_mobility_limited, FALSE) AS is_mobility_limited,
                       u.username AS account,
                       s.player_level AS level, s.player_exp AS exp
                FROM users u
                LEFT JOIN user_profiles p ON p.user_id = u.user_id
                LEFT JOIN user_stats s ON s.user_id = u.user_id
                LEFT JOIN user_accessibility_profiles acc ON acc.user_id = u.user_id
                WHERE u.user_id = %s;
            """, (user_id,))
            row = _require_row(cur.fetchone(), "找不到使用者資料")
            result = dict(row)
            if result["birthdate"] is not None:
                result["birthdate"] = result["birthdate"].isoformat()
            return result


def _outfit_unlocked(cur, user_id: int, outfit_id: int) -> bool:
    cur.execute("""
        SELECT (is_default OR EXISTS (
            SELECT 1 FROM user_outfits
            WHERE user_id = %s AND outfit_id = %s AND unlocked = TRUE
        )) AS allowed
        FROM outfits WHERE outfit_id = %s;
    """, (user_id, outfit_id, outfit_id))
    row = cur.fetchone()
    return bool(row and row["allowed"])


def save_profile(user_id: int, game_name: str, real_name: str, gender: str,
                  height_cm: int, weight_kg: int, birthdate: str,
                  equipped_outfit_id=None, is_on_medication=None, diet_type=None,
                  is_mobility_limited=None) -> dict:
    # is_on_medication / diet_type / is_mobility_limited 是給阿明用的欄位。
    # 傳 None 代表「這次沒送」→ 保留原值，舊版 Unity 整包存檔時不會把它們洗掉。
    # is_mobility_limited 存在 user_accessibility_profiles（阿明推薦遊戲時用它篩掉要站起來的運動）。
    # Unity 端的 SaveUserProfile 每次都送完整的 UserProfile（含 equipped_outfit_id），
    # OutfitPanel 換裝也是走這條路（複製目前 Profile、改 equipped_outfit_id、整包存檔），
    # 不是走單獨的「換裝」端點，所以這裡要順便驗證解鎖狀態。
    with db_transaction() as conn:
        with conn.cursor() as cur:
            if equipped_outfit_id is not None and not _outfit_unlocked(cur, user_id, equipped_outfit_id):
                raise RuleError("這套服裝尚未解鎖")
            cur.execute("""
                INSERT INTO user_profiles (user_id, name, real_name, gender, height, weight, birthday,
                                           equipped_outfit_id, is_on_medication, diet_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, FALSE), COALESCE(%s, 'None'))
                ON CONFLICT (user_id) DO UPDATE SET
                    is_on_medication = COALESCE(%s, user_profiles.is_on_medication),
                    diet_type = COALESCE(%s, user_profiles.diet_type),
                    name = EXCLUDED.name,
                    real_name = EXCLUDED.real_name,
                    gender = EXCLUDED.gender,
                    height = EXCLUDED.height,
                    weight = EXCLUDED.weight,
                    birthday = EXCLUDED.birthday,
                    equipped_outfit_id = COALESCE(EXCLUDED.equipped_outfit_id, user_profiles.equipped_outfit_id),
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, game_name, real_name, gender, height_cm, weight_kg, birthdate, equipped_outfit_id,
                  is_on_medication, diet_type, is_on_medication, diet_type))
            if is_mobility_limited is not None:
                cur.execute("""
                    INSERT INTO user_accessibility_profiles (user_id, is_mobility_limited)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        is_mobility_limited = EXCLUDED.is_mobility_limited,
                        updated_at = CURRENT_TIMESTAMP;
                """, (user_id, is_mobility_limited))
    return get_profile(user_id)


def save_avatar_url(user_id: int, avatar_url: str) -> dict:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_profiles (user_id, avatar_url)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    avatar_url = EXCLUDED.avatar_url,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, avatar_url))
    return get_profile(user_id)


# ───────────── 健康狀況 ─────────────

def get_health_condition_catalog() -> list:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT condition_id AS id, condition_name AS name, condition_id AS sort_order, is_active
                FROM health_conditions
                WHERE is_active = TRUE
                ORDER BY condition_id;
            """)
            return cur.fetchall()


def get_user_health_conditions(user_id: int) -> list:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, condition_id, TRUE AS has_condition, created_at AS updated_at
                FROM user_health_conditions
                WHERE user_id = %s;
            """, (user_id,))
            rows = cur.fetchall()
            for r in rows:
                if r["updated_at"] is not None:
                    r["updated_at"] = r["updated_at"].isoformat()
            return rows


def save_user_health_conditions(user_id: int, condition_ids_with_flag: list) -> list:
    """condition_ids_with_flag: [{"condition_id": int, "has_condition": bool}, ...]
    覆蓋寫入：先清空，再只插入 has_condition=True 的項目（presence-based，無歷史記錄）。"""
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_health_conditions WHERE user_id = %s;", (user_id,))
            for item in condition_ids_with_flag:
                if item.get("has_condition"):
                    cur.execute("""
                        INSERT INTO user_health_conditions (user_id, condition_id)
                        VALUES (%s, %s);
                    """, (user_id, item["condition_id"]))
    return get_user_health_conditions(user_id)


# ───────────── 食物過敏原 ─────────────
# 必須跟 ingredients.allergen_group 同一套詞彙（AI助手後端說明.pdf p.4），
# 讓長輩自己打字的話 recipe_filter 會靜靜地篩錯。資料庫也有同一份 CHECK
# （user_allergies_food_vocab_check），這裡先擋是為了回清楚的錯誤訊息。
FOOD_ALLERGEN_CATEGORIES = ['海鮮', '乳製品', '蛋類', '麩質', '大豆', '堅果', '花生', '芝麻', '芒果']


def get_allergen_catalog() -> list:
    return [{"name": n, "sort_order": i + 1} for i, n in enumerate(FOOD_ALLERGEN_CATEGORIES)]


def get_user_allergies(user_id: int) -> list:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT allergen_name AS name, severity
                FROM user_allergies
                WHERE user_id = %s AND allergen_type = 'food'
                ORDER BY allergen_name;
            """, (user_id,))
            return cur.fetchall()


def save_user_allergies(user_id: int, names: list) -> list:
    """覆蓋寫入使用者的食物過敏原（只動 allergen_type='food'，藥物/環境過敏不碰）。"""
    unknown = [n for n in names if n not in FOOD_ALLERGEN_CATEGORIES]
    if unknown:
        raise ValueError("不支援的過敏原類別：" + "、".join(unknown)
                         + "（只能選：" + "、".join(FOOD_ALLERGEN_CATEGORIES) + "）")
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_allergies WHERE user_id = %s AND allergen_type = 'food';", (user_id,))
            for name in dict.fromkeys(names):  # 去重、保留順序
                cur.execute("""
                    INSERT INTO user_allergies (user_id, allergen_name, allergen_type)
                    VALUES (%s, %s, 'food');
                """, (user_id, name))
    return get_user_allergies(user_id)


# ───────────── 換裝 ─────────────

def get_outfits(user_id: int) -> list:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.outfit_id AS id, o.name, o.is_default,
                       (o.is_default OR COALESCE(uo.unlocked, FALSE)) AS unlocked
                FROM outfits o
                LEFT JOIN user_outfits uo ON uo.outfit_id = o.outfit_id AND uo.user_id = %s
                ORDER BY o.sort_order, o.outfit_id;
            """, (user_id,))
            return cur.fetchall()


# ───────────── 成就 ─────────────

# condition_key -> 判斷函式；函式收 (cur, user_id, stats) 回傳 bool。
# stats 是 _exercise_streak_stats() 算好的 {"total_days": int, "max_streak": int}，
# 同一次評估共用一次查詢結果，不要在每個判斷式裡各自查一次 exercise_logs。
def _has_diet_variety_5(cur, user_id, stats):
    cur.execute("""
        SELECT 1 FROM user_weekly_diet_reviews
        WHERE user_id = %s AND variety_score = 5 LIMIT 1;
    """, (user_id,))
    return cur.fetchone() is not None


_ACHIEVEMENT_CONDITIONS = {
    "first_login": lambda cur, user_id, stats: True,
    "first_exercise": lambda cur, user_id, stats: stats["total_days"] >= 1,
    "streak_3": lambda cur, user_id, stats: stats["max_streak"] >= 3,
    "streak_7": lambda cur, user_id, stats: stats["max_streak"] >= 7,
    "total_days_28": lambda cur, user_id, stats: stats["total_days"] >= 28,
    "diet_variety_5": _has_diet_variety_5,
}


def _exercise_streak_stats(cur, user_id: int) -> dict:
    """累積完成天數、歷史最長連續完成天數。用 gaps-and-islands：同一段連續日期
    減掉各自的列號會得到相同的分組鍵，再取各組的天數取最大值。"""
    cur.execute("""
        WITH days AS (
            SELECT DISTINCT started_at::date AS d
            FROM exercise_logs
            WHERE user_id = %s AND result = 'completed'
        ),
        grp AS (
            SELECT d, d - (ROW_NUMBER() OVER (ORDER BY d))::int AS grp_key
            FROM days
        ),
        streaks AS (
            SELECT COUNT(*) AS streak_len FROM grp GROUP BY grp_key
        )
        SELECT
            (SELECT COUNT(*) FROM days) AS total_days,
            COALESCE((SELECT MAX(streak_len) FROM streaks), 0) AS max_streak;
    """, (user_id,))
    row = cur.fetchone()
    return {"total_days": row["total_days"], "max_streak": row["max_streak"]}


def _evaluate_achievements(cur, user_id: int):
    """把新達成的成就寫進 user_achievements；已經 achieved=TRUE 的不重算、不覆蓋 achieved_at。"""
    cur.execute("""
        SELECT a.achievement_id, a.condition_key
        FROM achievements a
        LEFT JOIN user_achievements ua ON ua.achievement_id = a.achievement_id AND ua.user_id = %s
        WHERE a.condition_key IS NOT NULL AND COALESCE(ua.achieved, FALSE) = FALSE;
    """, (user_id,))
    pending = cur.fetchall()
    if not pending:
        return

    stats = _exercise_streak_stats(cur, user_id)
    for row in pending:
        check = _ACHIEVEMENT_CONDITIONS.get(row["condition_key"])
        if check is None or not check(cur, user_id, stats):
            continue
        cur.execute("""
            INSERT INTO user_achievements (user_id, achievement_id, achieved, achieved_at)
            VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, achievement_id) DO UPDATE SET
                achieved = TRUE,
                achieved_at = COALESCE(user_achievements.achieved_at, EXCLUDED.achieved_at);
        """, (user_id, row["achievement_id"]))


def get_achievements(user_id: int) -> list:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            _evaluate_achievements(cur, user_id)
            cur.execute("""
                SELECT a.achievement_id AS id, a.name, a.description, a.icon,
                       COALESCE(ua.achieved, FALSE) AS achieved,
                       ua.achieved_at, COALESCE(ua.is_displayed, FALSE) AS is_displayed
                FROM achievements a
                LEFT JOIN user_achievements ua ON ua.achievement_id = a.achievement_id AND ua.user_id = %s
                ORDER BY a.sort_order, a.achievement_id;
            """, (user_id,))
            rows = cur.fetchall()
            for r in rows:
                if r["achieved_at"] is not None:
                    r["achieved_at"] = r["achieved_at"].isoformat()
                else:
                    r["achieved_at"] = ""
            return rows


def save_displayed_achievements(user_id: int, achievement_ids: list) -> list:
    ids = set(achievement_ids)
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT achievement_id FROM user_achievements
                WHERE user_id = %s AND achieved = TRUE;
            """, (user_id,))
            achieved_ids = {r["achievement_id"] for r in cur.fetchall()}
            to_display = ids & achieved_ids
            cur.execute("""
                UPDATE user_achievements SET is_displayed = FALSE WHERE user_id = %s;
            """, (user_id,))
            for aid in to_display:
                cur.execute("""
                    INSERT INTO user_achievements (user_id, achievement_id, achieved, is_displayed)
                    VALUES (%s, %s, TRUE, TRUE)
                    ON CONFLICT (user_id, achievement_id) DO UPDATE SET is_displayed = TRUE;
                """, (user_id, aid))
    return get_achievements(user_id)


# ───────────── 個人設定 ─────────────

def get_settings(user_id: int) -> dict:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_settings (user_id) VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING;
            """, (user_id,))
            cur.execute("""
                SELECT font_size, master_volume, sfx_volume, music_volume, tts_enabled
                FROM user_settings WHERE user_id = %s;
            """, (user_id,))
            return _require_row(cur.fetchone(), "找不到設定資料")


def save_settings(user_id: int, font_size: int, master_volume: float,
                   sfx_volume: float, music_volume: float, tts_enabled: bool) -> dict:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_settings (user_id, font_size, master_volume, sfx_volume, music_volume, tts_enabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    font_size = EXCLUDED.font_size,
                    master_volume = EXCLUDED.master_volume,
                    sfx_volume = EXCLUDED.sfx_volume,
                    music_volume = EXCLUDED.music_volume,
                    tts_enabled = EXCLUDED.tts_enabled;
            """, (user_id, font_size, master_volume, sfx_volume, music_volume, tts_enabled))
    return get_settings(user_id)


# ───────────── 運動紀錄（給數據分析頁的長條圖用，重用既有 exercise_logs） ─────────────

def get_exercise_sessions(user_id: int, date_from: str, date_to: str) -> list:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT exercise_log_id AS id, user_id, started_at,
                       COALESCE(duration_seconds, 0) / 60.0 AS duration_min,
                       COALESCE(exercise_type, '運動') AS exercise_type
                FROM exercise_logs
                WHERE user_id = %s AND started_at >= %s AND started_at < %s
                ORDER BY started_at;
            """, (user_id, date_from, date_to))
            rows = cur.fetchall()
            for r in rows:
                if r["started_at"] is not None:
                    r["started_at"] = r["started_at"].isoformat()
            return rows


# ───────────── 飲食週報（取代原規格的每日營養攝取，見 PhotoManager.GetWeeklyObservation） ─────────────

def save_weekly_diet_review(user_id: int, week_monday: str, vegetable_score: int,
                             fried_score: int, variety_score: int, ai_observation: str) -> dict:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_weekly_diet_reviews
                    (user_id, week_monday, vegetable_score, fried_score, variety_score, ai_observation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, week_monday) DO UPDATE SET
                    vegetable_score = EXCLUDED.vegetable_score,
                    fried_score = EXCLUDED.fried_score,
                    variety_score = EXCLUDED.variety_score,
                    ai_observation = EXCLUDED.ai_observation,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, week_monday, vegetable_score, fried_score, variety_score, ai_observation))
            # 存檔當下順便評估一次成就（飲食達人要看這張表）。
            _evaluate_achievements(cur, user_id)
    return get_latest_weekly_diet_review(user_id)


def get_latest_weekly_diet_review(user_id: int):
    """回傳最新一週的飲食評分；還沒有任何一週資料時回傳 None。"""
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT week_monday, vegetable_score, fried_score, variety_score, ai_observation
                FROM user_weekly_diet_reviews
                WHERE user_id = %s
                ORDER BY week_monday DESC
                LIMIT 1;
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                return None
            result = dict(row)
            result["week_monday"] = result["week_monday"].isoformat()
            return result
