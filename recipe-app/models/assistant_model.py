"""
阿明（長輩陪伴 AI 助手）要用的資料查詢 + 呼叫 Cloudflare Worker。

對應規格：AI助手後端說明.pdf（2026/11/07，規則版本 1104-k）、
assistant_queries.sql、recipe_filter.sql。

這一版的前提：
1. 食材過敏原補標沒做，所以有登記過敏原的長輩直接不給食譜候選，
   不跑 get_recipe_candidates()。
2. 服藥(is_on_medication)、素食(diet_type) 來自 user_profiles，
   軟質食物(need_soft) 由健康狀況「牙口不好」推導
   （schema_assistant_profile_gaps.sql，2026-11-16 補上；之前是寫死 False/'None'/False）。
"""
import logging
import os
from datetime import date

import httpx
from psycopg2.extras import RealDictCursor

from config.database import get_db_conn

log = logging.getLogger(__name__)

WORKER_URL = os.getenv(
    "WORKER_URL", "https://elder-assistant.lm-foodcam-ai.workers.dev/"
)
WORKER_APP_SECRET = os.getenv("WORKER_APP_SECRET")
WORKER_TIMEOUT_SECONDS = float(os.getenv("WORKER_TIMEOUT_SECONDS", "10"))
WORKER_MODEL = "mini"

# 逾時或呼叫失敗固定回這句，不重試——長輩等不了第二輪。
FALLBACK_REPLY = "我這邊有點慢，等一下再跟我說好嗎"

MAX_GAMES = 3
MAX_RECIPES = 3

_PROFILE_SQL = """
    SELECT
      coalesce(p.name, u.username)                                   AS "displayName",
      coalesce(a.allergens, '')                                      AS allergies,
      coalesce(h.conditions, '')                                     AS "chronicConditions",
      coalesce(h.condition_ids, ARRAY[]::int[])                      AS condition_ids,
      coalesce(p.is_on_medication, false)                            AS is_on_medication,
      coalesce(p.diet_type, 'None')                                  AS diet_type,
      coalesce(h.need_soft, false)                                   AS need_soft
    FROM users u
    LEFT JOIN user_profiles p ON p.user_id = u.user_id
    LEFT JOIN LATERAL (
      SELECT string_agg(allergen_name, '、' ORDER BY allergen_name) AS allergens
      FROM user_allergies
      WHERE user_id = u.user_id AND allergen_type = 'food'
    ) a ON true
    LEFT JOIN LATERAL (
      SELECT string_agg(hc.condition_name, '、' ORDER BY hc.condition_id) AS conditions,
             array_agg(hc.condition_id ORDER BY hc.condition_id)          AS condition_ids,
             bool_or(hc.condition_key = 'poor_dental_status')             AS need_soft
      FROM user_health_conditions uhc
      JOIN health_conditions hc ON hc.condition_id = uhc.condition_id
      WHERE uhc.user_id = u.user_id
    ) h ON true
    WHERE u.user_id = %s;
"""

_SUMMARY_SQL = """
    SELECT concat_ws('；',
      CASE WHEN coalesce(st.steps, 0) > 0 THEN '今天步數 ' || st.steps || ' 步' END,
      CASE WHEN ex.secs >= 60    THEN '活動 ' || (ex.secs / 60) || ' 分鐘' END,
      CASE WHEN tk.done IS NOT NULL THEN '完成了' || tk.done || '任務' END,
      CASE WHEN q.played > 0     THEN '玩了問答遊戲' END
    ) AS summary
    FROM (SELECT %s::int AS uid) base
    LEFT JOIN step_logs st
           ON st.user_id = base.uid AND st.step_date = current_date
    LEFT JOIN LATERAL (
      SELECT coalesce(sum(accepted_seconds), 0) AS secs
      FROM exercise_sessions
      WHERE user_id = base.uid
        AND status = 'completed'
        AND ended_at::date = current_date
    ) ex ON true
    LEFT JOIN LATERAL (
      SELECT string_agg(t.task_name, '、' ORDER BY dt.slot_no) AS done
      FROM daily_tasks dt
      JOIN tasks t ON t.task_id = dt.task_id
      JOIN user_task_progress p ON p.daily_task_id = dt.daily_task_id
      WHERE dt.user_id = base.uid
        AND dt.task_date = current_date
        AND p.status IN ('completed', 'claimable', 'rewarded')
    ) tk ON true
    LEFT JOIN LATERAL (
      SELECT count(*) AS played
      FROM user_question_logs
      WHERE user_id = base.uid AND answered_at::date = current_date
    ) q ON true;
"""

# games 只給還沒完成的，限制在 SQL 裡用 LIMIT 做（而不是事後字串裁切），
# 這樣排序（slot_no）跟數量限制一致。
_GAMES_SQL = """
    SELECT string_agg(task_name, '、') AS games
    FROM (
        SELECT t.task_name
        FROM daily_tasks dt
        JOIN tasks t ON t.task_id = dt.task_id
        LEFT JOIN user_accessibility_profiles acc ON acc.user_id = dt.user_id
        WHERE dt.user_id = %(user_id)s
          AND dt.task_date = current_date
          -- 跟 NPC 派任務同一套行動規則（npc_model.task_fits_mobility）：
          -- 不能久站不推要站的，腳不方便動也不推要動腳的
          AND NOT (acc.allow_standing_exercise = FALSE AND t.requires_standing)
          AND NOT (acc.allow_leg_exercise = FALSE AND t.requires_leg_movement)
          AND NOT EXISTS (
            SELECT 1 FROM user_task_progress p
            WHERE p.daily_task_id = dt.daily_task_id
              AND p.status IN ('completed', 'claimable', 'rewarded')
          )
        ORDER BY dt.slot_no
        LIMIT %(max_games)s
    ) x;
"""

# 對應 recipe_filter.sql 的五層篩選；:allergies 在呼叫這支之前就已經保證是空陣列
# （有過敏原的長輩，上層根本不會呼叫這個函式），NOT EXISTS 那段留著當防線。
_RECIPE_FILTER_SQL = """
    SELECT r.id, r.title
    FROM recipes r
    WHERE
      -- 「水果」分類是單一水果（蘋果、木瓜…），不是菜；規格要的是菜名。
      -- 水果都有當季標記，不排除的話會被當季排序擠到最前面。
      NOT EXISTS (
        SELECT 1 FROM categories c WHERE c.id = r.category_id AND c."name" = '水果'
      )
      AND NOT EXISTS (
        SELECT 1
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = r.id
          AND (
            EXISTS (
              SELECT 1
              FROM unnest(string_to_array(coalesce(i.allergen_group, ''), '、')) AS g
              WHERE btrim(g) <> '' AND btrim(g) = ANY(%(allergies)s)
            )
            OR EXISTS (
              SELECT 1
              FROM unnest(%(allergies)s::text[]) AS a
              WHERE i."name" LIKE '%%' || a || '%%'
            )
          )
      )
      AND (
        %(diet_type)s IS DISTINCT FROM 'Vegan'
        OR EXISTS (
          SELECT 1 FROM recipe_tags rt JOIN tags t ON t.id = rt.tag_id
          WHERE rt.recipe_id = r.id AND t."name" = '全素'
        )
      )
      AND NOT EXISTS (
        SELECT 1
        FROM recipe_health_evaluations he
        WHERE he.recipe_id = r.id
          AND he.suitability = '不適合'
          AND (
            -- 優先用 condition_id 比對（病名兩邊寫法不一致，例如「冠狀動脈 / 心血管疾病」vs「心血管疾病」）
            he.condition_id = ANY(%(condition_ids)s::int[])
            OR (he.condition_id IS NULL AND EXISTS (
              SELECT 1 FROM unnest(%(conditions)s::text[]) AS c
              WHERE he.disease_name LIKE '%%' || c || '%%'
            ))
          )
      )
      AND (
        %(need_soft)s IS NOT TRUE
        OR EXISTS (
          SELECT 1 FROM recipe_tags rt JOIN tags t ON t.id = rt.tag_id
          WHERE rt.recipe_id = r.id AND t."name" = '軟質食物'
        )
      )
      AND (
        %(month)s IS NULL
        OR NOT EXISTS (SELECT 1 FROM recipe_seasons rs WHERE rs.recipe_id = r.id)
        OR EXISTS (
          SELECT 1
          FROM recipe_seasons rs JOIN seasons s ON s.id = rs.season_id
          WHERE rs.recipe_id = r.id
            AND (
              s."name" = '全年'
              OR (s."name" = '春' AND %(month)s IN (3,4,5))
              OR (s."name" = '夏' AND %(month)s IN (6,7,8))
              OR (s."name" = '秋' AND %(month)s IN (9,10,11))
              OR (s."name" = '冬' AND %(month)s IN (12,1,2))
            )
        )
      )
    ORDER BY
      (SELECT count(*)
         FROM recipe_health_evaluations he
        WHERE he.recipe_id = r.id
          AND he.suitability = '適合'
          AND (he.condition_id = ANY(%(condition_ids)s::int[])
               OR (he.condition_id IS NULL AND EXISTS (
                     SELECT 1 FROM unnest(%(conditions)s::text[]) c
                     WHERE he.disease_name LIKE '%%' || c || '%%')))
      ) DESC,
      (EXISTS (SELECT 1
                 FROM recipe_seasons rs JOIN seasons s ON s.id = rs.season_id
                WHERE rs.recipe_id = r.id AND s."name" <> '全年')
      ) DESC,
      (%(need_soft)s IS TRUE AND EXISTS (SELECT 1
                 FROM recipe_tags rt JOIN tags t ON t.id = rt.tag_id
                WHERE rt.recipe_id = r.id AND t."name" = '軟質食物')
      ) DESC,
      random()
    LIMIT %(limit)s;
"""


def _split_pipe(value: str):
    """assistant_queries.sql 用頓號(、)分隔多值欄位，這裡還原成陣列。"""
    if not value:
        return []
    return [v.strip() for v in value.split("、") if v.strip()]


def get_profile(user_id: int) -> dict:
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_PROFILE_SQL, (user_id,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return {"displayName": "", "allergies": "", "chronicConditions": "",
                "condition_ids": [], "is_on_medication": False,
                "diet_type": "None", "need_soft": False}
    return dict(row)


def get_summary(user_id: int) -> str:
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_SUMMARY_SQL, (user_id,))
            row = cur.fetchone()
    finally:
        conn.close()
    return (row["summary"] if row else None) or ""


def get_games(user_id: int) -> str:
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_GAMES_SQL, {"user_id": user_id, "max_games": MAX_GAMES})
            row = cur.fetchone()
    finally:
        conn.close()
    return (row["games"] if row else None) or ""


def get_recipe_candidates(profile: dict) -> str:
    """
    篩選後的候選菜名，頓號分隔，最多三道。

    硬性規則（見 recipe_filter.sql 開頭）：呼叫端要先確認
    profile["allergies"] 是空字串才能呼叫這支；這裡仍把 allergies
    當參數傳入當防線，但正常情況下應該永遠是空陣列。
    """
    today = date.today()
    params = {
        "allergies": _split_pipe(profile.get("allergies", "")),
        "diet_type": profile.get("diet_type") or "None",
        "conditions": _split_pipe(profile.get("chronicConditions", "")),
        "condition_ids": list(profile.get("condition_ids") or []),
        "need_soft": bool(profile.get("need_soft")),
        "month": today.month,
        "limit": MAX_RECIPES,
    }

    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_RECIPE_FILTER_SQL, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    return "、".join(r["title"] for r in rows)


def call_worker(payload: dict) -> dict:
    """POST 到阿明的 Cloudflare Worker。逾時或失敗不重試，回固定話。"""
    if not WORKER_APP_SECRET:
        log.error("WORKER_APP_SECRET 未設定，無法呼叫阿明（請在 .env 補上）")
        return {"reply": FALLBACK_REPLY, "factId": "", "safetyLevel": "none"}

    try:
        resp = httpx.post(
            WORKER_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-App-Secret": WORKER_APP_SECRET,
            },
            timeout=WORKER_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        log.exception("呼叫阿明 Worker 失敗")
        return {"reply": FALLBACK_REPLY, "factId": "", "safetyLevel": "none"}

    # reply 一個字都不能改，原樣轉給 App。
    return {
        "reply": data.get("reply", FALLBACK_REPLY),
        "factId": data.get("factId", ""),
        "safetyLevel": data.get("safetyLevel", "none"),
    }


def build_chat_reply(user_id: int, req: dict) -> dict:
    """
    組裝規格裡的五步驟（第 1 步 user_id 由呼叫端的 session 保證）：
    2. 查詢 profile/summary/recipes/games
    3. 組 JSON 送 Worker
    4. 把 reply 原樣轉給 App（第 5 步的逾時/失敗已經包在 call_worker 裡）
    """
    profile = get_profile(user_id)
    summary = get_summary(user_id)
    games = get_games(user_id)

    # 硬性規則：有登記過敏原就不給食譜候選（見 recipe_filter.sql 開頭）。
    if profile["allergies"]:
        recipes = ""
    else:
        recipes = get_recipe_candidates(profile)

    payload = {
        "topic": req.get("topic") or "閒聊",
        "userMessage": req.get("userMessage", ""),
        "model": WORKER_MODEL,
        "summary": summary,
        "recipes": recipes,
        "games": games,
        "profile": {
            "displayName": profile["displayName"],
            "allergies": profile["allergies"],
            "chronicConditions": profile["chronicConditions"],
            "isOnMedication": bool(profile.get("is_on_medication")),
        },
        "lastUserMessage": req.get("lastUserMessage", ""),
        "lastReply": req.get("lastReply", ""),
        "history": req.get("history", []),
        "wantFact": req.get("wantFact", False),
        "toldFacts": req.get("toldFacts", ""),
        "lastFactId": req.get("lastFactId", ""),
    }

    return call_worker(payload)
