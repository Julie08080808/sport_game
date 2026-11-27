-- 照護中心後台（獨立於 /admin，給照護中心的照護者看老人運動/飲食數據用）（2026-11-25）
--
-- 歸屬模型：老人（users）歸屬「整個照護中心」，同中心的照護者都能看中心內所有老人。
-- 指派方式：後台（/admin）手動把 users.care_center_id 指派到某個照護中心，
--           不會修改 Unity 端的註冊流程。
-- 照護者帳號是獨立的一組帳號密碼（caregiver_accounts），跟 /admin 現有的單一
-- 系統管理員帳號（.env 的 ADMIN_USERNAME/ADMIN_PASSWORD_HASH）完全分開，
-- 一個照護中心可以有多個照護者帳號，密碼雜湊格式沿用 services/admin_auth.py
-- 的 pbkdf2_sha256:<迭代次數>:<salt hex>:<hash hex>。
--
-- 可重複執行（已存在就略過），不會刪資料。
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_care_portal.sql

BEGIN;

-- ───────────── 1. 照護中心 ─────────────
CREATE TABLE IF NOT EXISTS care_centers (
    care_center_id SERIAL PRIMARY KEY,
    center_name    VARCHAR(100) NOT NULL,
    center_code    VARCHAR(30)  NOT NULL,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_care_centers_code') THEN
        ALTER TABLE care_centers ADD CONSTRAINT uq_care_centers_code UNIQUE (center_code);
    END IF;
END $$;

-- ───────────── 2. 照護者帳號（一個中心可以有多個） ─────────────
CREATE TABLE IF NOT EXISTS caregiver_accounts (
    caregiver_id    SERIAL PRIMARY KEY,
    care_center_id  INTEGER      NOT NULL REFERENCES care_centers(care_center_id) ON DELETE CASCADE,
    username        VARCHAR(50)  NOT NULL,
    password_hash   VARCHAR(200) NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_caregiver_accounts_username') THEN
        ALTER TABLE caregiver_accounts ADD CONSTRAINT uq_caregiver_accounts_username UNIQUE (username);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_caregiver_accounts_center ON caregiver_accounts(care_center_id);

-- ───────────── 3. 老人歸屬哪個照護中心（可為空＝尚未指派） ─────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS care_center_id INTEGER REFERENCES care_centers(care_center_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_care_center ON users(care_center_id);

COMMIT;
