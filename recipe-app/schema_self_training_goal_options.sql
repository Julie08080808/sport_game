-- ============================================================
-- 自主運動：每個運動可選的「時間／次數」選項（2026-11-17）
--
-- 自主運動清單（GET /api/npc/self_training/exercises）只列出有 exercise_goal_options 的運動。
-- 原本只有 抬手、踏步、手按壓，這裡補上 二頭彎舉、雙手按壓、踩球、踢腿。
--   計時：1／3／5 分鐘（預設 1 分鐘），可自訂 30 秒～10 分鐘、每次 ±30 秒
--   計次：5／10／20 次（預設 10 次），可自訂 1～100 次、每次 ±1
--   踏步一次很快，計次改成 10／20／30 次（預設 20 次）
-- 上下限必須符合後端 validate_goal：次數 1～100；秒數 30～600 且為 30 的倍數。
--
-- 可以重複執行。執行方式（範例）：psql -U postgres -d sport -f schema_self_training_goal_options.sql
-- ============================================================

BEGIN;

INSERT INTO exercise_goal_options
    (exercise_id, count_presets, default_count, min_count, max_count, count_step,
     seconds_presets, default_seconds, min_seconds, max_seconds, seconds_step)
SELECT e.exercise_id, ARRAY[5, 10, 20], 10, 1, 100, 1,
       ARRAY[60, 180, 300], 60, 30, 600, 30
FROM exercise_definitions e
WHERE e.exercise_key IN ('HAND_BICEP_CURL', 'HAND_DUAL_PRESS', 'LEG_BALL_PRESS', 'LEG_KICK')
ON CONFLICT (exercise_id) DO NOTHING;

-- 踏步：只在還是原本的預設值時才改，不覆蓋之後手動調整過的設定
UPDATE exercise_goal_options o
SET count_presets = ARRAY[10, 20, 30], default_count = 20
FROM exercise_definitions e
WHERE e.exercise_id = o.exercise_id AND e.exercise_key = 'LEG_STEP'
  AND o.count_presets = ARRAY[5, 10, 20] AND o.default_count = 10;

-- 執行後檢查：自主運動會列出的運動
SELECT e.exercise_key, e.exercise_name, o.seconds_presets, o.default_seconds,
       o.count_presets, o.default_count
FROM exercise_definitions e JOIN exercise_goal_options o USING (exercise_id)
WHERE e.is_active
ORDER BY e.exercise_id;

COMMIT;
