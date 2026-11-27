"""照護中心後台的資料存取層。

跟 /admin（單一系統管理員帳號，管任務設計）完全分開：
- 照護者帳號存在 caregiver_accounts，一個照護中心可以有多個照護者帳號。
- 老人（users）用 users.care_center_id 歸屬到一個照護中心；同中心的照護者
  可以看到中心內所有老人（歸屬模型：中心層級，不是指派到個別照護者）。
- 每一個查詢都要帶 care_center_id 做範圍限制，避免跨中心看到別人的資料。

運動分類（互斥三類 + 全身，跟 exercise_definitions 對應）：
  球（ball）：input_type = 'ball_pressure'（不分手腳，壓力球動作都算這類）
  手（hand）：exercise_category = 'hand' 且不是壓力球
  腳（leg） ：exercise_category = 'leg'  且不是壓力球
  全身（full_body）：其餘（目前只有 FULL_BODY_WALK）
"""
from config.database import get_db_conn, db_transaction
from psycopg2.extras import RealDictCursor

from services.password_hashing import hash_password, verify_password

VALID_CATEGORIES = ("hand", "leg", "ball", "full_body")

_BUCKET_CASE_SQL = """
    CASE
        WHEN ed.input_type = 'ball_pressure' THEN 'ball'
        WHEN ed.exercise_category = 'hand' THEN 'hand'
        WHEN ed.exercise_category = 'leg' THEN 'leg'
        ELSE 'full_body'
    END
"""


def _fetchall(cur):
    return [dict(r) for r in cur.fetchall()]


# ───────────────────────── 照護者登入 ─────────────────────────

def authenticate_caregiver(username: str, password: str):
    """帳密正確且帳號啟用中才回傳資料；否則回傳 None。"""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT c.caregiver_id, c.care_center_id, c.username, c.display_name,
                       c.password_hash, c.is_active, ctr.center_name
                FROM caregiver_accounts c
                JOIN care_centers ctr ON ctr.care_center_id = c.care_center_id
                WHERE c.username = %s AND ctr.is_active = TRUE;
            """, (username.strip(),))
            row = cur.fetchone()
            if not row or not row["is_active"] or not verify_password(password, row["password_hash"]):
                return None
            return {
                "caregiver_id": row["caregiver_id"],
                "care_center_id": row["care_center_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "center_name": row["center_name"],
            }
    finally:
        conn.close()


def get_caregiver_for_session(caregiver_id: int):
    """驗證 session cookie 時用：重新查目前的密碼雜湊/啟用狀態/所屬中心。
    改密碼、停用帳號、或換照護中心後，舊 session 都會立刻失效。"""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT c.caregiver_id, c.care_center_id, c.username, c.display_name,
                       c.password_hash, c.is_active, ctr.center_name
                FROM caregiver_accounts c
                JOIN care_centers ctr ON ctr.care_center_id = c.care_center_id
                WHERE c.caregiver_id = %s AND ctr.is_active = TRUE;
            """, (caregiver_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


# ───────────────────────── 中心總覽 ─────────────────────────

def get_dashboard_stats(care_center_id: int):
    """中心首頁的大數據：平均每日/每週完成次數、平均運動天數(週/月)。

    - 平均每日/每週：最近 7 天，中心所有老人的完成次數總和，
      平均每日 = 總和 / 7 / 人數；平均每週 = 總和 / 人數。
    - 平均運動天數：最近 7 天 / 最近 30 天內，平均每位老人「有完成運動」的天數。
    """
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM users WHERE care_center_id = %s;",
                (care_center_id,),
            )
            resident_count = cur.fetchone()["n"]

            if resident_count == 0:
                return {
                    "resident_count": 0,
                    "avg_per_day": 0, "avg_per_week": 0,
                    "avg_days_active_week": 0, "avg_days_active_month": 0,
                }

            cur.execute("""
                SELECT COUNT(*) AS n
                FROM exercise_sessions s
                JOIN users u ON u.user_id = s.user_id
                WHERE u.care_center_id = %s
                  AND s.status = 'completed'
                  AND s.ended_at >= CURRENT_DATE - INTERVAL '6 days';
            """, (care_center_id,))
            week_total = cur.fetchone()["n"]

            # 用 LEFT JOIN 從「中心全部老人」出發，完全沒運動的人要算進分母當 0 天，
            # 不能只對「有運動的人」取平均（那樣會把數字墊高，失去代表性）。
            cur.execute("""
                SELECT AVG(COALESCE(days, 0)) AS avg_days
                FROM users u
                LEFT JOIN (
                    SELECT s.user_id, COUNT(DISTINCT s.ended_at::date) AS days
                    FROM exercise_sessions s
                    WHERE s.status = 'completed'
                      AND s.ended_at >= CURRENT_DATE - INTERVAL '6 days'
                    GROUP BY s.user_id
                ) t ON t.user_id = u.user_id
                WHERE u.care_center_id = %s;
            """, (care_center_id,))
            avg_days_week = cur.fetchone()["avg_days"] or 0

            cur.execute("""
                SELECT AVG(COALESCE(days, 0)) AS avg_days
                FROM users u
                LEFT JOIN (
                    SELECT s.user_id, COUNT(DISTINCT s.ended_at::date) AS days
                    FROM exercise_sessions s
                    WHERE s.status = 'completed'
                      AND s.ended_at >= CURRENT_DATE - INTERVAL '29 days'
                    GROUP BY s.user_id
                ) t ON t.user_id = u.user_id
                WHERE u.care_center_id = %s;
            """, (care_center_id,))
            avg_days_month = cur.fetchone()["avg_days"] or 0

            return {
                "resident_count": resident_count,
                "avg_per_day": round(week_total / 7 / resident_count, 1),
                "avg_per_week": round(week_total / resident_count, 1),
                "avg_days_active_week": round(float(avg_days_week), 1),
                "avg_days_active_month": round(float(avg_days_month), 1),
            }
    finally:
        conn.close()


def get_center_trend(care_center_id: int, days: int = 7):
    """中心總覽用：最近 N 天，中心全部老人每天的完成次數（依類型分）。"""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT
                    s.ended_at::date AS bucket_date,
                    {_BUCKET_CASE_SQL} AS bucket,
                    COUNT(*) AS cnt
                FROM exercise_sessions s
                JOIN exercise_definitions ed ON ed.exercise_id = s.exercise_id
                JOIN users u ON u.user_id = s.user_id
                WHERE u.care_center_id = %s
                  AND s.status = 'completed'
                  AND s.ended_at >= CURRENT_DATE - ({days} - 1)
                GROUP BY bucket_date, bucket
                ORDER BY bucket_date;
            """, (care_center_id,))
            rows = _fetchall(cur)
    finally:
        conn.close()

    points: dict[str, dict] = {}
    for r in rows:
        key = r["bucket_date"].isoformat()
        points.setdefault(key, {"date": key, "hand": 0, "leg": 0, "ball": 0, "full_body": 0})
        points[key][r["bucket"]] = r["cnt"]
    return sorted(points.values(), key=lambda p: p["date"])


# ───────────────────────── 老人名單 ─────────────────────────

def list_residents(care_center_id: int, categories: list[str] | None, sort: str = "desc"):
    """中心內所有老人，附上手/腳/球/全身各自完成次數，以及（依篩選分類加總的）total 供排序。

    categories 為 None 或空 list 時，total 用全部分類加總；
    有指定時，total 只加總被選到的分類（可單選或複選）。
    """
    order = "DESC" if sort != "asc" else "ASC"
    selected = list(dict.fromkeys(c for c in (categories or []) if c in VALID_CATEGORIES))

    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                WITH per_bucket AS (
                    SELECT
                        s.user_id,
                        {_BUCKET_CASE_SQL} AS bucket,
                        COUNT(*) AS cnt
                    FROM exercise_sessions s
                    JOIN exercise_definitions ed ON ed.exercise_id = s.exercise_id
                    WHERE s.status = 'completed'
                    GROUP BY s.user_id, bucket
                ),
                pivot AS (
                    SELECT
                        user_id,
                        COALESCE(SUM(cnt) FILTER (WHERE bucket = 'hand'), 0) AS hand_count,
                        COALESCE(SUM(cnt) FILTER (WHERE bucket = 'leg'), 0) AS leg_count,
                        COALESCE(SUM(cnt) FILTER (WHERE bucket = 'ball'), 0) AS ball_count,
                        COALESCE(SUM(cnt) FILTER (WHERE bucket = 'full_body'), 0) AS full_body_count
                    FROM per_bucket
                    GROUP BY user_id
                )
                SELECT
                    u.user_id, u.username,
                    COALESCE(p.hand_count, 0) AS hand_count,
                    COALESCE(p.leg_count, 0) AS leg_count,
                    COALESCE(p.ball_count, 0) AS ball_count,
                    COALESCE(p.full_body_count, 0) AS full_body_count,
                    (SELECT MAX(s.ended_at)::date FROM exercise_sessions s
                     WHERE s.user_id = u.user_id AND s.status = 'completed') AS last_completed_date
                FROM users u
                LEFT JOIN pivot p ON p.user_id = u.user_id
                WHERE u.care_center_id = %s
                ORDER BY u.username;
            """, (care_center_id,))
            rows = _fetchall(cur)
    finally:
        conn.close()

    buckets = selected if selected else list(VALID_CATEGORIES)
    for r in rows:
        r["total_count"] = sum(r[f"{b}_count"] for b in buckets)

    rows.sort(key=lambda r: r["total_count"], reverse=(order == "DESC"))
    return rows


# ───────────────────────── 個人詳細頁 ─────────────────────────

def resident_belongs_to_center(user_id: int, care_center_id: int) -> bool:
    """每次開個人頁前都要先檢查，避免照護者改網址猜到別的中心的 user_id。"""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT 1 FROM users WHERE user_id = %s AND care_center_id = %s;",
                (user_id, care_center_id),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


_RANGE_SQL = {
    # (interval, date_trunc 的粒度) — 以資料庫時區的日曆日/月為準，含今天/本月。
    "week": ("6 days", "day"),
    "month": ("29 days", "day"),
    "year": ("11 months", "month"),
}


def get_resident_overview(user_id: int):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT user_id, username FROM users WHERE user_id = %s;", (user_id,))
            return cur.fetchone()
    finally:
        conn.close()


def get_resident_trend(user_id: int, range_key: str):
    """個人頁的運動次數趨勢：week=最近7天(每日)、month=最近30天(每日)、year=最近12個月(每月)。"""
    interval, granularity = _RANGE_SQL.get(range_key, _RANGE_SQL["week"])

    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT
                    date_trunc('{granularity}', s.ended_at)::date AS bucket_date,
                    {_BUCKET_CASE_SQL} AS bucket,
                    COUNT(*) AS cnt
                FROM exercise_sessions s
                JOIN exercise_definitions ed ON ed.exercise_id = s.exercise_id
                WHERE s.user_id = %s
                  AND s.status = 'completed'
                  AND s.ended_at >= date_trunc('{granularity}', CURRENT_DATE) - INTERVAL '{interval}'
                GROUP BY bucket_date, bucket
                ORDER BY bucket_date;
            """, (user_id,))
            rows = _fetchall(cur)
    finally:
        conn.close()

    points: dict[str, dict] = {}
    for r in rows:
        key = r["bucket_date"].isoformat()
        points.setdefault(key, {"date": key, "hand": 0, "leg": 0, "ball": 0, "full_body": 0})
        points[key][r["bucket"]] = r["cnt"]
    return sorted(points.values(), key=lambda p: p["date"])


def get_resident_exercise_breakdown(user_id: int, range_key: str):
    """個人頁圓餅圖用：依分類(手/腳/球/全身)分組，並附上該分類底下每個運動項目各自的完成次數。

    例如 bucket='hand' 底下會有 [{'exercise_name': '二頭彎舉', 'count': 30}, {'exercise_name': '抬手', 'count': 50}, ...]。
    """
    interval, granularity = _RANGE_SQL.get(range_key, _RANGE_SQL["week"])

    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"""
                SELECT
                    {_BUCKET_CASE_SQL} AS bucket,
                    ed.exercise_name,
                    COUNT(*) AS cnt
                FROM exercise_sessions s
                JOIN exercise_definitions ed ON ed.exercise_id = s.exercise_id
                WHERE s.user_id = %s
                  AND s.status = 'completed'
                  AND s.ended_at >= date_trunc('{granularity}', CURRENT_DATE) - INTERVAL '{interval}'
                GROUP BY bucket, ed.exercise_name
                ORDER BY bucket, cnt DESC;
            """, (user_id,))
            rows = _fetchall(cur)
    finally:
        conn.close()

    buckets: dict[str, dict] = {b: {"bucket": b, "total": 0, "items": []} for b in VALID_CATEGORIES}
    for r in rows:
        b = buckets[r["bucket"]]
        b["total"] += r["cnt"]
        b["items"].append({"exercise_name": r["exercise_name"], "count": r["cnt"]})
    return buckets


def get_resident_diet_trend(user_id: int, weeks: int = 12):
    """個人頁的飲食週報趨勢（蔬菜/油炸/多樣性星等），預設取最近 12 週。"""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT week_monday, vegetable_score, fried_score, variety_score, ai_observation
                FROM user_weekly_diet_reviews
                WHERE user_id = %s
                ORDER BY week_monday DESC
                LIMIT %s;
            """, (user_id, weeks))
            rows = _fetchall(cur)
    finally:
        conn.close()
    rows.reverse()
    for r in rows:
        r["week_monday"] = r["week_monday"].isoformat()
    return rows


# ───────────────────────── /admin 端：中心與照護者帳號管理 ─────────────────────────

def list_care_centers():
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT ctr.care_center_id, ctr.center_name, ctr.center_code, ctr.is_active,
                       COUNT(u.user_id) AS resident_count
                FROM care_centers ctr
                LEFT JOIN users u ON u.care_center_id = ctr.care_center_id
                GROUP BY ctr.care_center_id
                ORDER BY ctr.center_name;
            """)
            return _fetchall(cur)
    finally:
        conn.close()


def create_care_center(center_name: str, center_code: str):
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO care_centers (center_name, center_code)
                VALUES (%s, %s) RETURNING care_center_id;
            """, (center_name.strip(), center_code.strip()))
            return cur.fetchone()["care_center_id"]


def get_care_center(care_center_id: int):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM care_centers WHERE care_center_id = %s;", (care_center_id,)
            )
            return cur.fetchone()
    finally:
        conn.close()


def list_caregivers(care_center_id: int):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT caregiver_id, username, display_name, is_active, created_at
                FROM caregiver_accounts
                WHERE care_center_id = %s
                ORDER BY username;
            """, (care_center_id,))
            return _fetchall(cur)
    finally:
        conn.close()


def create_caregiver(care_center_id: int, username: str, password: str, display_name: str):
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO caregiver_accounts
                    (care_center_id, username, password_hash, display_name)
                VALUES (%s, %s, %s, %s) RETURNING caregiver_id;
            """, (care_center_id, username.strip(), hash_password(password), display_name.strip()))
            return cur.fetchone()["caregiver_id"]


def set_caregiver_active(caregiver_id: int, is_active: bool):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE caregiver_accounts SET is_active = %s, updated_at = CURRENT_TIMESTAMP "
                "WHERE caregiver_id = %s;",
                (is_active, caregiver_id),
            )


def list_users_with_center():
    """/admin 指派畫面用：所有玩家帳號目前歸屬哪個中心（未指派則是 None）。"""
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT u.user_id, u.username, u.care_center_id, ctr.center_name
                FROM users u
                LEFT JOIN care_centers ctr ON ctr.care_center_id = u.care_center_id
                ORDER BY ctr.center_name NULLS FIRST, u.username;
            """)
            return _fetchall(cur)
    finally:
        conn.close()


def assign_user_to_center(user_id: int, care_center_id: int | None):
    """care_center_id 傳 None 代表取消指派。"""
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET care_center_id = %s WHERE user_id = %s;",
                (care_center_id, user_id),
            )
