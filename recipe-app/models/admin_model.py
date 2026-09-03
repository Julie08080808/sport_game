from config.database import get_db_conn
from psycopg2.extras import RealDictCursor


def _fetchall(cur):
    return [dict(r) for r in cur.fetchall()]


def get_dashboard_stats():
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS count FROM tasks;")
            task_count = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM users;")
            user_count = cur.fetchone()["count"]

            cur.execute("""
                SELECT COUNT(*) AS count
                FROM user_task_progress
                WHERE status IN ('accepted', 'in_progress', 'interrupted');
            """)
            active_progress_count = cur.fetchone()["count"]

            cur.execute("""
                SELECT COUNT(*) AS count
                FROM user_task_progress
                WHERE status IN ('completed', 'claimable', 'rewarded');
            """)
            completed_progress_count = cur.fetchone()["count"]

            cur.execute("""
                SELECT
                    p.progress_id,
                    p.user_id,
                    u.username,
                    p.task_id,
                    t.task_name,
                    p.status,
                    p.updated_at
                FROM user_task_progress p
                JOIN users u ON u.user_id = p.user_id
                JOIN tasks t ON t.task_id = p.task_id
                ORDER BY p.updated_at DESC NULLS LAST, p.progress_id DESC
                LIMIT 8;
            """)
            recent_progress = _fetchall(cur)

            return {
                "task_count": task_count,
                "user_count": user_count,
                "active_progress_count": active_progress_count,
                "completed_progress_count": completed_progress_count,
                "recent_progress": recent_progress,
            }
    finally:
        conn.close()


def list_tasks(keyword: str = ""):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where = ""
            params = ()
            if keyword:
                like = f"%{keyword}%"
                where = """
                    WHERE t.task_name ILIKE %s
                       OR t.task_key ILIKE %s
                       OR COALESCE(t.exercise_type, '') ILIKE %s
                """
                params = (like, like, like)

            cur.execute(f"""
                SELECT
                    t.task_id,
                    t.task_key,
                    t.task_name,
                    t.task_category,
                    t.task_type,
                    t.task_mode,
                    t.exercise_type,
                    t.goal_type,
                    t.target_count,
                    t.target_seconds,
                    t.input_requirement,
                    t.required_ball_count,
                    t.recurrence_type,
                    t.reward_player_exp,
                    t.reward_scene_exp,
                    t.reward_money,
                    t.scene_id,
                    s.scene_name,
                    t.is_initial_unlock,
                    t.is_active,
                    n.npc_id,
                    n.npc_name
                FROM tasks t
                LEFT JOIN scenes s ON s.scene_id = t.scene_id
                LEFT JOIN LATERAL (
                    SELECT n.npc_id, n.npc_name
                    FROM npc_task_assignments a
                    JOIN npcs n ON n.npc_id = a.npc_id
                    WHERE a.task_id = t.task_id
                      AND a.is_active = TRUE
                    ORDER BY a.priority DESC, a.npc_id
                    LIMIT 1
                ) n ON TRUE
                {where}
                ORDER BY t.task_id DESC;
            """, params)
            return _fetchall(cur)
    finally:
        conn.close()


def get_task_form_options():
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT scene_id, scene_key, scene_name FROM scenes ORDER BY scene_id;")
            scenes = _fetchall(cur)

            cur.execute("""
                SELECT npc_id, npc_key, npc_name, scene_id
                FROM npcs
                WHERE is_active = TRUE
                ORDER BY scene_id, npc_id;
            """)
            npcs = _fetchall(cur)
            return {"scenes": scenes, "npcs": npcs}
    finally:
        conn.close()


def get_task(task_id: int):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tasks WHERE task_id = %s;", (task_id,))
            task = cur.fetchone()
            if not task:
                return None
            task = dict(task)

            cur.execute("""
                SELECT npc_id
                FROM npc_task_assignments
                WHERE task_id = %s
                  AND is_active = TRUE
                ORDER BY priority DESC, npc_id
                LIMIT 1;
            """, (task_id,))
            assignment = cur.fetchone()
            task["npc_id"] = assignment["npc_id"] if assignment else None
            return task
    finally:
        conn.close()


def _backfill_initial_unlocks(cur, task_id: int):
    cur.execute("""
        INSERT INTO user_task_unlocks (user_id, task_id, unlocked_at)
        SELECT u.user_id, %s, CURRENT_TIMESTAMP
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1
            FROM user_task_unlocks x
            WHERE x.user_id = u.user_id
              AND x.task_id = %s
        );
    """, (task_id, task_id))


def _set_npc_assignment(cur, task_id: int, npc_id):
    cur.execute("""
        UPDATE npc_task_assignments
        SET is_active = FALSE
        WHERE task_id = %s;
    """, (task_id,))

    if npc_id is None:
        return

    # npc_task_assignments 沒有 assignment_id。
    # 這張表的主鍵是 (npc_id, task_id)，因此直接用複合主鍵 UPSERT。
    cur.execute("""
        INSERT INTO npc_task_assignments
            (npc_id, task_id, priority, weight, is_active)
        VALUES (%s, %s, 100, 1, TRUE)
        ON CONFLICT (npc_id, task_id)
        DO UPDATE SET
            priority = EXCLUDED.priority,
            weight = EXCLUDED.weight,
            is_active = TRUE;
    """, (npc_id, task_id))


def create_task(data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO tasks (
                    task_key, task_name, task_description,
                    task_category, task_type, task_mode,
                    scene_id, exercise_type, goal_type,
                    target_count, target_seconds,
                    input_requirement, required_ball_count,
                    recurrence_type, allow_pause, allow_resume,
                    reward_player_exp, reward_scene_exp, reward_money,
                    required_player_level, expire_policy, expire_after_seconds,
                    is_initial_unlock, is_active
                )
                VALUES (
                    %(task_key)s, %(task_name)s, %(task_description)s,
                    %(task_category)s, %(task_type)s, %(task_mode)s,
                    %(scene_id)s, %(exercise_type)s, %(goal_type)s,
                    %(target_count)s, %(target_seconds)s,
                    %(input_requirement)s, %(required_ball_count)s,
                    %(recurrence_type)s, %(allow_pause)s, %(allow_resume)s,
                    %(reward_player_exp)s, %(reward_scene_exp)s, %(reward_money)s,
                    %(required_player_level)s, %(expire_policy)s, %(expire_after_seconds)s,
                    %(is_initial_unlock)s, %(is_active)s
                )
                RETURNING task_id;
            """, data)
            task_id = cur.fetchone()["task_id"]
            _set_npc_assignment(cur, task_id, data.get("npc_id"))
            if data.get("is_initial_unlock"):
                _backfill_initial_unlocks(cur, task_id)
            conn.commit()
            return task_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_task(task_id: int, data: dict):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE tasks
                SET
                    task_key = %(task_key)s,
                    task_name = %(task_name)s,
                    task_description = %(task_description)s,
                    task_category = %(task_category)s,
                    task_type = %(task_type)s,
                    task_mode = %(task_mode)s,
                    scene_id = %(scene_id)s,
                    exercise_type = %(exercise_type)s,
                    goal_type = %(goal_type)s,
                    target_count = %(target_count)s,
                    target_seconds = %(target_seconds)s,
                    input_requirement = %(input_requirement)s,
                    required_ball_count = %(required_ball_count)s,
                    recurrence_type = %(recurrence_type)s,
                    allow_pause = %(allow_pause)s,
                    allow_resume = %(allow_resume)s,
                    reward_player_exp = %(reward_player_exp)s,
                    reward_scene_exp = %(reward_scene_exp)s,
                    reward_money = %(reward_money)s,
                    required_player_level = %(required_player_level)s,
                    expire_policy = %(expire_policy)s,
                    expire_after_seconds = %(expire_after_seconds)s,
                    is_initial_unlock = %(is_initial_unlock)s,
                    is_active = %(is_active)s
                WHERE task_id = %(task_id)s;
            """, {**data, "task_id": task_id})
            _set_npc_assignment(cur, task_id, data.get("npc_id"))
            if data.get("is_initial_unlock"):
                _backfill_initial_unlocks(cur, task_id)
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def toggle_task(task_id: int):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET is_active = NOT is_active WHERE task_id = %s;", (task_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_users(keyword: str = ""):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where = ""
            params = ()
            if keyword:
                like = f"%{keyword}%"
                where = "WHERE u.username ILIKE %s OR CAST(u.user_id AS TEXT) ILIKE %s"
                params = (like, like)

            cur.execute(f"""
                SELECT
                    u.user_id,
                    u.username,
                    s.player_level,
                    s.player_exp,
                    s.money,
                    COUNT(p.progress_id) AS task_attempts,
                    COUNT(*) FILTER (
                        WHERE p.status IN ('completed', 'claimable', 'rewarded')
                    ) AS completed_tasks
                FROM users u
                LEFT JOIN user_stats s ON s.user_id = u.user_id
                LEFT JOIN user_task_progress p ON p.user_id = u.user_id
                {where}
                GROUP BY u.user_id, u.username, s.player_level, s.player_exp, s.money
                ORDER BY u.user_id DESC;
            """, params)
            return _fetchall(cur)
    finally:
        conn.close()


def get_user_detail(user_id: int):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT u.user_id, u.username, s.player_level, s.player_exp, s.money
                FROM users u
                LEFT JOIN user_stats s ON s.user_id = u.user_id
                WHERE u.user_id = %s;
            """, (user_id,))
            user = cur.fetchone()
            if not user:
                return None

            cur.execute("""
                SELECT us.scene_id, sc.scene_name, us.scene_level, us.scene_exp
                FROM user_scenes us
                JOIN scenes sc ON sc.scene_id = us.scene_id
                WHERE us.user_id = %s
                ORDER BY us.scene_id;
            """, (user_id,))
            scenes = _fetchall(cur)

            cur.execute("""
                SELECT
                    p.progress_id,
                    p.task_id,
                    t.task_key,
                    t.task_name,
                    t.recurrence_type,
                    p.status,
                    p.progress_count,
                    p.target_count,
                    p.progress_seconds,
                    p.target_seconds,
                    p.accepted_at,
                    p.completed_at,
                    p.rewarded_at,
                    p.updated_at
                FROM user_task_progress p
                JOIN tasks t ON t.task_id = p.task_id
                WHERE p.user_id = %s
                ORDER BY p.progress_id DESC
                LIMIT 100;
            """, (user_id,))
            progress = _fetchall(cur)

            return {"user": dict(user), "scenes": scenes, "progress": progress}
    finally:
        conn.close()
