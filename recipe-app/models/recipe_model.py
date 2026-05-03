"""
食譜資料模型 (Model)
負責所有與食譜、食材、步驟相關的資料庫操作。
不含任何 HTTP 邏輯,只專注於資料存取。

【欄位對應說明】
此 Model 透過 SQL 的 AS 別名,把資料庫的實際欄位映射成
前端期望的名稱,讓 controllers 與前端完全不用因 schema 差異而修改:
    recipes.title               → name
    recipe_ingredients.quantity → 用於組合食材字串(NULL 時顯示「適量」)
    recipe_ingredients.unit     → NULL 時不顯示
    recipe_steps.instruction    → description
"""
from config.database import get_db_conn


def fetch_all_recipes():
    """
    取得所有食譜以及對應的食材清單。

    SQL 處理重點:
    1. 食譜名稱:r.title AS name(前端用 name)
    2. 份量:整數型 servings 去小數點(2.00 → 「2 人份」)
    3. 食材字串:用 CASE 處理 quantity 與 unit 為 NULL 的狀況
       - quantity 有值:顯示「名稱 數量單位」(例如「鹽 1小匙」)
       - quantity 為 NULL:顯示「名稱 適量」
    4. FILTER (WHERE i.id IS NOT NULL):過濾沒有食材的食譜不會出現 [null]
    """
    sql = """
        SELECT
            r.id,
            r.title AS name,
            r.image_url,
            CASE
                WHEN r.servings IS NULL THEN NULL
                WHEN r.servings = floor(r.servings)
                    THEN floor(r.servings)::int::text || ' 人份'
                ELSE r.servings::text || ' 人份'
            END AS servings,
            r.category_id,
            COALESCE(
                array_agg(
                    i.name || ' ' ||
                    CASE
                        WHEN ri.quantity IS NULL THEN '適量'
                        ELSE ri.quantity::text || COALESCE(ri.unit, '')
                    END
                ) FILTER (WHERE i.id IS NOT NULL),
                ARRAY[]::text[]
            ) AS ingredients
        FROM recipes r
        LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
        LEFT JOIN ingredients i ON ri.ingredient_id = i.id
        GROUP BY r.id, r.title, r.image_url, r.servings, r.category_id
        ORDER BY r.id;
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def fetch_recipe_steps(recipe_id: int):
    """
    根據食譜 ID 取得詳細步驟,依步驟編號排序。
    instruction 欄位用 AS description 對齊前端命名。
    """
    sql = """
        SELECT
            step_number,
            instruction AS description
        FROM recipe_steps
        WHERE recipe_id = %s
        ORDER BY step_number;
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (recipe_id,))
            return cur.fetchall()
    finally:
        conn.close()