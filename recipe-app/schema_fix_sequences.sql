-- 對齊所有自動編號（sequence）（2026-11-21）
-- 症狀：跑 SQL 時出現 duplicate key value violates unique constraint "xxx_pkey"、
--       Key (xxx_id)=(182) already exists。
-- 原因：資料庫是用匯入的，資料進來了，但自動編號的計數器還停在比較小的數字，
--       下一筆新增就拿到已經被用掉的編號。
-- 做法：每個用自動編號的欄位，計數器比表裡最大的編號還小的，就調到最大的編號。
--       只會往上調，不會往回調；不改任何資料列。可以重複執行。
-- 執行（Docker 伺服器）：
--   docker compose exec -T db psql -U postgres -d sport -v ON_ERROR_STOP=1 < sport_game/recipe-app/schema_fix_sequences.sql

DO $$
DECLARE
    r       record;
    max_id  bigint;
    cur_val bigint;
    called  boolean;
    fixed   int := 0;
BEGIN
    FOR r IN
        SELECT n.nspname AS schema_name, c.relname AS table_name, a.attname AS column_name,
               pg_get_serial_sequence(format('%I.%I', n.nspname, c.relname), a.attname) AS seq
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
         WHERE c.relkind = 'r'
           AND n.nspname = 'public'
    LOOP
        CONTINUE WHEN r.seq IS NULL;

        EXECUTE format('SELECT max(%I)::bigint FROM %I.%I', r.column_name, r.schema_name, r.table_name)
           INTO max_id;
        CONTINUE WHEN max_id IS NULL;

        EXECUTE format('SELECT last_value, is_called FROM %s', r.seq) INTO cur_val, called;

        -- 下一個會拿到的編號：is_called 時是 last_value + 1，否則是 last_value
        IF (CASE WHEN called THEN cur_val + 1 ELSE cur_val END) <= max_id THEN
            PERFORM setval(r.seq, max_id, true);
            fixed := fixed + 1;
            RAISE NOTICE '[S1] %.% 的編號從 % 調到 %（下一筆是 %）',
                r.table_name, r.column_name, cur_val, max_id, max_id + 1;
        END IF;
    END LOOP;

    RAISE NOTICE '[S1] 共調整 % 個自動編號', fixed;
END $$;
