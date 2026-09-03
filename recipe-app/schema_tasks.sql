-- NPC / 任務系統 - 新版 Task 架構 (對應 commit 68c9a74「npc的功能修正、任務功能、管理平台」)
--
-- 這支檔案不是原作者提供的，是依照下列程式碼實際下的 SQL 逆向整理出來的，
-- 因為當時的 commit 沒有一併附上建表語法：
--   models/npc_model.py, models/admin_model.py, models/admin_test_model.py,
--   models/user_model.py (_initialize_user_scenes / _unlock_initial_tasks),
--   views/admin/task_form.html
-- 如果之後拿到作者本人的正式 schema，請以那份為準，這份只是先讓功能能跑起來。
--
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_tasks.sql

-- ============================================================
-- 0. scenes 表擴充：新架構會用 scene_key(給 admin 表單顯示) 和 is_active(篩選景點)
-- ============================================================
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS scene_key VARCHAR(30);
ALTER TABLE scenes ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE scenes SET scene_key = CASE scene_id
    WHEN 0 THEN 'farm'
    WHEN 1 THEN 'pond'
    WHEN 2 THEN 'forest'
    WHEN 3 THEN 'center'
    WHEN 4 THEN 'orchard'
END
WHERE scene_key IS NULL;

-- ============================================================
-- 1. npcs：場景裡的 NPC 基本資料
-- ============================================================
CREATE TABLE IF NOT EXISTS npcs (
    npc_id SERIAL PRIMARY KEY,
    npc_key VARCHAR(50) UNIQUE NOT NULL,   -- Unity NpcInteraction.npcId 送過來的字串，例如 rabbit
    scene_id INTEGER NOT NULL REFERENCES scenes(scene_id),
    npc_name VARCHAR(50) NOT NULL,
    description TEXT,
    image_key VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- 2. tasks：任務主表(管理後台的新增/編輯任務表單對應這張)
-- ============================================================
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    task_key VARCHAR(50) UNIQUE NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    task_description TEXT,
    task_category VARCHAR(20) NOT NULL DEFAULT 'commission', -- main | daily | commission | special
    task_type VARCHAR(20) NOT NULL DEFAULT 'persistent',     -- persistent | immediate
    task_mode VARCHAR(20) NOT NULL DEFAULT 'basic',          -- basic | advanced
    scene_id INTEGER NOT NULL REFERENCES scenes(scene_id),
    exercise_type VARCHAR(50),                                -- 例如 Grip、BicepCurl、LegRaise
    goal_type VARCHAR(20) NOT NULL DEFAULT 'count',           -- count | time
    target_count INTEGER,
    target_seconds INTEGER,
    input_requirement VARCHAR(20) NOT NULL DEFAULT 'imu_required', -- ball_required | ball_or_imu | imu_required | both_required
    required_ball_count INTEGER NOT NULL DEFAULT 0,
    recurrence_type VARCHAR(20) NOT NULL DEFAULT 'none',       -- none | daily | weekly
    allow_pause BOOLEAN NOT NULL DEFAULT TRUE,
    allow_resume BOOLEAN NOT NULL DEFAULT TRUE,
    reward_player_exp INTEGER NOT NULL DEFAULT 0,
    reward_scene_exp INTEGER NOT NULL DEFAULT 0,
    reward_money INTEGER NOT NULL DEFAULT 0,
    required_player_level INTEGER NOT NULL DEFAULT 1,
    expire_policy VARCHAR(20) NOT NULL DEFAULT 'none',         -- none | after_accept | end_of_day | end_of_week
    expire_after_seconds INTEGER,
    is_initial_unlock BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- 3. npc_task_assignments：哪個 NPC 會發送哪個任務
-- ============================================================
CREATE TABLE IF NOT EXISTS npc_task_assignments (
    npc_id INTEGER NOT NULL REFERENCES npcs(npc_id),
    task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    priority INTEGER NOT NULL DEFAULT 0,
    weight INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (npc_id, task_id)
);

-- ============================================================
-- 4. user_task_unlocks：玩家解鎖了哪些任務(才會被 NPC 提供)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_task_unlocks (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    unlock_reason VARCHAR(50),
    unlocked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, task_id)
);

-- ============================================================
-- 5. user_task_progress：玩家實際的任務進度(接受/進行中/完成/放棄...)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_task_progress (
    progress_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    daily_task_id INTEGER,             -- 保留給未來每日任務表用，目前程式碼一律傳 NULL
    source_type VARCHAR(20) NOT NULL DEFAULT 'npc',
    source_npc_id INTEGER REFERENCES npcs(npc_id),
    story_variant VARCHAR(10),
    status VARCHAR(20) NOT NULL DEFAULT 'accepted', -- accepted|in_progress|interrupted|completed|claimable|rewarded|abandoned|cancelled
    progress_count INTEGER NOT NULL DEFAULT 0,
    target_count INTEGER,
    progress_seconds INTEGER NOT NULL DEFAULT 0,
    target_seconds INTEGER,
    accepted_at TIMESTAMP,
    completed_at TIMESTAMP,
    rewarded_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 6. task_prerequisites：任務前置條件(要先完成某任務才能解鎖)
-- ============================================================
CREATE TABLE IF NOT EXISTS task_prerequisites (
    task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    prerequisite_task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    required_status VARCHAR(20) NOT NULL DEFAULT 'completed', -- completed | rewarded
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (task_id, prerequisite_task_id)
);

-- ============================================================
-- 7. task_story_steps：任務對話文字(依 story_variant 分支)
-- ============================================================
CREATE TABLE IF NOT EXISTS task_story_steps (
    step_id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    story_variant VARCHAR(10) NOT NULL DEFAULT 'A',
    story_phase VARCHAR(20) NOT NULL DEFAULT 'offer', -- intro | offer (目前程式碼只用到這兩種)
    step_order INTEGER NOT NULL DEFAULT 0,
    dialogue_text TEXT
);

-- ============================================================
-- 8. user_task_test_replays：管理後台「重新開放測試」用的一次性通行證
-- ============================================================
CREATE TABLE IF NOT EXISTS user_task_test_replays (
    replay_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    reason TEXT,
    created_by VARCHAR(30),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    used_progress_id INTEGER REFERENCES user_task_progress(progress_id)
);

-- ============================================================
-- 9. 示範資料：把原本 npc_dialogues 時代的「小兔子」+ 手/腳/壓力球 三個任務
--    搬到新架構，才能實際測試「點 NPC -> 領任務 -> 感測器類型」這條路
-- ============================================================
INSERT INTO npcs (npc_key, scene_id, npc_name, description, image_key, is_active)
SELECT 'rabbit', 0, '小兔子', '住在農場旁邊，會找玩家一起做運動的小兔子。', 'rabbit_avatar', TRUE
WHERE NOT EXISTS (SELECT 1 FROM npcs WHERE npc_key = 'rabbit');

INSERT INTO tasks (
    task_key, task_name, task_description, task_category, task_type, task_mode,
    scene_id, exercise_type, goal_type, target_count, input_requirement, required_ball_count,
    recurrence_type, reward_player_exp, reward_scene_exp, reward_money,
    is_initial_unlock, is_active
)
SELECT 'FARM_HAND_BICEP_CURL', '陪小兔子做手臂運動', '用手機感測手臂彎舉動作。', 'commission', 'persistent', 'basic',
    0, 'BicepCurl', 'count', 10, 'imu_required', 0,
    'daily', 100, 0, 50,
    TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE task_key = 'FARM_HAND_BICEP_CURL');

INSERT INTO tasks (
    task_key, task_name, task_description, task_category, task_type, task_mode,
    scene_id, exercise_type, goal_type, target_count, input_requirement, required_ball_count,
    recurrence_type, reward_player_exp, reward_scene_exp, reward_money,
    is_initial_unlock, is_active
)
SELECT 'FARM_LEG_RAISE', '陪小兔子動一動腿', '用手機感測抬腿動作。', 'commission', 'persistent', 'basic',
    0, 'LegRaise', 'count', 10, 'imu_required', 0,
    'daily', 100, 0, 50,
    TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE task_key = 'FARM_LEG_RAISE');

INSERT INTO tasks (
    task_key, task_name, task_description, task_category, task_type, task_mode,
    scene_id, exercise_type, goal_type, target_count, input_requirement, required_ball_count,
    recurrence_type, reward_player_exp, reward_scene_exp, reward_money,
    is_initial_unlock, is_active
)
SELECT 'FARM_BALL_GRIP', '陪小兔子練習握力', '需要壓力球感測器，訓練手掌握力。', 'commission', 'persistent', 'basic',
    0, 'Grip', 'count', 10, 'ball_required', 1,
    'daily', 100, 0, 50,
    TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE task_key = 'FARM_BALL_GRIP');

INSERT INTO npc_task_assignments (npc_id, task_id, priority, weight, is_active)
SELECT n.npc_id, t.task_id, 100, 1, TRUE
FROM npcs n, tasks t
WHERE n.npc_key = 'rabbit'
  AND t.task_key IN ('FARM_HAND_BICEP_CURL', 'FARM_LEG_RAISE', 'FARM_BALL_GRIP')
ON CONFLICT (npc_id, task_id) DO NOTHING;

INSERT INTO task_story_steps (task_id, story_variant, story_phase, step_order, dialogue_text)
SELECT t.task_id, 'A', 'offer', 1, txt.dialogue_text
FROM tasks t
JOIN (VALUES
    ('FARM_HAND_BICEP_CURL', '今天想不想陪我做點手臂運動呀？'),
    ('FARM_LEG_RAISE', '要不要陪我一起動一動腿，走遠一點的路？'),
    ('FARM_BALL_GRIP', '握著壓力球，跟我一起訓練手掌力氣吧！')
) AS txt(task_key, dialogue_text) ON txt.task_key = t.task_key
WHERE NOT EXISTS (
    SELECT 1 FROM task_story_steps s WHERE s.task_id = t.task_id AND s.story_variant = 'A'
);
