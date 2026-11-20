-- 行動能力三個等級 + 森林（山林猴）的替代任務（2026-11-20）
--
-- 個人檔案「行動」改成三個選項（存在 user_accessibility_profiles）：
--   方便           allow_standing_exercise = true , allow_leg_exercise = true , is_mobility_limited = false
--   不能久站       allow_standing_exercise = false, allow_leg_exercise = true , is_mobility_limited = true
--   腳不方便動     allow_standing_exercise = false, allow_leg_exercise = false, is_mobility_limited = true
--
-- NPC 派任務時：
--   - 不能久站 → 不派 requires_standing 的任務
--   - 腳不方便動 → 不派 requires_standing 或 requires_leg_movement 的任務
--   - tasks.mobility_audience 不是 'all' 的任務，只派給那個等級的人（替代任務，一般玩家不會抽到）
--
-- 森林原本只有要站著用腳的任務（踏步、散步、踢椰子），所以補上：
--   不能久站   → 坐著踏步推椰子、坐著踏步清小路（踏步 STEP，坐著原地踏步，示範影片「坐腳踏步」）
--   腳不方便動 → 伸手摘松果（抬手）、拉藤蔓過小溪（二頭彎舉）——都用手機，不用感測球
-- （第一版的坐姿任務是「坐著踢」MONKEY_SEATED_KICK_00x，執行這個檔案會自動改成坐著踏步，task_id 不變）
--
-- 可重複執行（已存在就略過），不會刪資料。
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_mobility_levels.sql

BEGIN;

-- ───────────── 1. 任務的適用對象 ─────────────
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS mobility_audience VARCHAR(16) NOT NULL DEFAULT 'all';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_tasks_mobility_audience') THEN
        ALTER TABLE tasks ADD CONSTRAINT chk_tasks_mobility_audience
            CHECK (mobility_audience IN ('all', 'no_standing', 'no_legs'));
    END IF;
END $$;

-- ───────────── 2. 舊資料：只有 is_mobility_limited = true 的，視為「腳不方便動」 ─────────────
-- （之前的版本只有「方便／不太方便」兩個選項，「不太方便」的意思是只做手部運動）
UPDATE user_accessibility_profiles
SET allow_standing_exercise = FALSE,
    allow_leg_exercise = FALSE,
    updated_at = CURRENT_TIMESTAMP
WHERE is_mobility_limited
  AND allow_standing_exercise
  AND allow_leg_exercise;

-- ───────────── 3. 森林的替代任務 ─────────────
-- tasks.task_id、task_story_steps.story_step_id 沒有自動編號，用目前最大值 +1。
DO $$
DECLARE
    monkey_npc  CONSTANT INTEGER := 6;   -- 山林猴
    forest      CONSTANT INTEGER := 3;   -- 森林
    t RECORD;
    new_id INTEGER;
    step_id INTEGER;
    i INTEGER;
BEGIN
    FOR t IN
        SELECT * FROM (VALUES
            -- task_key, 舊 task_key（要轉換的舊版任務）, 名稱, 說明, 對象, 運動 id, exercise_type, 部位, 要動腳, 次數, 劇情（6 句）
            ('MONKEY_SEATED_STEP_001', 'MONKEY_SEATED_KICK_001', '坐著踏步推椰子',
             '坐在椅子上，和山林猴一起原地踏步，把路邊的 10 顆椰子推開。',
             'no_standing', 5, 'Step', 'leg', TRUE, 10,
             ARRAY['哎呀～路邊掉了好多椰子！我們坐著也能幫忙喔。',
                   '先坐穩在椅子上，把手機固定好，坐著原地慢慢踏步，每踏一下就推開一顆椰子，一起推開 10 顆吧！',
                   '踏得好！椰子滾到旁邊去囉～',
                   '剩最後幾顆，記得坐穩、慢慢來！',
                   '椰子都推開了！坐著也好厲害！',
                   '謝謝你幫忙開路，這是森林的小禮物！']),
            ('MONKEY_SEATED_STEP_002', 'MONKEY_SEATED_KICK_002', '坐著踏步清小路',
             '坐在椅子上，和山林猴一起原地踏步，把 15 顆椰子推回樹下。',
             'no_standing', 5, 'Step', 'leg', TRUE, 15,
             ARRAY['小路上又滾來一堆椰子，擋住大家回家的路了！',
                   '坐穩在椅子上，手機固定好，左右腳輪流踏步，把 15 顆椰子推回樹下吧！',
                   '好棒！椰子乖乖滾回樹下了～',
                   '小路快清出來了，累了可以先休息一下喔！',
                   '小路清乾淨了！大家都可以回家啦！',
                   '謝謝你幫大家清出小路，這是森林的小禮物！']),
            ('MONKEY_ARM_RAISE_001', NULL, '伸手摘松果',
             '和山林猴一起把手往上抬，從樹枝上摘下 10 顆松果。',
             'no_legs', 4, 'Raise', 'hand', FALSE, 10,
             ARRAY['嘿嘿～樹枝上掛著好多松果！',
                   '拿著手機，慢慢把手往上抬高再放下，每抬一次就摘下一顆，一起摘 10 顆吧！',
                   '伸手、放下～松果越摘越多囉！',
                   '再幾顆就滿籃了，加油！',
                   '哇！籃子都滿了！你的手好靈活！',
                   '這是森林的小禮物，謝謝你幫忙！']),
            ('MONKEY_BICEP_CURL_001', NULL, '拉藤蔓過小溪',
             '和山林猴一起做二頭彎舉，拉著藤蔓過小溪，一共拉 10 次。',
             'no_legs', 2, 'BicepCurl', 'hand', FALSE, 10,
             ARRAY['小溪對面有好吃的果子，可是要拉著藤蔓才過得去！',
                   '拿著手機，手肘貼著身體，把手往上彎再放下，每彎一次就把藤蔓拉近一點，一起拉 10 次吧！',
                   '拉得好！藤蔓越來越近了～',
                   '再幾下就過得去囉，加油！',
                   '過小溪了！你的手臂好有力氣！',
                   '謝謝你帶我過小溪，這是森林的小禮物！'])
        ) AS v(task_key, old_key, task_name, task_description, audience, exercise_id, exercise_type,
               body_part, uses_legs, target_count, lines)
    LOOP
        IF EXISTS (SELECT 1 FROM tasks WHERE task_key = t.task_key) THEN
            CONTINUE;
        END IF;

        -- 執行過第一版的資料庫：把舊任務原地改成新版（task_id 不變，玩家的進度紀錄保留）。
        IF t.old_key IS NOT NULL AND EXISTS (SELECT 1 FROM tasks WHERE task_key = t.old_key) THEN
            SELECT task_id INTO new_id FROM tasks WHERE task_key = t.old_key;
            UPDATE tasks SET
                task_key = t.task_key,
                task_name = t.task_name,
                task_description = t.task_description,
                exercise_id = t.exercise_id,
                exercise_type = t.exercise_type,
                exercise_body_part = t.body_part,
                requires_standing = FALSE,
                requires_leg_movement = t.uses_legs,
                target_count = t.target_count,
                mobility_audience = t.audience
            WHERE task_id = new_id;
            FOR i IN 1..6 LOOP
                UPDATE task_story_steps SET dialogue_text = t.lines[i]
                WHERE task_id = new_id AND story_variant = 'A' AND step_order = i;
            END LOOP;
            CONTINUE;
        END IF;

        SELECT COALESCE(MAX(task_id), 0) + 1 INTO new_id FROM tasks;
        INSERT INTO tasks (
            task_id, scene_id, task_name, task_description, task_mode,
            exercise_type, exercise_body_part, requires_standing, requires_leg_movement, is_mobility_friendly,
            goal_type, target_count, allow_pause, is_time_strict,
            reward_player_exp, reward_scene_exp, reward_money, difficulty, safety_level, is_active,
            task_key, task_type, task_category, recurrence_type, allow_resume, cross_mode_progress,
            expire_policy, required_player_level, is_initial_unlock, input_requirement, required_ball_count,
            exercise_id, task_kind, is_listed, mobility_audience)
        VALUES (
            new_id, forest, t.task_name, t.task_description, 'basic',
            t.exercise_type, t.body_part, FALSE, t.uses_legs, TRUE,
            'count', t.target_count, TRUE, FALSE,
            10, 1, 5, 'easy', 'low', TRUE,
            t.task_key, 'persistent', 'commission', 'none', TRUE, FALSE,
            'none', 1, TRUE, 'imu_required', 0,
            t.exercise_id, 'story', TRUE, t.audience);

        INSERT INTO npc_task_assignments (npc_id, task_id, priority, weight, is_active)
        VALUES (monkey_npc, new_id, 200, 1, TRUE)
        ON CONFLICT (npc_id, task_id) DO NOTHING;

        SELECT COALESCE(MAX(story_step_id), 0) INTO step_id FROM task_story_steps;
        FOR i IN 1..6 LOOP
            INSERT INTO task_story_steps (story_step_id, task_id, story_variant, step_order, story_phase,
                                          speaker_type, npc_id, dialogue_text)
            VALUES (step_id + i, new_id, 'A', i,
                    (ARRAY['intro', 'offer', 'partial', 'partial', 'completed', 'rewarded'])[i],
                    'npc', monkey_npc, t.lines[i]);
        END LOOP;
    END LOOP;
END $$;

COMMIT;
