-- ============================================================
-- 暫停發放還沒有示範影片的任務（2026-11-20）
--
-- 使用者決定：沒有示範影片的任務先不要讓 NPC 發，等影片做好、使用者說「開啟」再開。
-- 做法：tasks.is_listed = FALSE（NPC 不主動發放）。不刪資料、不影響歷史紀錄，
-- 管理後台「NPC 主動發放」打勾、或把下面清單改成 TRUE 再跑一次就能重新開啟。
--
-- 這次暫停的 6 個任務（還沒有示範影片）：
--   咪兔   抬手挑戰 MITU_HAND_RAISE_001、採茭白筍 MITU_HAND_RAISE_TIME_001（抬手）
--   老山狐 每日抬手挑戰 FOX_DAILY_HAND_RAISE_001（抬手）
--   姜太喵 水車補水 CAT_FOOT_PRESS_001、讓水車一直轉 CAT_FOOT_PRESS_TIME_001（雙腳踩球）
--   山林猴 伸手摘松果 MONKEY_ARM_RAISE_001（抬手）
-- 有影片的照常發放：咪兔「搬地瓜」×2、山林猴「拉藤蔓過小溪」用二頭彎舉影片（BICEP_CURL，手側邊.mp4）。
--
-- 重新開啟某個任務（影片做好後）：
--   1. Unity 加影片：DemoVideoSetup.cs 的 Videos 加一行，點選單 Tools/設定/加入運動示範影片
--   2. 後端：schema_demo_videos.sql 加上那個任務的影片代號並執行
--   3. UPDATE tasks SET is_listed = TRUE WHERE task_key = '任務代號';
--
-- 要在 schema_demo_videos.sql 之後執行。可以重複執行。
-- 執行方式（範例）：psql -U postgres -d sport -f schema_hide_tasks_without_video.sql
-- ============================================================

BEGIN;

DO $$
DECLARE
    hidden INTEGER;
BEGIN
    UPDATE tasks SET is_listed = FALSE
    WHERE task_key IN (
        'MITU_HAND_RAISE_001',
        'MITU_HAND_RAISE_TIME_001',
        'FOX_DAILY_HAND_RAISE_001',
        'CAT_FOOT_PRESS_001',
        'CAT_FOOT_PRESS_TIME_001',
        'MONKEY_ARM_RAISE_001'
    )
    AND is_listed;
    GET DIAGNOSTICS hidden = ROW_COUNT;
    RAISE NOTICE '[V1] 暫停發放 % 個沒有示範影片的任務', hidden;
END $$;

COMMIT;

-- 確認（應該列出上面 6 個，is_listed = f）：
-- SELECT task_key, task_name, is_listed FROM tasks WHERE NOT is_listed AND is_active ORDER BY task_key;
