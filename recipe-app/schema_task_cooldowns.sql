-- ============================================================
-- 任務冷卻（2026-11-20）
--
-- 沒做完的任務不再保留進度（沒有「我的任務」資料夾續做），放棄後依放棄的地方冷卻一段時間，
-- 冷卻結束才會回到 NPC 可以抽的任務裡：
--   declined          一開始就拒絕             1 分鐘
--   preparation_exit  在準備／暖身畫面放棄      1 分鐘
--   exercise_exit     在運動畫面中途離開        30 分鐘（會出現在日曆）
--   challenge_timeout 限時挑戰時間到沒達標      30 分鐘（會出現在日曆）
-- 冷卻時間寫在後端程式（models/npc_model.py 的 COOLDOWN_MINUTES）。
--
-- 可以重複執行。執行方式（範例）：psql -U postgres -d sport -f schema_task_cooldowns.sql
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS user_task_cooldowns (
    user_id        INTEGER     NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    task_id        INTEGER     NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    cooldown_until TIMESTAMPTZ NOT NULL,
    reason         VARCHAR(30) NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, task_id)
);

COMMENT ON TABLE user_task_cooldowns IS '任務放棄／拒絕後的冷卻：cooldown_until 之前 NPC 不會再發這個任務給這位玩家';

COMMIT;
