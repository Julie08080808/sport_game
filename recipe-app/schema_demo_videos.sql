-- 運動示範影片（2026-11-20）
--
-- 示範影片照「動作」分，同一個動作的任務共用一支影片。影片代號（demo_video_key）填在每個任務
-- 開場（intro）那句對話上；Unity 準備畫面（ExercisePreparation）用同一個代號找影片：
--   選單 Tools/設定/加入運動示範影片 會把下面的代號和影片檔接好。
--
--   代號                  影片（Assets/運動示範影片-20261120-001/運動影片去聲音/）  任務
--   STEP_STANDING         腳踏步.mp4        踏步挑戰、每日踏步挑戰、森林散步
--   STEP_SEATED           坐腳踏步.mp4      坐著踏步推椰子、坐著踏步清小路（不能久站）
--   LEG_SIDE_RAISE_WALL   扶牆側抬腳.mp4    踢開椰子、清出椰子小路
--   （球類示範影片.mp4 是教「怎麼連接感測球」的，2026-11-20 使用者確認；不當動作示範，
--    改放在 Unity 連接感測球畫面的「看怎麼連線」按鈕。握球類任務的動作示範先顯示圖片）
--   BICEP_CURL            手側邊.mp4        搬地瓜（計次、計時）、拉藤蔓過小溪
--                         （檔名是「手側邊」，內容是二頭彎舉，2026-11-20 使用者確認）
--   ARM_RAISE             抬手示範影片.mp4  抬手挑戰、每日抬手挑戰、採茭白筍、伸手摘松果（2026-11-21 加入）
--
-- 還沒有影片（準備畫面會顯示空白／備用圖）：
--   雙腳踩球（水車補水、讓水車一直轉）
--   沒有影片的任務先暫停發放：schema_hide_tasks_without_video.sql
--   握球（每日握球挑戰、撈魚挑戰、穩住撈網）沒有動作示範影片，但照常發放（顯示圖片）
--
-- 另外：踢開椰子、清出椰子小路的正確（對長輩安全的）動作是「扶著牆，把腳往側邊抬起」，
-- 這裡一併把任務說明和山林猴的對話改成這個動作。
--
-- 先執行 schema_mobility_levels.sql（坐著踏步的任務要先存在）。可重複執行。
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_demo_videos.sql

BEGIN;

-- ───────────── 1. 每個任務的示範影片代號 ─────────────
UPDATE task_story_steps s
SET demo_video_key = v.video_key
FROM tasks t
JOIN (VALUES
    ('MONKEY_STEP_001',            'STEP_STANDING'),
    ('FOX_DAILY_STEP_001',         'STEP_STANDING'),
    ('MONKEY_STEP_TIME_001',       'STEP_STANDING'),
    ('MONKEY_SEATED_STEP_001',     'STEP_SEATED'),
    ('MONKEY_SEATED_STEP_002',     'STEP_SEATED'),
    ('MITU_HAND_RAISE_001',        'ARM_RAISE'),
    ('FOX_DAILY_HAND_RAISE_001',   'ARM_RAISE'),
    ('MITU_HAND_RAISE_TIME_001',   'ARM_RAISE'),
    ('MONKEY_ARM_RAISE_001',       'ARM_RAISE'),
    ('MONKEY_KICK_001',            'LEG_SIDE_RAISE_WALL'),
    ('MONKEY_KICK_TIME_001',       'LEG_SIDE_RAISE_WALL'),
    -- 握球：球類影片是教連線的，不當動作示範（照常發放，準備畫面顯示圖片）
    ('FOX_DAILY_GRIP_001',         NULL),
    ('CAT_HAND_PRESS_001',         NULL),
    ('CAT_HAND_PRESS_TIME_001',    NULL),
    ('MITU_BICEP_CURL_001',        'BICEP_CURL'),
    ('MITU_BICEP_CURL_TIME_001',   'BICEP_CURL'),
    ('MONKEY_BICEP_CURL_001',      'BICEP_CURL')
) AS v(task_key, video_key) ON v.task_key = t.task_key
WHERE s.task_id = t.task_id
  AND s.story_phase = 'intro';

-- ───────────── 2. 踢椰子改成「扶牆側抬腳」 ─────────────
UPDATE tasks SET task_description = '扶著牆壁站穩，和山林猴一起把腳往側邊抬起，把路邊的 10 顆椰子撥開。'
WHERE task_key = 'MONKEY_KICK_001';
UPDATE tasks SET task_description = '扶著牆壁站穩，和山林猴一起把腳往側邊抬起 60 秒，把小路上的椰子都撥到旁邊。'
WHERE task_key = 'MONKEY_KICK_TIME_001';

UPDATE task_story_steps s SET dialogue_text = v.line
FROM tasks t
JOIN (VALUES
    ('MONKEY_KICK_001', 2, '一手扶著牆壁站穩，拿著手機，把腳慢慢往側邊抬起再放下，每抬一次就撥開一顆椰子，一起撥開 10 顆吧！'),
    ('MONKEY_KICK_001', 3, '抬得好！椰子滾到旁邊去囉～'),
    ('MONKEY_KICK_001', 4, '剩最後幾顆椰子，記得扶好牆壁喔！'),
    ('MONKEY_KICK_001', 5, '椰子都撥開了！小路又可以走啦！'),
    ('MONKEY_KICK_TIME_001', 2, '一手扶著牆壁站穩，用舒服的節奏把腳往側邊抬起再放下，持續 60 秒，把路上的椰子都撥到旁邊！'),
    ('MONKEY_KICK_TIME_001', 4, '再一下下就好，記得扶好牆壁喔！')
) AS v(task_key, step_order, line) ON v.task_key = t.task_key
WHERE s.task_id = t.task_id
  AND s.story_variant = 'A'
  AND s.step_order = v.step_order;

COMMIT;
