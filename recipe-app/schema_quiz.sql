-- ============================================================
-- 銀髮族健康問答 - 資料表建立 + 範例資料
-- ============================================================
-- 執行前請先建立資料庫:test_QA_0421
--
-- 在 pgAdmin: 左邊 Databases 右鍵 → Create → Database → 取名 test_QA_0421
--
-- 然後執行此檔:
--   psql -U postgres -d test_QA_0421 -f schema_quiz.sql
-- 或在 pgAdmin 對 test_QA_0421 右鍵 → Query Tool → 貼上整段 → F5
-- ============================================================

-- 題目資料表
CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,                     -- 流水號(內部用)
    question_no INTEGER UNIQUE NOT NULL,       -- 題號(對外顯示用,例如 33、34)
    question TEXT NOT NULL,                    -- 題目內容
    option_a TEXT NOT NULL,                    -- 選項 A
    option_b TEXT NOT NULL,                    -- 選項 B
    correct_answer CHAR(1) NOT NULL CHECK (correct_answer IN ('A', 'B')),  -- 正確答案
    explanation TEXT NOT NULL,                 -- 解釋說明
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立題號索引(加速查詢)
CREATE INDEX IF NOT EXISTS idx_question_no ON quiz_questions(question_no);

-- ============================================================
-- 插入範例題目(可重複執行,不會重複新增)
-- ============================================================

-- 題號 33
INSERT INTO quiz_questions (question_no, question, option_a, option_b, correct_answer, explanation)
VALUES (
    33,
    '請問「稀飯」和「乾飯」,哪一個對血糖的影響比較大(升糖較快)?',
    '稀飯',
    '乾飯',
    'A',
    '稀飯煮得糜爛,腸道吸收非常快,血糖容易飆升。建議長輩如果吃稀飯,一定要配肉和蔬菜,或是改吃乾飯配湯。'
)
ON CONFLICT (question_no) DO NOTHING;

-- 題號 34
INSERT INTO quiz_questions (question_no, question, option_a, option_b, correct_answer, explanation)
VALUES (
    34,
    '長輩為了保護心血管,應該「完全不攝取油脂(滴油不沾)」嗎?',
    '是',
    '否',
    'B',
    '完全沒油會導致便秘與皮膚乾癢。重點是選「好油」,像是苦茶油、橄欖油或魚油,而不是不吃油。'
)
ON CONFLICT (question_no) DO NOTHING;

-- ============================================================
-- 驗證:確認題目都進去了
-- ============================================================
SELECT question_no, LEFT(question, 30) AS question_preview, correct_answer
FROM quiz_questions
ORDER BY question_no;
