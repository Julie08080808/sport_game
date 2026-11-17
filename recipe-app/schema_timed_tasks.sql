-- ============================================================
-- 新增 8 個 NPC 任務：6 種運動 × 計次／計時，補齊 12 個可接任務（2026-11-16）
--
-- 已有（不動）：MITU_HAND_RAISE_001 抬手計次、MONKEY_STEP_001 踏步計次、
--              CAT_HAND_PRESS_001 雙手按壓計次、CAT_FOOT_PRESS_001 踩球計次
-- 本檔新增：
--   計次 MONKEY_GRIP_001          採松果        山林猴  手按壓    10 次
--   計次 MITU_BICEP_CURL_001      搬地瓜        咪兔    二頭彎舉  10 次
--   計時 MONKEY_GRIP_TIME_001     抓緊藤蔓      山林猴  手按壓    60 秒
--   計時 MITU_HAND_RAISE_TIME_001 採茭白筍      咪兔    抬手      60 秒
--   計時 MONKEY_STEP_TIME_001     森林散步      山林猴  踏步      90 秒
--   計時 MITU_BICEP_CURL_TIME_001 搬地瓜        咪兔    二頭彎舉  60 秒
--   （MONKEY_GRIP_001、MONKEY_GRIP_TIME_001 還沒有運動畫面，新增後由 T3 停用）
--   計時 CAT_HAND_PRESS_TIME_001  穩住撈網      姜太喵  雙手按壓  60 秒
--   計時 CAT_FOOT_PRESS_TIME_001  讓水車一直轉  姜太喵  踩球      60 秒
--
-- 規則：
--   - 以同類型的既有任務為範本複製（分類、身體部位、暫停／續做等設定沿用）
--   - 計時目標必須是 30～600 秒、30 的倍數（後端 validate_goal 規則）
--   - 感測方式與球數依運動定義：手機 → imu_required／0 顆；感測球 → ball_required／預設球數
--   - NPC 指派的 priority 用該 NPC 目前最高的 priority：後端只從最高 priority 的任務裡抽，
--     priority 較低的新任務會永遠抽不到
--   - 每個任務寫 6 句台詞：intro、offer、partial×2（運動中過一半／快結束各念一句）、completed、rewarded
--
-- 需要 Unity 端支援計時任務（ExerciseCountTaskRules／ExerciseSessionController 已更新）。
-- 可以重複執行：已存在的任務與台詞不會重複新增。
-- 執行方式（範例）：psql -U postgres -d sport -f schema_timed_tasks.sql
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- T1：新增任務
-- ------------------------------------------------------------
DO $$
DECLARE
    cols TEXT;
    spec RECORD;
    ex RECORD;
    npc RECORD;
    npc_priority INTEGER;
    new_task_id INTEGER;
BEGIN
    SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
    INTO cols
    FROM information_schema.columns
    WHERE table_name = 'tasks' AND table_schema = current_schema()
      AND column_name <> 'task_id';

    FOR spec IN
        SELECT * FROM (VALUES
            ('MONKEY_GRIP_001', '採松果', '和山林猴一起握壓感測球撿松果，完成 10 次。',
             'CAT_GRIP_001', 'FOREST_SHANLINHOU', 'HAND_GRIP', 'Grip', 'count', 10, 10, 1, 5),
            ('MITU_BICEP_CURL_001', '搬地瓜', '和咪兔一起做二頭彎舉，把 10 籃地瓜搬進倉庫。',
             'MITU_HAND_RAISE_001', 'FARM_MITU', 'HAND_BICEP_CURL', 'BicepCurl', 'count', 10, 10, 1, 5),
            ('MONKEY_GRIP_TIME_001', '抓緊藤蔓', '和山林猴一起持續握壓感測球 60 秒，抓緊藤蔓過小溪。',
             'CAT_GRIP_001', 'FOREST_SHANLINHOU', 'HAND_GRIP', 'Grip', 'time', 60, 10, 1, 5),
            ('MITU_HAND_RAISE_TIME_001', '採茭白筍', '和咪兔一起抬手 60 秒，把水田裡的茭白筍採收起來。',
             'MITU_HAND_RAISE_001', 'FARM_MITU', 'HAND_RAISE', 'Raise', 'time', 60, 10, 1, 5),
            ('MONKEY_STEP_TIME_001', '森林散步', '和山林猴一起用舒服的速度踏步 90 秒，在森林裡散散步。',
             'MONKEY_STEP_001', 'FOREST_SHANLINHOU', 'LEG_STEP', 'Step', 'time', 90, 15, 1, 8),
            ('MITU_BICEP_CURL_TIME_001', '搬地瓜', '和咪兔一起持續做二頭彎舉 60 秒，把剛挖出來的地瓜搬進倉庫。',
             'MITU_HAND_RAISE_001', 'FARM_MITU', 'HAND_BICEP_CURL', 'BicepCurl', 'time', 60, 10, 1, 5),
            ('CAT_HAND_PRESS_TIME_001', '穩住撈網', '和姜太喵一起用雙手按壓感測球 60 秒，穩住撈網撈大魚。',
             'CAT_HAND_PRESS_001', 'POND_JIANGTAIMIAO', 'HAND_DUAL_PRESS', 'HandPress', 'time', 60, 10, 1, 5),
            ('CAT_FOOT_PRESS_TIME_001', '讓水車一直轉', '和姜太喵一起用雙腳踩壓感測球 60 秒，讓水車持續轉動。',
             'CAT_FOOT_PRESS_001', 'POND_JIANGTAIMIAO', 'LEG_BALL_PRESS', 'FootPress', 'time', 60, 10, 1, 5)
        ) AS v(task_key, task_name, task_description, template_key, npc_key, exercise_key,
               exercise_type, goal_type, target, reward_player_exp, reward_scene_exp, reward_money)
    LOOP
        IF EXISTS (SELECT 1 FROM tasks WHERE task_key = spec.task_key) THEN
            RAISE NOTICE '[T1] % 已存在，略過新增', spec.task_key;
            CONTINUE;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM tasks WHERE task_key = spec.template_key) THEN
            RAISE EXCEPTION '[T1] 找不到範本任務 %', spec.template_key;
        END IF;

        SELECT exercise_id, input_type, default_required_ball_count INTO ex
        FROM exercise_definitions WHERE exercise_key = spec.exercise_key AND is_active;
        IF ex.exercise_id IS NULL THEN
            RAISE EXCEPTION '[T1] 找不到啟用中的運動定義 %', spec.exercise_key;
        END IF;

        SELECT npc_id, scene_id INTO npc FROM npcs WHERE npc_key = spec.npc_key AND is_active;
        IF npc.npc_id IS NULL THEN
            RAISE EXCEPTION '[T1] 找不到啟用中的 NPC %', spec.npc_key;
        END IF;

        IF spec.goal_type = 'time' AND (spec.target < 30 OR spec.target > 600 OR spec.target % 30 <> 0) THEN
            RAISE EXCEPTION '[T1] % 的目標秒數 % 不合規則（30～600 秒、30 的倍數）', spec.task_key, spec.target;
        END IF;

        IF to_regclass('pg_temp.tmp_task') IS NOT NULL THEN
            DROP TABLE tmp_task;
        END IF;
        CREATE TEMP TABLE tmp_task ON COMMIT DROP AS
            SELECT * FROM tasks WHERE task_key = spec.template_key LIMIT 1;

        UPDATE tmp_task
        SET task_key = spec.task_key,
            task_name = spec.task_name,
            task_description = spec.task_description,
            scene_id = npc.scene_id,
            exercise_id = ex.exercise_id,
            exercise_type = spec.exercise_type,
            goal_type = spec.goal_type,
            target_count = CASE WHEN spec.goal_type = 'count' THEN spec.target END,
            target_seconds = CASE WHEN spec.goal_type = 'time' THEN spec.target END,
            input_requirement = CASE WHEN ex.input_type = 'phone_imu' THEN 'imu_required' ELSE 'ball_required' END,
            required_ball_count = CASE WHEN ex.input_type = 'phone_imu' THEN 0
                                       ELSE GREATEST(ex.default_required_ball_count, 1) END,
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

        SELECT COALESCE(MAX(a.priority), 100) INTO npc_priority
        FROM npc_task_assignments a JOIN tasks t ON t.task_id = a.task_id
        WHERE a.npc_id = npc.npc_id AND a.is_active AND t.is_active;

        INSERT INTO npc_task_assignments (npc_id, task_id, priority, weight, is_active)
        VALUES (npc.npc_id, new_task_id, npc_priority, 1, TRUE)
        ON CONFLICT (npc_id, task_id) DO UPDATE SET priority = EXCLUDED.priority, weight = 1, is_active = TRUE;

        -- 初始解鎖：所有玩家都能直接接到（等同管理後台的 _backfill_initial_unlocks）
        INSERT INTO user_task_unlocks (user_id, task_id, unlocked_at)
        SELECT u.user_id, new_task_id, CURRENT_TIMESTAMP
        FROM users u
        WHERE NOT EXISTS (SELECT 1 FROM user_task_unlocks x
                          WHERE x.user_id = u.user_id AND x.task_id = new_task_id);

        RAISE NOTICE '[T1] 已新增 %（task_id=%，NPC=%，priority=%）',
            spec.task_key, new_task_id, spec.npc_key, npc_priority;
    END LOOP;
END $$;

-- ------------------------------------------------------------
-- T1b：文案改版（2026-11-17）
--   趕走小麻雀 → 採茭白筍（沿用抬手挑戰的茭白筍運動畫面）
--   搬運大南瓜 → 搬地瓜（配合運動畫面）
-- 已經跑過舊版本檔案的資料庫：把舊名稱與舊台詞原地換成新版，避免 T2 再多寫一份。
-- ------------------------------------------------------------
UPDATE tasks SET task_name = '採茭白筍',
                 task_description = '和咪兔一起抬手 60 秒，把水田裡的茭白筍採收起來。'
WHERE task_key = 'MITU_HAND_RAISE_TIME_001' AND task_name = '趕走小麻雀';

UPDATE tasks SET task_name = '搬地瓜',
                 task_description = '和咪兔一起持續做二頭彎舉 60 秒，把剛挖出來的地瓜搬進倉庫。'
WHERE task_key = 'MITU_BICEP_CURL_TIME_001' AND task_name = '搬運大南瓜';

UPDATE tasks SET task_name = '搬地瓜',
                 task_description = '和咪兔一起做二頭彎舉，把 10 籃地瓜搬進倉庫。'
WHERE task_key = 'MITU_BICEP_CURL_001' AND task_name = '提水澆菜';

UPDATE task_story_steps s
SET dialogue_text = v.new_text
FROM tasks t,
     (VALUES
        ('MITU_HAND_RAISE_TIME_001', '哎呀～小麻雀又來偷吃番茄了！', '水田裡的茭白筍長得又白又胖，該採收囉！'),
        ('MITU_HAND_RAISE_TIME_001', '跟我一起抬起手揮一揮 60 秒，把小麻雀嚇跑吧！慢慢來就好。', '跟我一起慢慢抬手 60 秒，把茭白筍一根根採起來吧！'),
        ('MITU_HAND_RAISE_TIME_001', '揮得好！小麻雀開始飛走囉～', '採得好！籃子裡的茭白筍越來越多了～'),
        ('MITU_HAND_RAISE_TIME_001', '剩一點點時間，小麻雀快飛光了！', '再一下下，最後幾根茭白筍就採完了！'),
        ('MITU_HAND_RAISE_TIME_001', '小麻雀都飛走啦！番茄保住了！', '茭白筍全部採好了！今天的晚餐有著落囉！'),
        ('MITU_BICEP_CURL_TIME_001', '今年的南瓜長得好大，我一個人搬不動耶～', '地瓜田大豐收！可是一籃一籃好重，我一個人搬不動耶～'),
        ('MITU_BICEP_CURL_TIME_001', '拿著手機持續做彎舉動作 60 秒，一起把南瓜搬進倉庫吧！', '拿著手機持續做彎舉動作 60 秒，一起把地瓜搬進倉庫吧！'),
        ('MITU_BICEP_CURL_TIME_001', '嘿咻嘿咻～南瓜慢慢移動了！', '嘿咻嘿咻～一籃地瓜搬好了！'),
        ('MITU_BICEP_CURL_TIME_001', '最後一顆南瓜，快搬進倉庫了！', '最後幾籃地瓜，快搬完囉！'),
        ('MITU_BICEP_CURL_TIME_001', '南瓜全都搬好了！你真的好厲害！', '地瓜全都搬好了！你真的好厲害！'),
        ('MITU_BICEP_CURL_001', '菜園的小白菜口渴了，可以幫我提水澆一澆嗎？', '地瓜挖好了，一籃一籃堆在田邊，可以幫我搬嗎？'),
        ('MITU_BICEP_CURL_001', '拿著手機慢慢彎起手臂，就像提起水桶，一起提 10 次吧！', '拿著手機慢慢彎起手臂，每做一次就搬一籃，一起搬 10 籃吧！'),
        ('MITU_BICEP_CURL_001', '提起來、放下去～菜菜們好開心！', '嘿咻～已經搬一半囉！'),
        ('MITU_BICEP_CURL_001', '最後幾桶水了，菜菜在等你喔！', '剩最後幾籃，快搬完了！'),
        ('MITU_BICEP_CURL_001', '澆完水了！小白菜都抬起頭來了！', '10 籃地瓜都搬進倉庫了！謝謝你！'),
        ('MITU_BICEP_CURL_001', '謝謝你幫忙照顧菜園，這是給你的謝禮！', '謝謝你幫忙搬地瓜，這是給你的謝禮！')
     ) AS v(task_key, old_text, new_text)
WHERE t.task_key = v.task_key AND s.task_id = t.task_id AND s.dialogue_text = v.old_text;

-- ------------------------------------------------------------
-- T2：台詞
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_story_lines (
    task_key TEXT,
    story_phase TEXT,
    phase_rank INTEGER,
    dialogue_text TEXT
) ON COMMIT DROP;

INSERT INTO tmp_story_lines VALUES
-- 山林猴｜採松果（計次）
('MONKEY_GRIP_001', 'intro', 1, '嘿嘿～樹上的松果掉了一地！可以幫我撿起來嗎？'),
('MONKEY_GRIP_001', 'offer', 2, '用手握緊感測球再放開，每握一次就撿起一顆，一起撿 10 顆吧！'),
('MONKEY_GRIP_001', 'partial', 3, '握緊、放開～松果越來越多囉！'),
('MONKEY_GRIP_001', 'partial', 4, '再幾顆就滿籃了，加油！'),
('MONKEY_GRIP_001', 'completed', 5, '哇！籃子都滿了！你的手好有力氣！'),
('MONKEY_GRIP_001', 'rewarded', 6, '這是森林的小禮物，謝謝你幫忙！'),
-- 咪兔｜搬地瓜（計次）
('MITU_BICEP_CURL_001', 'intro', 1, '地瓜挖好了，一籃一籃堆在田邊，可以幫我搬嗎？'),
('MITU_BICEP_CURL_001', 'offer', 2, '拿著手機慢慢彎起手臂，每做一次就搬一籃，一起搬 10 籃吧！'),
('MITU_BICEP_CURL_001', 'partial', 3, '嘿咻～已經搬一半囉！'),
('MITU_BICEP_CURL_001', 'partial', 4, '剩最後幾籃，快搬完了！'),
('MITU_BICEP_CURL_001', 'completed', 5, '10 籃地瓜都搬進倉庫了！謝謝你！'),
('MITU_BICEP_CURL_001', 'rewarded', 6, '謝謝你幫忙搬地瓜，這是給你的謝禮！'),
-- 山林猴｜抓緊藤蔓（計時）
('MONKEY_GRIP_TIME_001', 'intro', 1, '前面要過小溪了，我們要抓著藤蔓慢慢走過去！'),
('MONKEY_GRIP_TIME_001', 'offer', 2, '持續握著感測球 60 秒，就像抓緊藤蔓一樣，不用急喔！'),
('MONKEY_GRIP_TIME_001', 'partial', 3, '抓穩了！保持呼吸，已經走一半囉～'),
('MONKEY_GRIP_TIME_001', 'partial', 4, '快到對岸了，再撐一下下！'),
('MONKEY_GRIP_TIME_001', 'completed', 5, '成功過河啦！你抓得好穩！'),
('MONKEY_GRIP_TIME_001', 'rewarded', 6, '謝謝你陪我冒險，這個送給你！'),
-- 咪兔｜採茭白筍（計時，沿用抬手挑戰的運動畫面）
('MITU_HAND_RAISE_TIME_001', 'intro', 1, '水田裡的茭白筍長得又白又胖，該採收囉！'),
('MITU_HAND_RAISE_TIME_001', 'offer', 2, '跟我一起慢慢抬手 60 秒，把茭白筍一根根採起來吧！'),
('MITU_HAND_RAISE_TIME_001', 'partial', 3, '採得好！籃子裡的茭白筍越來越多了～'),
('MITU_HAND_RAISE_TIME_001', 'partial', 4, '再一下下，最後幾根茭白筍就採完了！'),
('MITU_HAND_RAISE_TIME_001', 'completed', 5, '茭白筍全部採好了！今天的晚餐有著落囉！'),
('MITU_HAND_RAISE_TIME_001', 'rewarded', 6, '多虧有你！這些是今天的謝禮～'),
-- 山林猴｜森林散步（計時）
('MONKEY_STEP_TIME_001', 'intro', 1, '今天陽光好舒服，要不要一起在森林裡散散步？'),
('MONKEY_STEP_TIME_001', 'offer', 2, '用自己舒服的速度踏步 90 秒，累了可以隨時休息。'),
('MONKEY_STEP_TIME_001', 'partial', 3, '一步一步～聽，有小鳥在唱歌呢！'),
('MONKEY_STEP_TIME_001', 'partial', 4, '前面就是終點啦，慢慢走～'),
('MONKEY_STEP_TIME_001', 'completed', 5, '走完一圈啦！森林的空氣真好！'),
('MONKEY_STEP_TIME_001', 'rewarded', 6, '謝謝你陪我散步，這是今天的紀念品！'),
-- 咪兔｜搬地瓜（計時）
('MITU_BICEP_CURL_TIME_001', 'intro', 1, '地瓜田大豐收！可是一籃一籃好重，我一個人搬不動耶～'),
('MITU_BICEP_CURL_TIME_001', 'offer', 2, '拿著手機持續做彎舉動作 60 秒，一起把地瓜搬進倉庫吧！'),
('MITU_BICEP_CURL_TIME_001', 'partial', 3, '嘿咻嘿咻～一籃地瓜搬好了！'),
('MITU_BICEP_CURL_TIME_001', 'partial', 4, '最後幾籃地瓜，快搬完囉！'),
('MITU_BICEP_CURL_TIME_001', 'completed', 5, '地瓜全都搬好了！你真的好厲害！'),
('MITU_BICEP_CURL_TIME_001', 'rewarded', 6, '這是農場的豐收禮，請收下！'),
-- 姜太喵｜穩住撈網（計時）
('CAT_HAND_PRESS_TIME_001', 'intro', 1, '喵嗚～有一條大魚游過來了！撈網要拿穩才行！'),
('CAT_HAND_PRESS_TIME_001', 'offer', 2, '雙手一起按壓感測球 60 秒，幫我穩住撈網吧！'),
('CAT_HAND_PRESS_TIME_001', 'partial', 3, '穩住穩住～大魚快進網了！'),
('CAT_HAND_PRESS_TIME_001', 'partial', 4, '大魚就在網邊，再穩住一下！'),
('CAT_HAND_PRESS_TIME_001', 'completed', 5, '撈到了！好大一條魚呀！'),
('CAT_HAND_PRESS_TIME_001', 'rewarded', 6, '這是我最珍貴的謝禮，快收下喵～'),
-- 姜太喵｜讓水車一直轉（計時）
('CAT_FOOT_PRESS_TIME_001', 'intro', 1, '池塘的水車又停下來了，可以幫它一直轉下去嗎？'),
('CAT_FOOT_PRESS_TIME_001', 'offer', 2, '雙腳一起踩壓感測球 60 秒，讓水車持續轉動吧！'),
('CAT_FOOT_PRESS_TIME_001', 'partial', 3, '水車轉起來了！保持節奏就好～'),
('CAT_FOOT_PRESS_TIME_001', 'partial', 4, '水快滿了，再踩一會兒就好！'),
('CAT_FOOT_PRESS_TIME_001', 'completed', 5, '池塘的水又清又滿了！謝謝你！'),
('CAT_FOOT_PRESS_TIME_001', 'rewarded', 6, '這是池塘送你的小禮物喵～');

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
        -- 同一句已經寫過就略過（重複執行不會多出台詞）
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

        IF speaker_npc IS NULL THEN
            RAISE NOTICE '[T2] % 沒有指派 NPC，略過：%', r.task_key, r.dialogue_text;
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

    RAISE NOTICE '[T2] 已寫入 % 句台詞', inserted;
END $$;

-- ------------------------------------------------------------
-- T3：山林猴的握球任務還沒有運動畫面，先停用（2026-11-17）
--   任務、台詞都保留，畫面做好後到管理後台按「啟用」即可
-- ------------------------------------------------------------
UPDATE tasks SET is_active = FALSE
WHERE task_key IN ('MONKEY_GRIP_001', 'MONKEY_GRIP_TIME_001') AND is_active;

-- 執行後檢查：每個 NPC 目前可發的任務
SELECT n.npc_name, t.task_key, t.task_name, t.goal_type,
       COALESCE(t.target_count::TEXT || ' 次', t.target_seconds::TEXT || ' 秒') AS target,
       t.input_requirement, t.required_ball_count, a.priority
FROM npc_task_assignments a
JOIN tasks t ON t.task_id = a.task_id
JOIN npcs n ON n.npc_id = a.npc_id
WHERE a.is_active AND t.is_active AND t.is_listed AND t.task_kind = 'story'
ORDER BY n.npc_id, t.goal_type, t.task_key;

COMMIT;
