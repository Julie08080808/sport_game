-- 限時挑戰任務的「超標加成」門檻。
-- time_limit_seconds 在建 tasks 表時就已經補上，但 bonus_target_count 這欄漏加，
-- 導致 models/exercise_model.py、models/npc_model.py、services/reward_service.py
-- 裡引用這欄的查詢全部炸掉（UndefinedColumn）。
-- 語意：progress_count 達到這個門檻就視為超標，reward_service.reward_task
-- 會把實際入帳的經驗值翻倍。沒有限時加成的任務留 NULL 即可。
--
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_tasks_bonus_target_count.sql

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS bonus_target_count INTEGER;
