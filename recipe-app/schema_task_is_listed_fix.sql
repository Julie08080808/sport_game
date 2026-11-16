-- ============================================================
-- 修正：咪兔「抬手挑戰」一直顯示「目前沒有可接取的任務」（2026-11-16）
--
-- 原因：MITU_HAND_RAISE_001 的 is_listed 被設成 FALSE（NPC 不主動發放），
--       而咪兔另一個任務 FARM_MAIN_GRIP_001 已停用，所以咪兔沒有任何任務可發。
--       管理後台原本沒有 is_listed 欄位，所以從畫面上看不出來；
--       現在任務編輯頁多了「NPC 主動發放」勾選框，任務列表也會標示「⚠ NPC 不發放」。
--
-- 可以重複執行。執行方式（範例）：psql -U postgres -d sport -f schema_task_is_listed_fix.sql
-- ============================================================

BEGIN;

-- 舊資料庫可能還沒有這個欄位；新增時預設為 TRUE（NPC 會發放）
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_listed BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE tasks SET is_listed = TRUE
WHERE task_key = 'MITU_HAND_RAISE_001' AND is_listed = FALSE;

-- 執行後檢查：列出所有「啟用中但 NPC 不發放」的任務，確認都是刻意的
SELECT task_id, task_key, task_name
FROM tasks
WHERE is_active AND NOT is_listed;

COMMIT;
