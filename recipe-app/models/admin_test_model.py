from config.database import get_db_conn
from psycopg2.extras import RealDictCursor


def restart_task_for_testing(user_id: int, task_id: int, reason: str = "manual dev replay"):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT user_id, username FROM users WHERE user_id = %s;",
                (user_id,),
            )
            user = cur.fetchone()
            if not user:
                return {"success": False, "message": "找不到此使用者"}

            cur.execute(
                '''
                SELECT task_id, task_key, task_name, recurrence_type, is_active
                FROM tasks
                WHERE task_id = %s;
                ''',
                (task_id,),
            )
            task = cur.fetchone()
            if not task:
                return {"success": False, "message": "找不到此任務"}

            # 保留歷史，只把目前仍可恢復中的 attempt 結束成 cancelled。
            cur.execute(
                '''
                UPDATE user_task_progress
                SET status = 'cancelled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND task_id = %s
                  AND status IN ('accepted', 'in_progress', 'interrupted')
                RETURNING progress_id;
                ''',
                (user_id, task_id),
            )
            cancelled = cur.fetchall()

            # 同一 user/task 同時只保留一張未使用 permit。
            cur.execute(
                '''
                SELECT replay_id
                FROM user_task_test_replays
                WHERE user_id = %s
                  AND task_id = %s
                  AND used_at IS NULL
                ORDER BY replay_id DESC
                LIMIT 1;
                ''',
                (user_id, task_id),
            )
            existing = cur.fetchone()

            if existing:
                replay_id = existing["replay_id"]
            else:
                cur.execute(
                    '''
                    INSERT INTO user_task_test_replays
                        (user_id, task_id, reason, created_by)
                    VALUES (%s, %s, %s, 'dev_admin')
                    RETURNING replay_id;
                    ''',
                    (user_id, task_id, reason),
                )
                replay_id = cur.fetchone()["replay_id"]

            conn.commit()

            return {
                "success": True,
                "message": "已重新開放此任務供開發測試",
                "user_id": user["user_id"],
                "username": user["username"],
                "task_id": task["task_id"],
                "task_key": task["task_key"],
                "task_name": task["task_name"],
                "recurrence_type": task["recurrence_type"],
                "cancelled_progress_ids": [r["progress_id"] for r in cancelled],
                "replay_id": replay_id,
                "replay_pending": True,
            }

    except Exception as e:
        conn.rollback()
        print(f"[Admin Test Model Error] restart task: {e}")
        return {"success": False, "message": f"重新開放測試任務失敗: {e}"}
    finally:
        conn.close()


def get_task_test_status(user_id: int, task_id: int):
    conn = get_db_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT
                    t.task_id,
                    t.task_key,
                    t.task_name,
                    t.recurrence_type,
                    r.replay_id,
                    r.reason,
                    r.created_at AS replay_created_at,
                    r.used_at,
                    r.used_progress_id
                FROM tasks t
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM user_task_test_replays x
                    WHERE x.user_id = %s
                      AND x.task_id = t.task_id
                    ORDER BY x.replay_id DESC
                    LIMIT 1
                ) r ON TRUE
                WHERE t.task_id = %s;
                ''',
                (user_id, task_id),
            )
            task = cur.fetchone()
            if not task:
                return {"success": False, "message": "找不到此任務"}

            cur.execute(
                '''
                SELECT progress_id, status, progress_count, target_count,
                       progress_seconds, target_seconds, accepted_at,
                       completed_at, rewarded_at, updated_at
                FROM user_task_progress
                WHERE user_id = %s
                  AND task_id = %s
                ORDER BY progress_id DESC;
                ''',
                (user_id, task_id),
            )
            history = cur.fetchall()

            return {
                "success": True,
                "user_id": user_id,
                "task": dict(task),
                "pending_replay": (
                    task["replay_id"] is not None and task["used_at"] is None
                ),
                "progress_history": [dict(row) for row in history],
            }

    except Exception as e:
        print(f"[Admin Test Model Error] status: {e}")
        return {"success": False, "message": f"讀取測試狀態失敗: {e}"}
    finally:
        conn.close()
