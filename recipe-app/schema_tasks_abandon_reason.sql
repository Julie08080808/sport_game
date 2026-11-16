-- /api/tasks/folder 和 /api/tasks/abandon 都會讀寫 user_task_progress.abandon_reason，
-- 但這張表從來沒有這一欄，一查就是 UndefinedColumn（Unity 看到的「任務資料夾讀取失敗」就是這個）。
-- 值對應 controllers/task_controller.py 的 ABANDON_REASONS = {'manual','challenge_timeout'}。
--
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_tasks_abandon_reason.sql

ALTER TABLE user_task_progress ADD COLUMN IF NOT EXISTS abandon_reason VARCHAR(30);
