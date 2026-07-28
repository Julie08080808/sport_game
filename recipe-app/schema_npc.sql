-- NPC 對話與任務系統
-- 對齊規格書「NPC即時事件任務」邏輯:
--   - 一般委託 (commission)：可重複觸發
--   - 特殊事件 (special)：一次性，玩家完成或放棄後不再出現
--   - 主線任務 (main)：保留分類，目前規則同特殊事件 (一次性)
--
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_npc.sql

-- 每個 NPC 底下預先寫好的對話/任務內容
CREATE TABLE IF NOT EXISTS npc_dialogues (
    dialogue_id SERIAL PRIMARY KEY,
    npc_id VARCHAR(50) NOT NULL,
    npc_name VARCHAR(50) NOT NULL,
    dialogue_text TEXT NOT NULL,
    task_category VARCHAR(20) NOT NULL DEFAULT 'commission', -- main | commission | special
    action_type VARCHAR(50) NOT NULL,      -- 對應運動動作，例如 BicepCurl、ShoulderStretch
    target_scene VARCHAR(50) NOT NULL,     -- 對應要跳轉的 Unity 場景名稱
    background_key VARCHAR(50) NOT NULL,   -- 對應場景內要套用的背景/美術資源代號
    required_level INTEGER NOT NULL DEFAULT 1,
    reward_exp INTEGER NOT NULL DEFAULT 0,
    reward_coin INTEGER NOT NULL DEFAULT 0,
    is_repeatable BOOLEAN NOT NULL DEFAULT TRUE -- special/main 建議設 FALSE
);

-- 玩家對每筆對話/任務的處理紀錄 (完成/放棄)，用來排除一次性事件重複出現
CREATE TABLE IF NOT EXISTS user_task_history (
    history_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    dialogue_id INTEGER NOT NULL REFERENCES npc_dialogues(dialogue_id),
    status VARCHAR(20) NOT NULL, -- accepted | completed | abandoned | rewarded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
