-- 建立遊戲/帳號系統實際用到的資料表
-- 欄位對齊 models/user_model.py 與 models/game_model.py 目前的查詢
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_users.sql

-- 使用者帳號 (user_model.verify_user / create_user_with_stats 用 user_id, password_hash)
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 玩家整體數值 (等級/經驗/金幣)
CREATE TABLE IF NOT EXISTS user_stats (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id),
    player_level INTEGER NOT NULL DEFAULT 1,
    player_exp INTEGER NOT NULL DEFAULT 0,
    money INTEGER NOT NULL DEFAULT 0
);

-- 場景/建築基礎資料 (1~5 號景點:農場/池塘/森林/中心...)
CREATE TABLE IF NOT EXISTS scenes (
    scene_id INTEGER PRIMARY KEY,
    scene_name VARCHAR(50)
);

INSERT INTO scenes (scene_id, scene_name) VALUES
    (0, '農場'), (1, '池塘'), (2, '森林'), (3, '中心'), (4, '果園')
ON CONFLICT (scene_id) DO NOTHING;

-- 每個使用者各場景的等級/經驗 (user_model.update_game_exp 用這張表)
CREATE TABLE IF NOT EXISTS user_scenes (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    scene_id INTEGER NOT NULL REFERENCES scenes(scene_id),
    scene_level INTEGER NOT NULL DEFAULT 1,
    scene_exp INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, scene_id)
);

-- 建築數據 (game_model.process_task_completion 用這張表, 目前 complete_task API 未被 Unity 呼叫)
CREATE TABLE IF NOT EXISTS building_stats (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    building_type INTEGER NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    current_exp INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, building_type)
);

-- 運動任務紀錄 (game_model.process_task_completion 寫入)
CREATE TABLE IF NOT EXISTS exercise_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    building_type INTEGER NOT NULL,
    exp_gained INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
