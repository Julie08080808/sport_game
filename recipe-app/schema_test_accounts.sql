-- ============================================================
-- 測試帳號標記（2026-11-20）
--
-- users.is_test_account：
--   TRUE  = 測試帳號：任務冷卻一律 10 秒、統計時排除
--   FALSE = 長輩帳號（預設）：正常冷卻（拒絕／準備畫面 1 分鐘、運動畫面 30 分鐘、領獎後 1 小時）
--
-- 規則：
--   1. 第一次執行（欄位還不存在）時，把「當下已經存在的所有帳號」都標成測試帳號
--      （2026-11-20 確認：現有帳號全部是測試帳號）。
--   2. 之後新註冊的帳號：名稱裡有 test（不分大小寫）= 測試帳號，其他 = 長輩帳號。
--      後端註冊時自動判斷（models/user_model.py 的 is_test_username）；這支只補標名稱有 test 的，
--      不會把任何帳號改回長輩帳號，所以重跑也不會動到已經在用的長輩帳號。
--
-- 長輩的統計請一律用 elder_users，或加條件：WHERE NOT u.is_test_account
-- 可以重複執行。執行方式（範例）：psql -U postgres -d sport -f schema_test_accounts.sql
-- ============================================================

BEGIN;

DO $$
DECLARE
    marked INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'users' AND table_schema = current_schema()
                     AND column_name = 'is_test_account') THEN
        ALTER TABLE users ADD COLUMN is_test_account BOOLEAN NOT NULL DEFAULT FALSE;
        UPDATE users SET is_test_account = TRUE;
        GET DIAGNOSTICS marked = ROW_COUNT;
        RAISE NOTICE '[T1] 已新增 is_test_account，現有 % 個帳號全部標成測試帳號', marked;
    ELSE
        RAISE NOTICE '[T1] is_test_account 已存在，不重標既有帳號';
    END IF;
END $$;

-- 名稱有 test 的一律是測試帳號（只補標，不會改回長輩）
UPDATE users SET is_test_account = TRUE
WHERE lower(username) LIKE '%test%' AND NOT is_test_account;

COMMENT ON COLUMN users.is_test_account IS '測試帳號：任務冷卻 10 秒、統計排除。2026-11-20 前的帳號全部是測試帳號；之後名稱有 test 的註冊時自動標記';

-- 統計用：只有長輩帳號
CREATE OR REPLACE VIEW elder_users AS
    SELECT user_id, username, created_at, last_login_at FROM users WHERE NOT is_test_account;

COMMIT;

-- 確認：
-- SELECT is_test_account, count(*) FROM users GROUP BY 1;
