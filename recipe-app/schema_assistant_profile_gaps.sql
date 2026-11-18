-- 阿明資料缺口補強（2026-11-16）
-- 對應：AI助手後端說明.pdf「這一版已知的限制」第 2、3 項，以及過敏原詞彙對齊。
-- 全部可重複執行（IF NOT EXISTS / 只補 NULL），不會刪資料。
-- 在 PostgreSQL 中執行:
--   psql -U postgres -d sport_game -f schema_assistant_profile_gaps.sql

BEGIN;

-- ───────────── 1. 服藥、素食型態：user_profiles 補欄位 ─────────────
-- 預設值跟之前寫死的值一樣（false / 'None'），所以舊帳號行為不變。
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS is_on_medication BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS diet_type VARCHAR(10) NOT NULL DEFAULT 'None';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_profiles_diet_type_check') THEN
        -- recipe_filter 目前只認得「全素」標籤，所以只開放這兩個值；
        -- 之後要加蛋奶素，要先有對應的 recipe_tags 才有意義。
        ALTER TABLE user_profiles
            ADD CONSTRAINT user_profiles_diet_type_check CHECK (diet_type IN ('None', 'Vegan'));
    END IF;
END $$;

-- 軟質食物（need_soft）不加欄位：health_conditions 已經有「牙口不好」(poor_dental_status)，
-- 個人檔案的健康狀況勾選就能設定，由 assistant_model 直接推導。

-- ───────────── 2. 過敏原詞彙：鎖成規格的 9 個類別 ─────────────
-- 必須跟 ingredients.allergen_group 同一套詞彙，不然 recipe_filter 會靜靜地篩錯。
-- 只限制 allergen_type = 'food'；藥物/環境過敏不在阿明的範圍內。
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'user_allergies_food_vocab_check') THEN
        ALTER TABLE user_allergies
            ADD CONSTRAINT user_allergies_food_vocab_check CHECK (
                allergen_type IS DISTINCT FROM 'food'
                OR allergen_name IN ('海鮮', '乳製品', '蛋類', '麩質', '大豆', '堅果', '花生', '芝麻', '芒果')
            );
    END IF;
END $$;

-- ───────────── 3. recipe_health_evaluations：補 condition_id ─────────────
-- 原本 78 筆 condition_id 全是 NULL，篩選只能拿病名做 LIKE 比對；
-- 但 health_conditions 叫「冠狀動脈 / 心血管疾病」、這張表叫「心血管疾病」，
-- LIKE 對不起來，心血管那一層等於沒作用。補上 id 後改用 id 比對。
-- 「阿茲海默症」「便秘」不在 health_conditions 裡，維持 NULL。
UPDATE recipe_health_evaluations he
SET condition_id = hc.condition_id
FROM health_conditions hc
WHERE he.condition_id IS NULL
  AND hc.condition_key = CASE
        WHEN he.disease_name LIKE '%糖尿病%'                                   THEN 'diabetes'
        WHEN he.disease_name LIKE '%痛風%' OR he.disease_name LIKE '%尿酸%'
          OR he.disease_name LIKE '%普林%'                                     THEN 'gout'
        WHEN he.disease_name LIKE '%心血管%'                                   THEN 'cardiovascular_disease'
        WHEN he.disease_name LIKE '%高血壓%'                                   THEN 'hypertension'
        WHEN he.disease_name LIKE '%腎%'                                       THEN 'kidney_disease'
      END;

-- recipe_id 為 NULL 的 17 筆不刪：它們永遠不會被任何食譜比對到，不影響結果，
-- 要刪要補由負責食譜資料的組員決定。

COMMIT;
