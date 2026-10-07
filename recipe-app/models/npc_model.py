"""
NPC 任務模型 - Phase 5B
=======================
重點：
1. 保留既有 none / daily / weekly recurrence。
2. 若已有 accepted / in_progress / interrupted，NPC 仍可把任務提供出來，
   accept 時會回傳 resumed=True，不建立第二筆 progress。
3. 支援開發者一次性 replay permit：
   user_task_test_replays.used_at IS NULL
   → 允許建立一筆新的 progress
   → 建立成功後消耗該 permit
"""

import random
from datetime import datetime, timedelta

from config.database import get_db_conn
from psycopg2.extras import RealDictCursor


COMPLETED_ENOUGH_FOR_PREREQUISITE = ("completed", "claimable", "rewarded")
ACTIVE_OR_RESUMABLE = ("accepted", "in_progress", "interrupted")
FINAL_NONREPEATABLE = ("completed", "claimable", "rewarded", "abandoned")


def _weighted_pick(rows):
    if not rows:
        return None

    max_priority = max(int(r.get("priority") or 0) for r in rows)
    top = [r for r in rows if int(r.get("priority") or 0) == max_priority]
    weights = [max(1, int(r.get("weight") or 1)) for r in top]
    return random.choices(top, weights=weights, k=1)[0]


def _calculate_expires_at(task):
    policy = task.get("expire_policy") or "none"
    now = datetime.now()

    if policy == "none":
        return None

    if policy == "after_accept":
        seconds = task.get("expire_after_seconds")
        if seconds and seconds > 0:
            return now + timedelta(seconds=int(seconds))
        return None

    if policy == "end_of_day":
        tomorrow = (now + timedelta(days=1)).date()
        return datetime.combine(tomorrow, datetime.min.time())

    if policy == "end_of_week":
        days_until_next_monday = 7 - now.weekday()
        next_monday = (now + timedelta(days=days_until_next_monday)).date()
        return datetime.combine(next_monday, datetime.min.time())

    return None


def _prerequisites_satisfied(cur, user_id: int, task_id: int) -> bool:
    cur.execute(
        """
        SELECT p.prerequisite_task_id, p.required_status
        FROM task_prerequisites p
        WHERE p.task_id = %s
          AND p.is_active = TRUE;
        """,
        (task_id,),
    )
    prerequisites = cur.fetchall()

    for p in prerequisites:
        prerequisite_task_id = p["prerequisite_task_id"]
        required_status = p["required_status"]

        if required_status == "rewarded":
            cur.execute(
                """
                SELECT 1
                FROM user_task_progress
                WHERE user_id = %s
                  AND task_id = %s
                  AND status = 'rewarded'
                LIMIT 1;
                """,
                (user_id, prerequisite_task_id),
            )
        else:
            cur.execute(
                """
                SELECT 1
                FROM user_task_progress
                WHERE user_id = %s
                  AND task_id = %s
                  AND status IN ('completed', 'claimable', 'rewarded')
                LIMIT 1;
                """,
                (user_id, prerequisite_task_id),
            )

        if cur.fetchone() is None:
            return False

    return True


def _get_active_progress(cur, user_id: int, task_id: int):
    cur.execute(
        """
        SELECT progress_id, status, progress_count, progress_seconds,
               target_count, target_seconds, story_variant
        FROM user_task_progress
        WHERE user_id = %s
          AND task_id = %s
          AND status IN ('accepted', 'in_progress', 'interrupted')
        ORDER BY progress_id DESC
        LIMIT 1;
        """,
        (user_id, task_id),
    )
    return cur.fetchone()


def _get_unused_test_replay(cur, user_id: int, task_id: int):
    cur.execute(
        """
        SELECT replay_id
        FROM user_task_test_replays
        WHERE user_id = %s
          AND task_id = %s
          AND used_at IS NULL
        ORDER BY replay_id DESC
        LIMIT 1;
        """,
        (user_id, task_id),
    )
    return cur.fetchone()


def _normal_recurrence_allows_new_accept(cur, user_id: int, task) -> bool:
    """
    只處理正式遊戲 recurrence。
    不處理 active resume，也不處理 dev replay。
    """
    task_id = task["task_id"]
    recurrence = task.get("recurrence_type") or "none"

    cur.execute(
        """
        SELECT progress_id, status, accepted_at
        FROM user_task_progress
        WHERE user_id = %s
          AND task_id = %s
        ORDER BY progress_id DESC;
        """,
        (user_id, task_id),
    )
    rows = cur.fetchall()

    if recurrence == "none":
        return not any(
            row["status"] in FINAL_NONREPEATABLE
            for row in rows
        )

    now = datetime.now()

    if recurrence == "daily":
        for row in rows:
            accepted_at = row.get("accepted_at")
            if accepted_at and accepted_at.date() == now.date():
                return False
        return True

    if recurrence == "weekly":
        iso_year, iso_week, _ = now.isocalendar()

        for row in rows:
            accepted_at = row.get("accepted_at")
            if not accepted_at:
                continue

            y, w, _ = accepted_at.isocalendar()
            if y == iso_year and w == iso_week:
                return False

        return True

    return True


def _is_available_for_offer(cur, user_id: int, task) -> bool:
    """
    NPC 是否應該把這個任務顯示給玩家。

    重要：
    active 任務要允許被 offer，因為後續 accept endpoint 會把它當 resume。
    """
    task_id = task["task_id"]

    if _get_active_progress(cur, user_id, task_id):
        return True

    if _get_unused_test_replay(cur, user_id, task_id):
        return True

    return _normal_recurrence_allows_new_accept(cur, user_id, task)


def _consume_test_replay(cur, replay_id: int, progress_id: int):
    cur.execute(
        """
        UPDATE user_task_test_replays
        SET
            used_at = CURRENT_TIMESTAMP,
            used_progress_id = %s
        WHERE replay_id = %s
          AND used_at IS NULL;
        """,
        (progress_id, replay_id),
    )


def _choose_story_variant(cur, task_id: int) -> str:
    cur.execute(
        """
        SELECT DISTINCT story_variant
        FROM task_story_steps
        WHERE task_id = %s
          AND story_phase IN ('intro', 'offer')
        ORDER BY story_variant;
        """,
        (task_id,),
    )
    variants = [r["story_variant"] for r in cur.fetchall()]
    return random.choice(variants) if variants else "A"


def _load_offer_text(cur, task_id: int, story_variant: str, fallback: str) -> str:
    cur.execute(
        """
        SELECT dialogue_text
        FROM task_story_steps
        WHERE task_id = %s
          AND story_variant = %s
          AND story_phase IN ('intro', 'offer')
        ORDER BY step_order;
        """,
        (task_id, story_variant),
    )
    lines = [
        r["dialogue_text"]
        for r in cur.fetchall()
        if r.get("dialogue_text")
    ]

    if lines:
        return "\n".join(lines)

    return fallback or "要一起完成這個任務嗎？"


def get_npc_task_offer(user_id: int, npc_key: str):
    conn = get_db_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT npc_id, npc_key, scene_id, npc_name, description, image_key,
                       exercise_scene_key
                FROM npcs
                WHERE npc_key = %s
                  AND is_active = TRUE;
                """,
                (npc_key,),
            )
            npc = cur.fetchone()

            if not npc:
                return {
                    "success": False,
                    "message": "找不到此 NPC，或 NPC 尚未啟用",
                }

            cur.execute(
                """
                SELECT player_level
                FROM user_stats
                WHERE user_id = %s;
                """,
                (user_id,),
            )
            stats = cur.fetchone()

            if not stats:
                return {
                    "success": False,
                    "message": "找不到玩家遊戲資料",
                }

            cur.execute(
                """
                SELECT
                    t.*,
                    a.priority,
                    a.weight
                FROM npc_task_assignments a
                JOIN tasks t
                  ON t.task_id = a.task_id
                JOIN user_task_unlocks u
                  ON u.task_id = t.task_id
                 AND u.user_id = %s
                WHERE a.npc_id = %s
                  AND a.is_active = TRUE
                  AND t.is_active = TRUE
                  AND t.scene_id = %s
                  AND t.required_player_level <= %s
                ORDER BY a.priority DESC, t.task_id;
                """,
                (
                    user_id,
                    npc["npc_id"],
                    npc["scene_id"],
                    stats["player_level"],
                ),
            )
            raw_candidates = cur.fetchall()

            candidates = []

            for task in raw_candidates:
                if not _prerequisites_satisfied(
                    cur,
                    user_id,
                    task["task_id"],
                ):
                    continue

                if not _is_available_for_offer(
                    cur,
                    user_id,
                    task,
                ):
                    continue

                candidates.append(task)

            task = _weighted_pick(candidates)

            if not task:
                return {
                    "success": False,
                    "message": "這個 NPC 目前沒有可接取的任務",
                    "npc_id": npc["npc_id"],
                    "npc_key": npc["npc_key"],
                    "npc_name": npc["npc_name"],
                }

            story_variant = _choose_story_variant(
                cur,
                task["task_id"],
            )

            dialogue_text = _load_offer_text(
                cur,
                task["task_id"],
                story_variant,
                task.get("task_description") or task["task_name"],
            )

            active = _get_active_progress(
                cur,
                user_id,
                task["task_id"],
            )

            return {
                "success": True,
                "message": (
                    "取得可恢復 NPC 任務成功"
                    if active
                    else "取得 NPC 任務成功"
                ),
                "resumable": bool(active),
                "npc_id": npc["npc_id"],
                "npc_key": npc["npc_key"],
                "npc_name": npc["npc_name"],
                "npc_image_key": npc.get("image_key"),
                "scene_id": task["scene_id"],
                # 場景路由看 NPC 自己的類別，不是看任務的 exercise_type，
                # 這樣同一個 NPC 以後不管加幾種動作，都保證進同一個 Exercise Scene。
                "exercise_scene_key": npc.get("exercise_scene_key"),
                "dialogue_text": dialogue_text,
                "story_variant": story_variant,
                "task_id": task["task_id"],
                "task_key": task["task_key"],
                "task_name": task["task_name"],
                "task_description": task.get("task_description"),
                "task_category": task["task_category"],
                "task_type": task["task_type"],
                "task_mode": task["task_mode"],
                "exercise_type": task["exercise_type"],
                "action_type": task["exercise_type"],
                "goal_type": task["goal_type"],
                "target_count": task.get("target_count"),
                "target_seconds": task.get("target_seconds"),
                "input_requirement": task.get("input_requirement"),
                "required_ball_count": (
                    task.get("required_ball_count") or 0
                ),
                "allow_pause": task.get("allow_pause"),
                "allow_resume": task.get("allow_resume"),
                "reward_player_exp": (
                    task.get("reward_player_exp") or 0
                ),
                "reward_scene_exp": (
                    task.get("reward_scene_exp") or 0
                ),
                "reward_money": task.get("reward_money") or 0,
            }

    except Exception as e:
        print(f"[NPC Model Error] 取得 NPC 任務失敗: {e}")
        return {
            "success": False,
            "message": f"取得 NPC 任務失敗: {e}",
        }
    finally:
        conn.close()


def accept_or_decline_task(
    user_id: int,
    npc_id: int,
    task_id: int,
    accepted: bool,
    story_variant: str = "A",
):
    if not accepted:
        return {
            "success": True,
            "status": "declined",
            "message": "已暫時不接取此任務",
        }

    conn = get_db_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    t.*,
                    n.npc_name,
                    n.npc_key,
                    n.scene_id AS npc_scene_id,
                    n.exercise_scene_key,
                    us.player_level
                FROM npc_task_assignments a
                JOIN npcs n
                  ON n.npc_id = a.npc_id
                JOIN tasks t
                  ON t.task_id = a.task_id
                JOIN user_stats us
                  ON us.user_id = %s
                JOIN user_task_unlocks u
                  ON u.user_id = %s
                 AND u.task_id = t.task_id
                WHERE a.npc_id = %s
                  AND a.task_id = %s
                  AND a.is_active = TRUE
                  AND n.is_active = TRUE
                  AND t.is_active = TRUE;
                """,
                (user_id, user_id, npc_id, task_id),
            )
            task = cur.fetchone()

            if not task:
                return {
                    "success": False,
                    "message": (
                        "任務不存在、尚未解鎖，"
                        "或此 NPC 無權發送這個任務"
                    ),
                }

            if task["npc_scene_id"] != task["scene_id"]:
                return {
                    "success": False,
                    "message": "NPC 與任務所屬景點不一致",
                }

            if (
                task["player_level"]
                < task["required_player_level"]
            ):
                return {
                    "success": False,
                    "message": "玩家等級尚未達到任務需求",
                }

            if not _prerequisites_satisfied(
                cur,
                user_id,
                task_id,
            ):
                return {
                    "success": False,
                    "message": "前置任務尚未完成",
                }

            # 先處理 resume。
            existing = _get_active_progress(
                cur,
                user_id,
                task_id,
            )

            if existing:
                return {
                    "success": True,
                    "status": "accepted",
                    "message": "此任務已接取，將使用原本的任務進度",
                    "resumed": True,
                    "task_progress_id": existing["progress_id"],
                    "task_id": task["task_id"],
                    "task_key": task["task_key"],
                    "task_name": task["task_name"],
                    "scene_id": task["scene_id"],
                    "exercise_type": task["exercise_type"],
                    "exercise_scene_key": task["exercise_scene_key"],
                    "goal_type": task["goal_type"],
                    "target_count": existing["target_count"],
                    "target_seconds": existing["target_seconds"],
                    "input_requirement": task.get("input_requirement"),
                    "required_ball_count": (
                        task.get("required_ball_count") or 0
                    ),
                    "story_variant": (
                        existing.get("story_variant")
                        or story_variant
                    ),
                    "reward_player_exp": (
                        task.get("reward_player_exp") or 0
                    ),
                    "reward_scene_exp": (
                        task.get("reward_scene_exp") or 0
                    ),
                    "reward_money": (
                        task.get("reward_money") or 0
                    ),
                }

            # Replay permit 優先：
            # 只要 Admin 明確要求重新測試，
            # 下一次建立新 progress 就會消耗它。
            replay = _get_unused_test_replay(
                cur,
                user_id,
                task_id,
            )

            normal_allowed = _normal_recurrence_allows_new_accept(
                cur,
                user_id,
                task,
            )

            if not replay and not normal_allowed:
                return {
                    "success": False,
                    "message": "此任務目前不能再次接取",
                }

            expires_at = _calculate_expires_at(task)

            cur.execute(
                """
                INSERT INTO user_task_progress (
                    user_id,
                    task_id,
                    daily_task_id,
                    source_type,
                    source_npc_id,
                    story_variant,
                    status,
                    progress_count,
                    target_count,
                    progress_seconds,
                    target_seconds,
                    accepted_at,
                    expires_at,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s, %s, NULL,
                    'npc', %s, %s,
                    'accepted',
                    0, %s,
                    0, %s,
                    CURRENT_TIMESTAMP,
                    %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                RETURNING progress_id, accepted_at;
                """,
                (
                    user_id,
                    task_id,
                    npc_id,
                    story_variant,
                    task.get("target_count"),
                    task.get("target_seconds"),
                    expires_at,
                ),
            )

            progress = cur.fetchone()

            if replay:
                _consume_test_replay(
                    cur,
                    replay["replay_id"],
                    progress["progress_id"],
                )

            conn.commit()

            return {
                "success": True,
                "status": "accepted",
                "message": (
                    "測試重跑任務接受成功"
                    if replay
                    else "任務接受成功"
                ),
                "resumed": False,
                "test_replay": bool(replay),
                "task_progress_id": progress["progress_id"],
                "task_id": task["task_id"],
                "task_key": task["task_key"],
                "task_name": task["task_name"],
                "scene_id": task["scene_id"],
                "exercise_type": task["exercise_type"],
                "exercise_scene_key": task["exercise_scene_key"],
                "goal_type": task["goal_type"],
                "target_count": task.get("target_count"),
                "target_seconds": task.get("target_seconds"),
                "input_requirement": task.get("input_requirement"),
                "required_ball_count": (
                    task.get("required_ball_count") or 0
                ),
                "story_variant": story_variant,
                "reward_player_exp": (
                    task.get("reward_player_exp") or 0
                ),
                "reward_scene_exp": (
                    task.get("reward_scene_exp") or 0
                ),
                "reward_money": task.get("reward_money") or 0,
            }

    except Exception as e:
        conn.rollback()
        print(f"[NPC Model Error] 接取任務失敗: {e}")
        return {
            "success": False,
            "message": f"接取任務失敗: {e}",
        }
    finally:
        conn.close()


def complete_task(user_id: int, task_progress_id: int):
    """
    玩家完成任務(暫時先不分 completed -> claim 兩步，直接完成即發獎):
    1. 玩家整體 EXP / 金幣，沿用其他功能一致的「每 1000 經驗升 1 級」公式。
    2. 場景完成次數 completion_count(跟 scene_exp 分開的獨立欄位，語意只做外觀解鎖用):
       每滿 20 次，scene_level +1、completion_count 歸零重算。
    3. user_task_progress 狀態改為 rewarded。
    """
    conn = get_db_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    p.progress_id,
                    p.status,
                    p.source_type,
                    t.task_id,
                    t.task_name,
                    t.scene_id,
                    t.reward_player_exp,
                    t.reward_scene_exp,
                    t.reward_money
                FROM user_task_progress p
                JOIN tasks t ON t.task_id = p.task_id
                WHERE p.progress_id = %s
                  AND p.user_id = %s
                FOR UPDATE;
                """,
                (task_progress_id, user_id),
            )
            progress = cur.fetchone()

            if not progress:
                return {
                    "success": False,
                    "message": "找不到這筆任務進度",
                }

            if progress["status"] not in ACTIVE_OR_RESUMABLE:
                return {
                    "success": False,
                    "message": f"這筆任務目前狀態是「{progress['status']}」，無法完成",
                }

            # 自主運動(老山狐/活動中心)：玩家經驗值、金幣減半，
            # 不給景點經驗值、不計入建築外觀升級次數(completion_count 完全不動)。
            is_self_training = progress["source_type"] == "self_training"

            reward_player_exp = (progress["reward_player_exp"] or 0)
            reward_money = (progress["reward_money"] or 0)
            reward_scene_exp = 0 if is_self_training else (progress["reward_scene_exp"] or 0)

            if is_self_training:
                reward_player_exp //= 2
                reward_money //= 2

            cur.execute(
                """
                UPDATE user_stats
                SET player_exp = (player_exp + %s) %% 1000,
                    player_level = player_level + floor((player_exp + %s) / 1000)::int,
                    money = money + %s
                WHERE user_id = %s
                RETURNING player_level, player_exp, money;
                """,
                (reward_player_exp, reward_player_exp, reward_money, user_id),
            )
            player_stats = cur.fetchone()

            if is_self_training:
                # 自主運動完全不動景點進度/建築外觀升級次數，單純讀現況回傳給 Unity。
                cur.execute(
                    """
                    SELECT scene_level, scene_exp, completion_count, display_level_cap
                    FROM user_scenes
                    WHERE user_id = %s
                      AND scene_id = %s;
                    """,
                    (user_id, progress["scene_id"]),
                )
                scene_stats = cur.fetchone()
                scene_stats["leveled_up"] = False
            else:
                cur.execute(
                    """
                    UPDATE user_scenes
                    SET scene_exp = scene_exp + %s,
                        completion_count = CASE
                            WHEN completion_count + 1 >= 20 THEN completion_count + 1 - 20
                            ELSE completion_count + 1
                        END,
                        scene_level = scene_level + CASE
                            WHEN completion_count + 1 >= 20 THEN 1
                            ELSE 0
                        END,
                        -- 場景升級的當下，把玩家先前手動調回舊外觀的選擇清掉，
                        -- 讓新解鎖的階段重新變成預設顯示(玩家之後可以再手動調回去)。
                        display_level_cap = CASE
                            WHEN completion_count + 1 >= 20 THEN NULL
                            ELSE display_level_cap
                        END
                    WHERE user_id = %s
                      AND scene_id = %s
                    RETURNING scene_level, scene_exp, completion_count, display_level_cap,
                        (completion_count = 0) AS leveled_up;
                    """,
                    (reward_scene_exp, user_id, progress["scene_id"]),
                )
                scene_stats = cur.fetchone()

            cur.execute(
                """
                UPDATE user_task_progress
                SET status = 'rewarded',
                    completed_at = CURRENT_TIMESTAMP,
                    rewarded_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE progress_id = %s;
                """,
                (task_progress_id,),
            )

            conn.commit()

            return {
                "success": True,
                "message": f"「{progress['task_name']}」完成！",
                "task_id": progress["task_id"],
                "task_progress_id": task_progress_id,
                "player_level": player_stats["player_level"],
                "player_exp": player_stats["player_exp"],
                "money": player_stats["money"],
                "scene_id": progress["scene_id"],
                "scene_level": scene_stats["scene_level"],
                "scene_exp": scene_stats["scene_exp"],
                "completion_count": scene_stats["completion_count"],
                # Unity 的 JsonUtility 讀不了 JSON null 進 int 欄位，-1 代表沒有手動覆寫。
                "display_level_cap": (
                    -1 if scene_stats["display_level_cap"] is None
                    else scene_stats["display_level_cap"]
                ),
                "leveled_up": scene_stats["leveled_up"],
            }

    except Exception as e:
        conn.rollback()
        print(f"[NPC Model Error] 完成任務失敗: {e}")
        return {
            "success": False,
            "message": f"完成任務失敗: {e}",
        }
    finally:
        conn.close()


# ============================================================
# 自主運動(老山狐 / 活動中心)：
# 玩家可以自由挑選任何已解鎖的運動任務來練習，不綁定特定 NPC、不限次數，
# 但完成獎勵的玩家經驗值/金幣減半、不給景點經驗值、不計入建築外觀升級次數。
# 跟故事任務(npc_task_assignments 綁 NPC)是分開的兩條路，不會互相佔用每日/每週次數限制。
# ============================================================

def get_self_training_exercises(user_id: int):
    """
    回傳玩家目前所有已解鎖、而且掛在「有效運動類別 NPC」底下的任務，
    不分是哪個 NPC 發的，老山狐這裡全部混在一起給玩家自由選。
    """
    conn = get_db_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (t.task_id)
                    t.task_id,
                    t.task_key,
                    t.task_name,
                    t.task_description,
                    t.exercise_type,
                    t.goal_type,
                    t.target_count,
                    t.target_seconds,
                    t.input_requirement,
                    t.required_ball_count,
                    t.reward_player_exp,
                    t.reward_scene_exp,
                    t.reward_money,
                    t.scene_id,
                    n.exercise_scene_key
                FROM tasks t
                JOIN user_task_unlocks u
                  ON u.task_id = t.task_id
                 AND u.user_id = %s
                JOIN npc_task_assignments a
                  ON a.task_id = t.task_id
                 AND a.is_active = TRUE
                JOIN npcs n
                  ON n.npc_id = a.npc_id
                 AND n.is_active = TRUE
                WHERE t.is_active = TRUE
                  AND t.exercise_type IS NOT NULL
                  AND n.exercise_scene_key IS NOT NULL
                ORDER BY t.task_id;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

            exercises = []
            for row in rows:
                exercises.append({
                    "task_id": row["task_id"],
                    "task_key": row["task_key"],
                    "task_name": row["task_name"],
                    "task_description": row.get("task_description"),
                    "exercise_type": row["exercise_type"],
                    "exercise_scene_key": row["exercise_scene_key"],
                    "goal_type": row["goal_type"],
                    "target_count": row.get("target_count"),
                    "target_seconds": row.get("target_seconds"),
                    "input_requirement": row.get("input_requirement"),
                    "required_ball_count": row.get("required_ball_count") or 0,
                    # 自主運動的實際獎勵是原任務的一半，先算好給 Unity 顯示用，
                    # 真正發獎勵時 complete_task 會用同樣的規則重算一次(不信任前端)。
                    "reward_player_exp": (row.get("reward_player_exp") or 0) // 2,
                    "reward_scene_exp": 0,
                    "reward_money": (row.get("reward_money") or 0) // 2,
                })

            return {
                "success": True,
                "exercises": exercises,
            }

    except Exception as e:
        print(f"[NPC Model Error] 取得自主運動清單失敗: {e}")
        return {
            "success": False,
            "message": f"取得自主運動清單失敗: {e}",
        }
    finally:
        conn.close()


def start_self_training(user_id: int, task_id: int):
    """
    開始一次自主運動：不檢查每日/每週次數限制(那是故事任務的規則)，
    每次呼叫都直接建立一筆新的 progress，掛 source_type='self_training'。
    """
    conn = get_db_conn()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT t.task_id, t.task_key, t.task_name, t.scene_id,
                       t.exercise_type, t.goal_type, t.target_count, t.target_seconds,
                       t.input_requirement, t.required_ball_count,
                       t.reward_player_exp, t.reward_scene_exp, t.reward_money,
                       n.npc_id AS fox_npc_id, n.exercise_scene_key
                FROM tasks t
                JOIN user_task_unlocks u
                  ON u.task_id = t.task_id
                 AND u.user_id = %s
                JOIN npc_task_assignments a
                  ON a.task_id = t.task_id
                 AND a.is_active = TRUE
                JOIN npcs n
                  ON n.npc_id = a.npc_id
                 AND n.is_active = TRUE
                JOIN npcs fox
                  ON fox.npc_key = 'ACTIVITY_LAOSHANHU'
                WHERE t.task_id = %s
                  AND t.is_active = TRUE
                  AND t.exercise_type IS NOT NULL
                  AND n.exercise_scene_key IS NOT NULL
                LIMIT 1;
                """,
                (user_id, task_id),
            )
            task = cur.fetchone()

            if not task:
                return {
                    "success": False,
                    "message": "這個運動不存在、尚未解鎖，或目前不能自主練習",
                }

            cur.execute(
                """
                SELECT npc_id FROM npcs WHERE npc_key = 'ACTIVITY_LAOSHANHU';
                """
            )
            fox = cur.fetchone()

            cur.execute(
                """
                INSERT INTO user_task_progress (
                    user_id, task_id, daily_task_id,
                    source_type, source_npc_id,
                    status, progress_count, target_count,
                    progress_seconds, target_seconds,
                    accepted_at, created_at, updated_at
                )
                VALUES (
                    %s, %s, NULL,
                    'self_training', %s,
                    'accepted', 0, %s,
                    0, %s,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                RETURNING progress_id;
                """,
                (
                    user_id,
                    task_id,
                    fox["npc_id"] if fox else None,
                    task.get("target_count"),
                    task.get("target_seconds"),
                ),
            )
            progress = cur.fetchone()

            conn.commit()

            return {
                "success": True,
                "status": "accepted",
                "resumed": False,
                "task_progress_id": progress["progress_id"],
                "task_id": task["task_id"],
                "task_key": task["task_key"],
                "task_name": task["task_name"],
                "scene_id": task["scene_id"],
                "exercise_type": task["exercise_type"],
                "exercise_scene_key": task["exercise_scene_key"],
                "goal_type": task["goal_type"],
                "target_count": task.get("target_count"),
                "target_seconds": task.get("target_seconds"),
                "input_requirement": task.get("input_requirement"),
                "required_ball_count": task.get("required_ball_count") or 0,
                "story_variant": "A",
                # 這裡先回傳半額給 Unity 顯示「預期獎勵」，實際發獎一樣由 complete_task 認定。
                "reward_player_exp": (task.get("reward_player_exp") or 0) // 2,
                "reward_scene_exp": 0,
                "reward_money": (task.get("reward_money") or 0) // 2,
            }

    except Exception as e:
        conn.rollback()
        print(f"[NPC Model Error] 開始自主運動失敗: {e}")
        return {
            "success": False,
            "message": f"開始自主運動失敗: {e}",
        }
    finally:
        conn.close()
