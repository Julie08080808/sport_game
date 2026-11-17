-- ============================================================
-- 山林猴「踢開路邊椰子」：新增踢腿運動＋計次／計時各一個任務（2026-11-17）
--
--   K1  運動定義 LEG_KICK（辨識 KICK、手機 IMU、腿部場景），以 LEG_STEP 為範本複製
--   K2  任務（以 MONKEY_STEP_001 為範本複製，指派給山林猴）
--       計次 MONKEY_KICK_001       踢開椰子      10 次
--       計時 MONKEY_KICK_TIME_001  清出椰子小路  60 秒
--   K3  台詞：intro、offer、partial×2、completed、rewarded
--
-- Unity 端：KickRecognitionService 已支援 KICK；運動畫面在 ExerciseLegScene 的
--   Exercise Frame Sets 加一組 Recognition Key = KICK（Task Key 留空，兩個任務共用）。
-- 可以重複執行。執行方式（範例）：psql -U postgres -d sport -f schema_monkey_kick_tasks.sql
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- K1：運動定義 LEG_KICK
-- ------------------------------------------------------------
DO $$
DECLARE
    cols TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM exercise_definitions WHERE exercise_key = 'LEG_KICK') THEN
        UPDATE exercise_definitions SET is_active = TRUE WHERE exercise_key = 'LEG_KICK' AND NOT is_active;
        RAISE NOTICE '[K1] LEG_KICK 已存在，略過新增';
    ELSIF NOT EXISTS (SELECT 1 FROM exercise_definitions WHERE exercise_key = 'LEG_STEP') THEN
        RAISE EXCEPTION '[K1] 找不到範本 LEG_STEP';
    ELSE
        CREATE TEMP TABLE tmp_exercise ON COMMIT DROP AS
            SELECT * FROM exercise_definitions WHERE exercise_key = 'LEG_STEP' LIMIT 1;

        UPDATE tmp_exercise
        SET exercise_key = 'LEG_KICK',
            exercise_name = '踢腿',
            recognition_key = 'KICK',
            input_type = 'phone_imu',
            exercise_scene_key = 'leg',
            default_required_ball_count = 0,
            is_active = TRUE;

        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'exercise_definitions' AND column_name = 'description') THEN
            EXECUTE $q$UPDATE tmp_exercise SET description = '使用手機 IMU 辨識向前踢腿。'$q$;
        END IF;

        SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
        INTO cols
        FROM information_schema.columns
        WHERE table_name = 'exercise_definitions' AND table_schema = current_schema()
          AND column_name NOT IN ('exercise_id', 'created_at', 'updated_at');

        EXECUTE format('INSERT INTO exercise_definitions (%s) SELECT %s FROM tmp_exercise', cols, cols);
        RAISE NOTICE '[K1] 已新增 LEG_KICK';
    END IF;
END $$;

-- ------------------------------------------------------------
-- K2：任務
-- ------------------------------------------------------------
DO $$
DECLARE
    cols TEXT;
    spec RECORD;
    ex_id INTEGER;
    npc RECORD;
    npc_priority INTEGER;
    new_task_id INTEGER;
BEGIN
    SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
    INTO cols
    FROM information_schema.columns
    WHERE table_name = 'tasks' AND table_schema = current_schema()
      AND column_name <> 'task_id';

    SELECT exercise_id INTO ex_id FROM exercise_definitions WHERE exercise_key = 'LEG_KICK' AND is_active;
    SELECT npc_id, scene_id INTO npc FROM npcs WHERE npc_key = 'FOREST_SHANLINHOU' AND is_active;
    IF ex_id IS NULL OR npc.npc_id IS NULL THEN
        RAISE EXCEPTION '[K2] 找不到 LEG_KICK 運動或山林猴';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM tasks WHERE task_key = 'MONKEY_STEP_001') THEN
        RAISE EXCEPTION '[K2] 找不到範本任務 MONKEY_STEP_001';
    END IF;

    FOR spec IN
        SELECT * FROM (VALUES
            ('MONKEY_KICK_001', '踢開椰子', '和山林猴一起向前踢腿，把路邊的 10 顆椰子踢開。',
             'count', 10, 10, 1, 5),
            ('MONKEY_KICK_TIME_001', '清出椰子小路', '和山林猴一起踢腿 60 秒，把小路上的椰子都清到旁邊。',
             'time', 60, 10, 1, 5)
        ) AS v(task_key, task_name, task_description, goal_type, target,
               reward_player_exp, reward_scene_exp, reward_money)
    LOOP
        IF EXISTS (SELECT 1 FROM tasks WHERE task_key = spec.task_key) THEN
            RAISE NOTICE '[K2] % 已存在，略過新增', spec.task_key;
            CONTINUE;
        END IF;

        IF to_regclass('pg_temp.tmp_task') IS NOT NULL THEN
            DROP TABLE tmp_task;
        END IF;
        CREATE TEMP TABLE tmp_task ON COMMIT DROP AS
            SELECT * FROM tasks WHERE task_key = 'MONKEY_STEP_001' LIMIT 1;

        UPDATE tmp_task
        SET task_key = spec.task_key,
            task_name = spec.task_name,
            task_description = spec.task_description,
            scene_id = npc.scene_id,
            exercise_id = ex_id,
            exercise_type = 'Kick',
            goal_type = spec.goal_type,
            target_count = CASE WHEN spec.goal_type = 'count' THEN spec.target END,
            target_seconds = CASE WHEN spec.goal_type = 'time' THEN spec.target END,
            input_requirement = 'imu_required',
            required_ball_count = 0,
            task_category = 'commission',
            task_kind = 'story',
            recurrence_type = 'none',
            time_limit_seconds = NULL,
            bonus_target_count = NULL,
            reward_player_exp = spec.reward_player_exp,
            reward_scene_exp = spec.reward_scene_exp,
            reward_money = spec.reward_money,
            required_player_level = 1,
            is_initial_unlock = TRUE,
            is_listed = TRUE,
            is_active = TRUE;

        EXECUTE format('INSERT INTO tasks (%s) SELECT %s FROM tmp_task RETURNING task_id', cols, cols)
        INTO new_task_id;

        -- 用山林猴目前最高的 priority，才會跟踏步任務一起輪流發放
        SELECT COALESCE(MAX(a.priority), 100) INTO npc_priority
        FROM npc_task_assignments a JOIN tasks t ON t.task_id = a.task_id
        WHERE a.npc_id = npc.npc_id AND a.is_active AND t.is_active;

        INSERT INTO npc_task_assignments (npc_id, task_id, priority, weight, is_active)
        VALUES (npc.npc_id, new_task_id, npc_priority, 1, TRUE)
        ON CONFLICT (npc_id, task_id) DO UPDATE SET priority = EXCLUDED.priority, weight = 1, is_active = TRUE;

        INSERT INTO user_task_unlocks (user_id, task_id, unlocked_at)
        SELECT u.user_id, new_task_id, CURRENT_TIMESTAMP
        FROM users u
        WHERE NOT EXISTS (SELECT 1 FROM user_task_unlocks x
                          WHERE x.user_id = u.user_id AND x.task_id = new_task_id);

        RAISE NOTICE '[K2] 已新增 %（task_id=%，priority=%）', spec.task_key, new_task_id, npc_priority;
    END LOOP;
END $$;

-- ------------------------------------------------------------
-- K3：台詞
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_story_lines (
    task_key TEXT,
    story_phase TEXT,
    phase_rank INTEGER,
    dialogue_text TEXT
) ON COMMIT DROP;

INSERT INTO tmp_story_lines VALUES
-- 山林猴｜踢開椰子（計次）
('MONKEY_KICK_001', 'intro', 1, '哎呀～路邊掉了好多椰子，把小路都擋住了！'),
('MONKEY_KICK_001', 'offer', 2, '拿著手機，慢慢抬腳往前踢，一次踢開一顆椰子，一起踢 10 顆吧！'),
('MONKEY_KICK_001', 'partial', 3, '踢得好！椰子滾到旁邊去囉～'),
('MONKEY_KICK_001', 'partial', 4, '剩最後幾顆椰子，小路快通了！'),
('MONKEY_KICK_001', 'completed', 5, '椰子都踢開了！小路又可以走啦！'),
('MONKEY_KICK_001', 'rewarded', 6, '謝謝你幫忙開路，這是森林的小禮物！'),
-- 山林猴｜清出椰子小路（計時）
('MONKEY_KICK_TIME_001', 'intro', 1, '起風之後，整條小路都是椰子，我們一起慢慢清吧！'),
('MONKEY_KICK_TIME_001', 'offer', 2, '用舒服的節奏踢腿 60 秒，把路上的椰子都踢到旁邊！需要的話可以扶著椅子。'),
('MONKEY_KICK_TIME_001', 'partial', 3, '一顆、兩顆～小路越來越乾淨了！'),
('MONKEY_KICK_TIME_001', 'partial', 4, '再一下下，就看得到小路的盡頭了！'),
('MONKEY_KICK_TIME_001', 'completed', 5, '整條小路都清乾淨了！你好厲害！'),
('MONKEY_KICK_TIME_001', 'rewarded', 6, '謝謝你陪我清小路，收下這份謝禮吧！');

DO $$
DECLARE
    r RECORD;
    speaker_npc INTEGER;
    next_order INTEGER;
    inserted INTEGER := 0;
    id_is_auto BOOLEAN;
BEGIN
    SELECT (is_identity = 'YES' OR column_default IS NOT NULL) INTO id_is_auto
    FROM information_schema.columns
    WHERE table_name = 'task_story_steps' AND table_schema = current_schema()
      AND column_name = 'story_step_id';

    FOR r IN
        SELECT t.task_id, l.task_key, l.story_phase, l.dialogue_text
        FROM tmp_story_lines l
        JOIN tasks t ON t.task_key = l.task_key
        ORDER BY l.task_key, l.phase_rank
    LOOP
        IF EXISTS (SELECT 1 FROM task_story_steps s
                   WHERE s.task_id = r.task_id AND s.story_variant = 'A'
                     AND s.story_phase = r.story_phase AND s.dialogue_text = r.dialogue_text) THEN
            CONTINUE;
        END IF;

        SELECT a.npc_id INTO speaker_npc
        FROM npc_task_assignments a
        WHERE a.task_id = r.task_id
        ORDER BY a.is_active DESC, a.priority DESC
        LIMIT 1;

        SELECT COALESCE(MAX(step_order), 0) + 1 INTO next_order
        FROM task_story_steps
        WHERE task_id = r.task_id AND story_variant = 'A';

        IF id_is_auto THEN
            INSERT INTO task_story_steps
                (task_id, story_variant, step_order, story_phase, speaker_type, npc_id, dialogue_text)
            VALUES
                (r.task_id, 'A', next_order, r.story_phase, 'npc', speaker_npc, r.dialogue_text);
        ELSE
            INSERT INTO task_story_steps
                (story_step_id, task_id, story_variant, step_order, story_phase, speaker_type, npc_id, dialogue_text)
            SELECT COALESCE(MAX(story_step_id), 0) + 1, r.task_id, 'A', next_order, r.story_phase, 'npc',
                   speaker_npc, r.dialogue_text
            FROM task_story_steps;
        END IF;

        inserted := inserted + 1;
    END LOOP;

    RAISE NOTICE '[K3] 已寫入 % 句台詞', inserted;
END $$;

COMMIT;
