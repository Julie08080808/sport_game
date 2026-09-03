-- 益智問答遊戲題庫
-- 對齊 models/quiz_model.py 的查詢欄位 (id, question_no, question, option_a, option_b,
-- correct_answer, explanation, image_url, question_type)
-- 移植自 feature/recipe-Mapp 分支的 schema_quiz.sql + schema_quiz_image.sql，
-- 合併成單一版本，直接建在 sport_game 資料庫裡 (不再另開 test_QA_0421)。
--
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_quiz.sql

CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    question_no INTEGER UNIQUE NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    correct_answer CHAR(1) NOT NULL CHECK (correct_answer IN ('A', 'B')),
    explanation TEXT NOT NULL,
    image_url VARCHAR(255),                      -- 相對於 image 資料夾，例如 'quiz/scallion.jpg'
    question_type VARCHAR(20) NOT NULL DEFAULT 'text' CHECK (question_type IN ('text', 'image')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_question_no ON quiz_questions(question_no);
CREATE INDEX IF NOT EXISTS idx_question_type ON quiz_questions(question_type);

-- 範例題目 (文字題)
INSERT INTO quiz_questions (question_no, question, option_a, option_b, correct_answer, explanation, question_type)
VALUES (
    33,
    '請問「稀飯」和「乾飯」,哪一個對血糖的影響比較大(升糖較快)?',
    '稀飯',
    '乾飯',
    'A',
    '稀飯煮得糜爛,腸道吸收非常快,血糖容易飆升。建議長輩如果吃稀飯,一定要配肉和蔬菜,或是改吃乾飯配湯。',
    'text'
)
ON CONFLICT (question_no) DO NOTHING;

INSERT INTO quiz_questions (question_no, question, option_a, option_b, correct_answer, explanation, question_type)
VALUES (
    34,
    '長輩為了保護心血管,應該「完全不攝取油脂(滴油不沾)」嗎?',
    '是',
    '否',
    'B',
    '完全沒油會導致便秘與皮膚乾癢。重點是選「好油」,像是苦茶油、橄欖油或魚油,而不是不吃油。',
    'text'
)
ON CONFLICT (question_no) DO NOTHING;

-- 範例題目 (圖片題)
INSERT INTO quiz_questions (question_no, question, option_a, option_b, correct_answer, explanation, image_url, question_type)
VALUES (
    41,
    '請問圖中的蔬菜是什麼?',
    '青蔥',
    '韭菜',
    'A',
    '青蔥的葉子是中空的圓管狀,韭菜的葉子則是扁平的。青蔥常用來爆香提味,韭菜則多用於水餃、炒蛋。',
    'quiz/scallion.jpg',
    'image'
)
ON CONFLICT (question_no) DO NOTHING;
