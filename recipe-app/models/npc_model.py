"""V1.2 NPC offers/acceptance. Uses existing DB only; no schema initialization."""
import logging
import random
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from config.database import get_db_conn
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
OPEN = ("accepted", "in_progress", "interrupted", "completed", "claimable")
DONE = ("completed", "claimable", "rewarded")
TAIPEI = ZoneInfo("Asia/Taipei")

# Exercise is canonical. Compatibility aliases remain in API responses.
TASK_SELECT = """
 SELECT t.*, n.npc_id, n.npc_key, n.npc_name, n.image_key AS npc_image_key,
 e.exercise_key, e.exercise_category, e.input_type, e.recognition_key,
 e.exercise_scene_key, e.default_required_ball_count, a.priority, a.weight,
 (u.task_id IS NOT NULL OR t.is_initial_unlock) AS unlocked
 FROM npc_task_assignments a JOIN tasks t ON t.task_id=a.task_id
 JOIN npcs n ON n.npc_id=a.npc_id
 JOIN exercise_definitions e ON e.exercise_id=t.exercise_id
 LEFT JOIN user_task_unlocks u ON u.task_id=t.task_id AND u.user_id=%s
 WHERE n.npc_id=%s AND a.is_active AND n.is_active AND t.is_active AND e.is_active
 AND t.scene_id=n.scene_id
"""


def _prerequisites_satisfied(cur, user_id, task_id):
    cur.execute(
        """SELECT 1 FROM task_prerequisites p WHERE p.task_id=%s AND p.is_active
       AND NOT EXISTS (SELECT 1 FROM user_task_progress x
       WHERE x.user_id=%s AND x.task_id=p.prerequisite_task_id
       AND ((p.required_status='rewarded' AND x.status='rewarded')
       OR (p.required_status='completed' AND x.status IN ('completed','claimable','rewarded')))) LIMIT 1""",
        (task_id, user_id),
    )
    return cur.fetchone() is None


def _active(cur, user_id, task_id):
    cur.execute(
        """SELECT * FROM user_task_progress WHERE user_id=%s AND task_id=%s
       AND status IN ('accepted','in_progress','interrupted','completed','claimable')
       ORDER BY progress_id DESC LIMIT 1""",
        (user_id, task_id),
    )
    return cur.fetchone()


def _eligible(cur, user_id, task, day):
    if not task["is_listed"]:
        return False
    if task["task_kind"] == "daily_commission":
        # Commission pool and replacement policy are not implemented yet.
        return False
    if task["task_kind"] == "daily_challenge":
        cur.execute(
            """SELECT 1 FROM daily_tasks d WHERE d.user_id=%s AND d.task_date=%s
          AND d.eligibility_mode='challenge' AND d.eligibility_key=%s
          AND (d.eligibility_state='rewarded' OR EXISTS
          (SELECT 1 FROM reward_transactions r WHERE r.daily_task_id=d.daily_task_id)) LIMIT 1""",
            (user_id, day, task["task_key"]),
        )
        return cur.fetchone() is None
    if task["recurrence_type"] != "none":
        # Do not guess semantics for unplanned recurring story tasks.
        return False
    cur.execute(
        """SELECT 1 FROM user_task_progress WHERE user_id=%s AND task_id=%s
       AND status IN ('completed','claimable','rewarded') LIMIT 1""",
        (user_id, task["task_id"]),
    )
    return cur.fetchone() is None


def _payload(cur, task, progress=None):
    e = task
    if progress:
        if progress.get("snapshot_exercise_id") is None:
            raise ValueError("這筆歷史任務缺少接取快照，請先確認遷移")
        cur.execute(
            "SELECT * FROM exercise_definitions WHERE exercise_id=%s",
            (progress["snapshot_exercise_id"],),
        )
        e = cur.fetchone()
        if not e:
            raise ValueError("找不到接取時的運動設定")
    out = {
        k: task.get(k)
        for k in (
            "npc_id",
            "npc_key",
            "npc_name",
            "npc_image_key",
            "scene_id",
            "task_id",
            "task_key",
            "task_name",
            "task_description",
            "task_category",
            "task_kind",
            "task_type",
            "task_mode",
            "allow_pause",
            "allow_resume",
        )
    }
    out.update(
        {
            k: e.get(k)
            for k in (
                "exercise_key",
                "input_type",
                "recognition_key",
                "exercise_scene_key",
            )
        }
    )
    out["exercise_id"] = (
        progress["snapshot_exercise_id"] if progress else task["exercise_id"]
    )
    out["exercise_category"] = e["exercise_category"]
    # Old Unity compatibility; recognition_key is the new canonical action identifier.
    out["exercise_type"] = task["exercise_type"]
    out["action_type"] = out["exercise_type"]
    out["input_requirement"] = (
        "imu_required" if e["input_type"] == "phone_imu" else "ball_required"
    )
    out["required_ball_count"] = e["default_required_ball_count"]
    out["goal_type"] = (
        progress["snapshot_goal_type"] if progress else task["goal_type"]
    )
    for k in ("target_count", "target_seconds"):
        out[k] = progress[k] if progress else task[k]
    for k, snap in (
        ("reward_player_exp", "snapshot_player_exp"),
        ("reward_scene_exp", "snapshot_scene_exp"),
        ("reward_money", "snapshot_money"),
    ):
        out[k] = progress[snap] if progress else task[k]
    out.update(
        task_progress_id=progress["progress_id"] if progress else None,
        status=progress["status"] if progress else "available",
        progress_count=progress["progress_count"] if progress else 0,
        progress_seconds=progress["progress_seconds"] if progress else 0,
        resumable=bool(progress and progress["status"] in OPEN[:3]),
        reward_pending=bool(
            progress and progress["status"] in ("completed", "claimable")
        ),
        story_variant=progress.get("story_variant") if progress else None,
    )
    return out


def _story(cur, task_id, variant=None):
    cur.execute(
        """SELECT DISTINCT story_variant FROM task_story_steps
       WHERE task_id=%s AND story_phase IN ('intro','offer') ORDER BY story_variant""",
        (task_id,),
    )
    variants = [r["story_variant"] for r in cur.fetchall()]
    if variant and variants and variant not in variants:
        raise ValueError("故事版本不存在")
    variant = variant or (random.choice(variants) if variants else "A")
    if not variants and variant != "A":
        raise ValueError("此任務僅支援預設故事版本 A")
    cur.execute(
        """SELECT dialogue_text FROM task_story_steps WHERE task_id=%s AND story_variant=%s
       AND story_phase IN ('intro','offer') ORDER BY step_order""",
        (task_id, variant),
    )
    return variant, "\n".join(
        r["dialogue_text"] for r in cur.fetchall() if r.get("dialogue_text")
    )


def get_npc_task_offer(user_id, npc_key):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT npc_id FROM npcs WHERE npc_key=%s AND is_active",
                (npc_key,),
            )
            npc = cur.fetchone()
            if not npc:
                return {"success": False, "message": "找不到啟用的 NPC"}
            cur.execute(
                "SELECT player_level FROM user_stats WHERE user_id=%s",
                (user_id,),
            )
            stats = cur.fetchone()
            if not stats:
                return {"success": False, "message": "找不到玩家資料"}
            cur.execute(TASK_SELECT, (user_id, npc["npc_id"]))
            tasks = cur.fetchall()
            available = []
            pending = []
            day = datetime.now(TAIPEI).date()
            for t in tasks:
                p = _active(cur, user_id, t["task_id"])
                # Existing progress stays reachable even if its new-offer listing was hidden.
                if p:
                    pending.append((t, p))
                    continue
                if (
                    t["unlocked"]
                    and t["required_player_level"] <= stats["player_level"]
                    and _eligible(cur, user_id, t, day)
                    and _prerequisites_satisfied(cur, user_id, t["task_id"])
                ):
                    available.append(t)
            if pending:
                t, p = sorted(pending, key=lambda x: x[1]["progress_id"])[0]
                out = _payload(cur, t, p)
                out["dialogue_text"] = (
                    "運動已完成，獎勵處理中。"
                    if out["reward_pending"]
                    else "已保留進度，準備好就可以繼續。"
                )
            elif available:
                maxp = max(t["priority"] for t in available)
                pool = [t for t in available if t["priority"] == maxp]
                t = random.choices(
                    pool, weights=[t["weight"] for t in pool], k=1)[0]
                out = _payload(cur, t)
                out["story_variant"], text = _story(cur, t["task_id"])
                out["dialogue_text"] = text or t["task_description"] or t["task_name"]
            else:
                return {
                    "success": True,
                    "has_task": False,
                    "message": "目前沒有可接取的任務",
                }
            return {
                "success": True,
                "has_task": True,
                "message": "取得 NPC 任務成功",
                **out,
            }
    except ValueError as exc:
        return {"success": False, "message": str(exc)}
    except Exception:
        logger.exception("NPC offer failed")
        return {
            "success": False,
            "message": "暫時無法取得任務，請稍後再試",
        }
    finally:
        conn.close()


def accept_or_decline_task(
    user_id,
    npc_id,
    task_id,
    accepted,
    story_variant="A",
    accept_request_id=None,
):
    if not accepted:
        return {
            "success": True,
            "status": "declined",
            "message": "已暫時不接取此任務",
        }
    try:
        request_id = str(UUID(str(accept_request_id))
                         ) if accept_request_id else None
    except ValueError:
        return {"success": False, "message": "accept_request_id 必須是 UUID"}
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # One user lock serializes acceptance across devices and daily creation.
            cur.execute(
                "SELECT player_level FROM user_stats WHERE user_id=%s FOR UPDATE",
                (user_id,),
            )
            stats = cur.fetchone()
            if not stats:
                raise ValueError("找不到玩家資料")
            cur.execute(
                TASK_SELECT + " AND t.task_id=%s",
                (user_id, npc_id, task_id),
            )
            t = cur.fetchone()
            if not t:
                raise ValueError("任務或 NPC 對應不存在／已停用")
            if request_id:
                cur.execute(
                    "SELECT * FROM user_task_progress WHERE user_id=%s AND accept_request_id=%s",
                    (user_id, request_id),
                )
                original = cur.fetchone()
                if original:
                    if (
                        original["task_id"] != task_id
                        or original["source_npc_id"] != npc_id
                    ):
                        raise ValueError("此請求識別碼已用於其他任務")
                    out = _payload(cur, t, original)
                    conn.commit()
                    return {
                        "success": True,
                        "resumed": True,
                        "idempotent_replay": True,
                        **out,
                    }
            p = _active(cur, user_id, task_id)
            if p:
                out = _payload(cur, t, p)
                conn.commit()
                return {"success": True, "resumed": True, **out}
            if not t["unlocked"] or t["required_player_level"] > stats["player_level"]:
                raise ValueError("任務尚未解鎖")
            day = datetime.now(TAIPEI).date()
            if not _eligible(cur, user_id, t, day) or not _prerequisites_satisfied(
                cur, user_id, task_id
            ):
                raise ValueError("此任務目前不可接取或今日已完成")
            if t["expire_policy"] != "none":
                raise ValueError("限時任務尚未納入本次版本")
            variant, _ = _story(cur, task_id, story_variant)
            daily_id = None
            if t["task_kind"] == "daily_challenge":
                cur.execute(
                    """INSERT INTO daily_tasks(user_id,task_id,task_date,slot_no,refresh_round,
                    eligibility_mode,eligibility_key,eligibility_scene_id)
                    VALUES(%s,%s,%s,1,1,'challenge',%s,%s)
                    ON CONFLICT(user_id,task_date,eligibility_key) WHERE eligibility_mode='challenge'
                    DO NOTHING RETURNING daily_task_id""",
                    (user_id, task_id, day, t["task_key"], t["scene_id"]),
                )
                d = cur.fetchone()
                if not d:
                    cur.execute(
                        """SELECT daily_task_id,task_id,eligibility_state FROM daily_tasks
                      WHERE user_id=%s AND task_date=%s AND eligibility_mode='challenge'
                      AND eligibility_key=%s FOR UPDATE""",
                        (user_id, day, t["task_key"]),
                    )
                    d = cur.fetchone()
                    if (
                        not d
                        or d["task_id"] != task_id
                        or d["eligibility_state"] == "rewarded"
                    ):
                        raise ValueError("每日資格不可使用")
                daily_id = d["daily_task_id"]
            cur.execute(
                """INSERT INTO user_task_progress(user_id,task_id,daily_task_id,source_type,
                source_npc_id,story_variant,status,accepted_at,accept_request_id)
                VALUES(%s,%s,%s,'npc',%s,%s,'accepted',CURRENT_TIMESTAMP,%s) RETURNING *""",
                (user_id, task_id, daily_id, npc_id, variant, request_id),
            )
            # Includes DB-trigger-created immutable snapshots.
            p = cur.fetchone()
            out = _payload(cur, t, p)
            conn.commit()
            return {"success": True, "resumed": False, "message": "任務接受成功", **out}
    except ValueError as exc:
        conn.rollback()
        return {"success": False, "message": str(exc)}
    except Exception:
        conn.rollback()
        logger.exception("NPC accept failed")
        return {"success": False, "message": "接取失敗，請重試或重新查詢任務"}
    finally:
        conn.close()


def complete_task(user_id, task_progress_id):
    from services.reward_service import reward_task
    from services.exercise_rules import RuleError
    try:
        return {"success": True, "reward": reward_task(user_id, task_progress_id)}
    except RuleError as exc:
        return {"success": False, "message": str(exc)}
    except Exception:
        logger.exception("Reward retry failed")
        return {"success": False, "message": "獎勵處理中，稍後自動重試"}


def get_self_training_exercises(user_id):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT e.exercise_id,e.exercise_key,e.exercise_name,e.exercise_category,
              e.input_type,e.recognition_key,e.exercise_scene_key,e.default_required_ball_count,
              o.count_presets,o.default_count,o.min_count,o.max_count,o.count_step,
              o.seconds_presets,o.default_seconds,o.min_seconds,o.max_seconds,o.seconds_step
              FROM exercise_definitions e JOIN exercise_goal_options o USING(exercise_id)
              WHERE e.is_active ORDER BY e.exercise_id"""
            )
            return {
                "success": True,
                "exercises": [
                    dict(
                        r,
                        reward_player_exp=0,
                        reward_scene_exp=0,
                        reward_money=0,
                    )
                    for r in cur.fetchall()
                ],
            }
    finally:
        conn.close()


def start_self_training(user_id, task_id):
    return {
        "success": False,
        "message": "自主運動改用 Exercise 與自訂目標；Session 開始入口尚待下一步完成",
    }
