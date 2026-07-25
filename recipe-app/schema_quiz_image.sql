-- ============================================================
-- 問答題庫擴充:新增圖片題支援
-- ============================================================
-- 執行對象:test_QA_0421 資料庫
--
-- 執行方式:
--   pgAdmin → test_QA_0421 右鍵 → Query Tool → 貼上整段 → F5
--   或 PowerShell:psql -U postgres -d test_QA_0421 -f schema_quiz_image.sql
--
-- 說明:
--   此腳本為「向後相容」設計,執行後現有 40 題完全不受影響,
--   會自動被歸類為 question_type = 'text'、image_url = NULL。
-- ============================================================

BEGIN;

-- 1. 新增圖片檔名欄位(可為 NULL,文字題不需要填)
--    存放格式:'quiz/scallion.jpg'(相對於 image 資料夾)
ALTER TABLE quiz_questions
    ADD COLUMN IF NOT EXISTS image_url VARCHAR(255);

-- 2. 新增題型欄位,預設為 text
ALTER TABLE quiz_questions
    ADD COLUMN IF NOT EXISTS question_type VARCHAR(20) DEFAULT 'text';

-- 3. 保險:把可能為 NULL 的舊資料補成 'text'
UPDATE quiz_questions
SET question_type = 'text'
WHERE question_type IS NULL;

-- 4. 限制題型只能是 text 或 image(避免打錯字造成篩選失效)
ALTER TABLE quiz_questions
    DROP CONSTRAINT IF EXISTS quiz_questions_type_check;

ALTER TABLE quiz_questions
    ADD CONSTRAINT quiz_questions_type_check
    CHECK (question_type IN ('text', 'image'));

-- 5. 建立題型索引(題目變多後,依題型篩選會比較快)
CREATE INDEX IF NOT EXISTS idx_question_type
    ON quiz_questions(question_type);

COMMIT;


-- ============================================================
-- 圖片題新增範本
-- ============================================================
-- 使用前請先:
--   1. 把圖片放到 recipe-app/image/quiz/ 資料夾
--   2. image_url 填 'quiz/檔名.jpg'
--   3. question_type 一定要填 'image'
--   4. question_no 不可與現有題號重複(目前已用到 40)
-- ============================================================

INSERT INTO quiz_questions
    (question_no, question, option_a, option_b, correct_answer, explanation, image_url, question_type)
VALUES
    (41,
     '請問圖中的蔬菜是什麼?',
     '青蔥',
     '韭菜',
     'A',
     '青蔥的葉子是中空的圓管狀,韭菜的葉子則是扁平的。青蔥常用來爆香提味,韭菜則多用於水餃、炒蛋。',
     'quiz/scallion.jpg',
     'image')
ON CONFLICT (question_no) DO NOTHING;


-- ============================================================
-- 驗證:確認欄位與資料都正確
-- ============================================================

-- 看各題型各有幾題
SELECT question_type, COUNT(*) AS 題數
FROM quiz_questions
GROUP BY question_type
ORDER BY question_type;

-- 看所有圖片題
SELECT question_no, LEFT(question, 20) AS 題目, image_url, correct_answer
FROM quiz_questions
WHERE question_type = 'image'
ORDER BY question_no;
