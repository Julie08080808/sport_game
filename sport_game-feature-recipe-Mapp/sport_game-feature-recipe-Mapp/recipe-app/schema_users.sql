-- 此 SQL 建立支援登入功能所需的 users 資料表
-- 在 PostgreSQL 中執行(資料庫: test_rec_0404):
--   psql -U postgres -d test_rec_0404 -f schema_users.sql

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 可選:建立一筆測試帳號(帳號 admin / 密碼 1234)
INSERT INTO users (username, password)
VALUES ('admin', '1234')
ON CONFLICT (username) DO NOTHING;
