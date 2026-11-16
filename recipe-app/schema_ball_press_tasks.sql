-- ============================================================
-- 姜泰喵雙球任務＋企劃書 V1.0 台詞（2026-11-16）
--
-- 內容：
--   B1  停用 CAT_GRIP_001（單球握球，避免進入姜泰喵的隨機抽籤）
--   B2  運動定義：
--       - 踩球 LEG_BALL_PRESS（FOOT_PRESS）改成 2 顆球、球類場景
--       - 新增 雙手按壓 HAND_DUAL_PRESS（HAND_PRESS）：2 顆球、球類場景
--   B4  新增兩個池塘委託：CAT_HAND_PRESS_001 撈魚挑戰、CAT_FOOT_PRESS_001 水車補水
--       （姜太喵、目標 10 次、不重複、初始解鎖；同優先度＋同權重 → 各 50% 隨機發布）
--   B5  企劃書第 4 章台詞（intro／offer 邀請、partial 挑戰中鼓勵、completed 完成、rewarded 領獎）：
--       已經有邀請台詞或該階段台詞的任務不覆蓋；Unity 運動場景會念出鼓勵與完成台詞
--
-- 可以重複執行：每一段都有 NOT EXISTS／條件保護，不會重複新增。
-- 執行方式（範例）：psql -U postgres -d sport -f schema_ball_press_tasks.sql
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- B1：停用舊的單球握球委託
-- ------------------------------------------------------------
UPDATE tasks SET is_active = FALSE WHERE task_key = 'CAT_GRIP_001';
UPDATE npc_task_assignments a SET is_active = FALSE
FROM tasks t WHERE t.task_id = a.task_id AND t.task_key = 'CAT_GRIP_001';

-- ------------------------------------------------------------
-- B2：運動定義
-- ------------------------------------------------------------
-- 踩球：改成左右腳各一顆球、進球類場景
UPDATE exercise_definitions
SET default_required_ball_count = 2,
    exercise_scene_key = 'ball',
    recognition_key = 'FOOT_PRESS'
WHERE exercise_key = 'LEG_BALL_PRESS';

-- 雙手按壓：以「手按壓 HAND_GRIP」為範本複製一筆，只改必要欄位。
-- 用動態欄位清單複製，不必知道 exercise_definitions 的全部欄位，也不管 exercise_id 是 serial 還是 identity。
DO $$
DECLARE
    cols TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM exercise_definitions WHERE exercise_key = 'HAND_DUAL_PRESS') THEN
        RAISE NOTICE '[B2] HAND_DUAL_PRESS 已存在，略過新增';
    ELSIF NOT EXISTS (SELECT 1 FROM exercise_definitions WHERE exercise_key = 'HAND_GRIP') THEN
        RAISE EXCEPTION '[B2] 找不到範本 HAND_GRIP，無法新增 HAND_DUAL_PRESS';
    ELSE
        CREATE TEMP TABLE tmp_exercise ON COMMIT DROP AS
            SELECT * FROM exercise_definitions WHERE exercise_key = 'HAND_GRIP' LIMIT 1;

        UPDATE tmp_exercise
        SET exercise_key = 'HAND_DUAL_PRESS',
            exercise_name = '雙手按壓',
            recognition_key = 'HAND_PRESS',
            default_required_ball_count = 2,
            exercise_scene_key = 'ball',
            is_active = TRUE;

        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'exercise_definitions' AND column_name = 'description') THEN
            EXECUTE $q$UPDATE tmp_exercise SET description = '左右手各一顆感測球，兩邊同時按下算一次。'$q$;
        END IF;

        SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
        INTO cols
        FROM information_schema.columns
        WHERE table_name = 'exercise_definitions' AND table_schema = current_schema()
          AND column_name <> 'exercise_id';

        EXECUTE format('INSERT INTO exercise_definitions (%s) SELECT %s FROM tmp_exercise', cols, cols);
        RAISE NOTICE '[B2] 已新增 HAND_DUAL_PRESS';
    END IF;
END $$;

-- ------------------------------------------------------------
-- B4：兩個池塘雙球委託（以 CAT_GRIP_001 為範本複製，獎勵、分類等設定沿用）
-- ------------------------------------------------------------
DO $$
DECLARE
    cols TEXT;
    spec RECORD;
    new_task_id INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tasks WHERE task_key = 'CAT_GRIP_001') THEN
        RAISE EXCEPTION '[B4] 找不到範本 CAT_GRIP_001';
    END IF;

    SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
    INTO cols
    FROM information_schema.columns
    WHERE table_name = 'tasks' AND table_schema = current_schema()
      AND column_name <> 'task_id';

    FOR spec IN
        SELECT * FROM (VALUES
            ('CAT_HAND_PRESS_001', '撈魚挑戰', '和姜太喵一起用雙手按壓感測球操控撈網，完成 10 次撈魚。',
             'HAND_DUAL_PRESS', 'HandPress'),
            ('CAT_FOOT_PRESS_001', '水車補水', '和姜太喵一起用雙腳踩壓感測球讓水車轉動，完成 10 次幫池塘補水。',
             'LEG_BALL_PRESS', 'FootPress')
        ) AS v(task_key, task_name, task_description, exercise_key, exercise_type)
    LOOP
        IF EXISTS (SELECT 1 FROM tasks WHERE task_key = spec.task_key) THEN
            RAISE NOTICE '[B4] % 已存在，略過新增', spec.task_key;
            CONTINUE;
        END IF;

        IF to_regclass('pg_temp.tmp_task') IS NOT NULL THEN
            DROP TABLE tmp_task;
        END IF;
        CREATE TEMP TABLE tmp_task ON COMMIT DROP AS
            SELECT * FROM tasks WHERE task_key = 'CAT_GRIP_001' LIMIT 1;

        UPDATE tmp_task
        SET task_key = spec.task_key,
            task_name = spec.task_name,
            task_description = spec.task_description,
            exercise_id = (SELECT exercise_id FROM exercise_definitions WHERE exercise_key = spec.exercise_key),
            exercise_type = spec.exercise_type,
            goal_type = 'count',
            target_count = 10,
            input_requirement = 'ball_required',
            required_ball_count = 2,
            recurrence_type = 'none',
            is_initial_unlock = TRUE,
            is_active = TRUE;

        IF (SELECT exercise_id FROM tmp_task) IS NULL THEN
            RAISE EXCEPTION '[B4] 找不到運動定義 %', spec.exercise_key;
        END IF;

        EXECUTE format('INSERT INTO tasks (%s) SELECT %s FROM tmp_task RETURNING task_id', cols, cols)
        INTO new_task_id;

        -- 指派給姜太喵：跟管理後台一樣用 priority 100、weight 1
        INSERT INTO npc_task_assignments (npc_id, task_id, priority, weight, is_active)
        SELECT n.npc_id, new_task_id, 100, 1, TRUE
        FROM npcs n WHERE n.npc_key = 'POND_JIANGTAIMIAO'
        ON CONFLICT (npc_id, task_id) DO UPDATE SET priority = 100, weight = 1, is_active = TRUE;

        -- 初始解鎖：所有玩家都能直接接到（等同管理後台的 _backfill_initial_unlocks）
        INSERT INTO user_task_unlocks (user_id, task_id, unlocked_at)
        SELECT u.user_id, new_task_id, CURRENT_TIMESTAMP
        FROM users u
        WHERE NOT EXISTS (SELECT 1 FROM user_task_unlocks x
                          WHERE x.user_id = u.user_id AND x.task_id = new_task_id);

        RAISE NOTICE '[B4] 已新增 %（task_id=%）', spec.task_key, new_task_id;
    END LOOP;
END $$;

-- ------------------------------------------------------------
-- B5：企劃書第 4 章台詞
-- 依資料庫實際規則：
--   - story_phase 只能用：intro、offer、accepted、instruction、warmup、partial、completed、
--     advanced_success、rewarded、abandoned
--     → 任務邀請 = intro、接受任務（目標說明）= offer、挑戰中鼓勵 = partial、
--       完成任務 = completed、領取獎勵 = rewarded
--   - speaker_type = 'npc' 時必須填 npc_id（發任務的 NPC）
--   - 同一個任務＋同一個故事版本的 step_order 不能重複（所有階段共用一個順序）
--     → 新台詞接在這個任務現有台詞的最後面
-- 不覆蓋：任務原本就有 intro/offer 台詞時不寫邀請台詞；原本就有某個階段時不寫那個階段。
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_story_lines (
    task_key TEXT,
    story_phase TEXT,
    phase_rank INTEGER,
    dialogue_text TEXT
) ON COMMIT DROP;

INSERT INTO tmp_story_lines VALUES
-- 4.1 山林猴｜森林踏步
('MONKEY_STEP_001', 'intro', 1, '嘿嘿～森林小路今天好安靜！陪我踏踏腳，讓這裡熱鬧起來吧！'),
('MONKEY_STEP_001', 'offer', 2, '今天的目標是踏步 20 次，完成就有小獎勵喔！'),
('MONKEY_STEP_001', 'partial', 3, '保持舒服的節奏！一步一步就好！'),
('MONKEY_STEP_001', 'completed', 4, '哇～20 次完成啦！森林小路又有活力了！'),
('MONKEY_STEP_001', 'rewarded', 5, '謝謝你陪我運動！快收下這份獎勵吧！'),
-- 4.2 老山狐｜每日握球
('FOX_DAILY_GRIP_001', 'intro', 1, '早安呀！今天也來動動手，讓我們一起完成每日握球吧！'),
('FOX_DAILY_GRIP_001', 'offer', 2, '這次握球 10 次，完成就能記下今天的運動成果。'),
('FOX_DAILY_GRIP_001', 'partial', 3, '握緊、放開，穩穩地來！'),
('FOX_DAILY_GRIP_001', 'completed', 4, '做得好！今天的握球練習完成了！'),
('FOX_DAILY_GRIP_001', 'rewarded', 5, '每日運動紀錄更新啦！記得看看你的獎勵。'),
-- 4.3 老山狐｜每日踏步
('FOX_DAILY_STEP_001', 'intro', 1, '今天也要讓雙腳動起來！來做個 20 次踏步吧！'),
('FOX_DAILY_STEP_001', 'offer', 2, '完成今天的踏步，就能累積每日運動紀錄。'),
('FOX_DAILY_STEP_001', 'partial', 3, '很好，穩穩地踏！'),
('FOX_DAILY_STEP_001', 'completed', 4, '今天的 20 次踏步完成了！'),
('FOX_DAILY_STEP_001', 'rewarded', 5, '記錄成功！再接再厲，明天也一起動一動。'),
-- 4.4 老山狐｜每日抬手
('FOX_DAILY_HAND_RAISE_001', 'intro', 1, '坐久了嗎？陪我慢慢抬抬手，讓肩膀活動一下！'),
('FOX_DAILY_HAND_RAISE_001', 'offer', 2, '完成 10 次抬手，就完成今天的任務囉！'),
('FOX_DAILY_HAND_RAISE_001', 'partial', 3, '不急，慢慢抬、慢慢放！'),
('FOX_DAILY_HAND_RAISE_001', 'completed', 4, '抬手挑戰完成啦！'),
('FOX_DAILY_HAND_RAISE_001', 'rewarded', 5, '今天的肩臂運動也記錄好了！'),
-- 4.5 姜泰喵｜手部撈魚
('CAT_HAND_PRESS_001', 'intro', 1, '喵嗚～小魚游得好快！能不能幫我一起把魚撈起來呀？'),
('CAT_HAND_PRESS_001', 'offer', 2, '一起用雙手按壓感測球，幫忙完成撈魚挑戰吧！'),
('CAT_HAND_PRESS_001', 'partial', 3, '好耶！慢慢按，撈網就靠你啦！'),
('CAT_HAND_PRESS_001', 'completed', 4, '喵嗚～魚撈上來啦！謝謝你幫忙！'),
('CAT_HAND_PRESS_001', 'rewarded', 5, '這是我的小小謝禮，快收下吧！'),
-- 4.6 姜泰喵｜腳部水車補水
('CAT_FOOT_PRESS_001', 'intro', 1, '哎呀～池塘的水變少了！可以幫我讓水車轉起來嗎？'),
('CAT_FOOT_PRESS_001', 'offer', 2, '跟著我慢慢踩壓感測球，一起幫池塘補水吧！'),
('CAT_FOOT_PRESS_001', 'partial', 3, '很好！慢慢踩，水車轉起來啦！'),
('CAT_FOOT_PRESS_001', 'completed', 4, '太好了！池塘的水慢慢回來了！'),
('CAT_FOOT_PRESS_001', 'rewarded', 5, '謝謝你幫忙照顧池塘，收下獎勵吧！'),
-- 4.7 咪兔｜抬手委託
('MITU_HAND_RAISE_001', 'intro', 1, '農場好多事情要忙呢！陪我一起抬抬手，好嗎？'),
('MITU_HAND_RAISE_001', 'offer', 2, '這次完成 10 次抬手，我們就能完成農場小幫手任務！'),
('MITU_HAND_RAISE_001', 'partial', 3, '慢慢來！我們快完成囉！'),
('MITU_HAND_RAISE_001', 'completed', 4, '太棒了！農場的工作輕鬆多啦！'),
('MITU_HAND_RAISE_001', 'rewarded', 5, '謝謝你今天來幫忙，這是你的獎勵！'),
-- 4.8 咪兔｜幫忙採番茄（主線；任務目前停用，台詞先放好）
('FARM_MAIN_GRIP_001', 'intro', 1, '哇！番茄都紅通通了！可以陪我一起採收嗎？'),
('FARM_MAIN_GRIP_001', 'offer', 2, '我們用抬手動作來採番茄，完成 10 次就能幫上忙喔！'),
('FARM_MAIN_GRIP_001', 'partial', 3, '又採到一顆！慢慢來就好！'),
('FARM_MAIN_GRIP_001', 'completed', 4, '太好了！番茄都採好啦！'),
('FARM_MAIN_GRIP_001', 'rewarded', 5, '謝謝你！農場任務完成，故事可以繼續囉！');

DO $$
DECLARE
    r RECORD;
    speaker_npc INTEGER;
    next_order INTEGER;
    inserted INTEGER := 0;
    id_is_auto BOOLEAN;
BEGIN
    -- story_step_id 是自動編號（identity／有預設值）就交給資料庫，否則自己接著最大號往下編
    SELECT (is_identity = 'YES' OR column_default IS NOT NULL) INTO id_is_auto
    FROM information_schema.columns
    WHERE table_name = 'task_story_steps' AND table_schema = current_schema()
      AND column_name = 'story_step_id';

    -- 執行前的狀態：哪些任務已經有邀請台詞、已經有哪些階段
    CREATE TEMP TABLE tmp_had_offer ON COMMIT DROP AS
        SELECT DISTINCT task_id FROM task_story_steps
        WHERE story_variant = 'A' AND story_phase IN ('intro', 'offer');
    CREATE TEMP TABLE tmp_had_phase ON COMMIT DROP AS
        SELECT DISTINCT task_id, story_phase FROM task_story_steps
        WHERE story_variant = 'A' AND story_phase IN ('partial', 'completed', 'rewarded');

    FOR r IN
        SELECT t.task_id, l.task_key, l.story_phase, l.dialogue_text
        FROM tmp_story_lines l
        JOIN tasks t ON t.task_key = l.task_key
        ORDER BY l.task_key, l.phase_rank
    LOOP
        IF r.story_phase IN ('intro', 'offer') AND
           EXISTS (SELECT 1 FROM tmp_had_offer h WHERE h.task_id = r.task_id) THEN
            CONTINUE;
        END IF;

        IF r.story_phase NOT IN ('intro', 'offer') AND
           EXISTS (SELECT 1 FROM tmp_had_phase h
                   WHERE h.task_id = r.task_id AND h.story_phase = r.story_phase) THEN
            CONTINUE;
        END IF;

        -- 說話的 NPC：這個任務目前指派給哪一隻 NPC
        SELECT a.npc_id INTO speaker_npc
        FROM npc_task_assignments a
        WHERE a.task_id = r.task_id
        ORDER BY a.is_active DESC, a.priority DESC
        LIMIT 1;

        IF speaker_npc IS NULL THEN
            RAISE NOTICE '[B5] % 沒有指派 NPC，略過：%', r.task_key, r.dialogue_text;
            CONTINUE;
        END IF;

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

    RAISE NOTICE '[B5] 已寫入 % 句台詞', inserted;

    FOR r IN
        SELECT DISTINCT l.task_key
        FROM tmp_story_lines l
        JOIN tasks t ON t.task_key = l.task_key
        JOIN tmp_had_offer h ON h.task_id = t.task_id
    LOOP
        RAISE NOTICE '[B5] % 原本就有邀請台詞，保留原本的，沒有改成企劃書版本', r.task_key;
    END LOOP;
END $$;

COMMIT;
