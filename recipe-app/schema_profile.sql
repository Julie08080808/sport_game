-- 「個人檔案」模組（SilverHealth）需要的欄位與資料表。
-- user_profiles 已有 name/height/weight/birthday，這裡只補它沒有的欄位；
-- health_conditions/user_health_conditions 已存在（user_health_conditions 是「有一列＝有這個狀況」，
-- 沒有 has_condition 布林欄位），直接重用，不重建。
-- outfits/achievements/user_settings 整張表都是新的。
--
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport -f schema_profile.sql

ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS real_name VARCHAR(100);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS equipped_outfit_id INTEGER;

CREATE TABLE IF NOT EXISTS outfits (
    outfit_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_outfits (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    outfit_id INTEGER NOT NULL REFERENCES outfits(outfit_id),
    unlocked BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, outfit_id)
);

CREATE TABLE IF NOT EXISTS achievements (
    achievement_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(200),
    icon VARCHAR(100),
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    achievement_id INTEGER NOT NULL REFERENCES achievements(achievement_id),
    achieved BOOLEAN NOT NULL DEFAULT FALSE,
    achieved_at TIMESTAMP,
    is_displayed BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(user_id),
    font_size INTEGER NOT NULL DEFAULT 80,
    master_volume REAL NOT NULL DEFAULT 0.8,
    sfx_volume REAL NOT NULL DEFAULT 0.8,
    music_volume REAL NOT NULL DEFAULT 0.6,
    tts_enabled BOOLEAN NOT NULL DEFAULT FALSE
);

-- 預設一套「日常便服」，所有人預設解鎖，equipped_outfit_id 沒設定時以這套為準。
INSERT INTO outfits (name, is_default, sort_order)
SELECT '日常便服', TRUE, 1
WHERE NOT EXISTS (SELECT 1 FROM outfits WHERE is_default = TRUE);

-- ── 成就自動解鎖（見 models/profile_model.py 的 _evaluate_achievements）──
-- condition_key 給程式對應判斷邏輯用，不要用會變動的中文 name 比對。
ALTER TABLE achievements ADD COLUMN IF NOT EXISTS condition_key VARCHAR(50);
UPDATE achievements SET condition_key = 'first_login' WHERE name = '初次登入' AND condition_key IS NULL;
-- 不加 WHERE 條件：Postgres 的一般 UNIQUE 索引本來就允許多個 NULL，
-- 但 ON CONFLICT (condition_key) 只有在非 partial 索引才能用來推斷目標。
CREATE UNIQUE INDEX IF NOT EXISTS achievements_condition_key_uq
    ON achievements (condition_key);

INSERT INTO achievements (condition_key, name, description, icon, sort_order) VALUES
    ('first_login',      '初次登入',     '第一次開啟 App', '', 1),
    ('streak_3',         '連續運動 3 天', '連續 3 天完成運動', '', 2),
    ('first_exercise',   '運動新手',     '完成第一次運動', '', 3),
    ('total_days_28',    '運動一個月',   '累積運動 28 天', '', 4),
    ('diet_variety_5',   '飲食達人',     '某週飲食多樣性獲得滿分評價', '', 5),
    ('streak_7',         '持之以恆',     '連續 7 天完成運動', '', 6)
ON CONFLICT (condition_key) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    sort_order = EXCLUDED.sort_order;

-- ── 飲食週報（PhotoManager.GetWeeklyObservation 算出的蔬菜/油炸/多樣性星等，同步進來）──
CREATE TABLE IF NOT EXISTS user_weekly_diet_reviews (
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    week_monday DATE NOT NULL,
    vegetable_score SMALLINT,
    fried_score SMALLINT,
    variety_score SMALLINT,
    ai_observation TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, week_monday)
);
