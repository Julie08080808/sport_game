-- 登入 session token
-- 給 /api/assistant/chat 用：user_id 一律要從這張表查出來，不能從請求參數拿（IDOR）。
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_assistant_sessions.sql

CREATE TABLE IF NOT EXISTS user_sessions (
    token VARCHAR(64) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
