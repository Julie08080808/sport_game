"""
食譜資料模型 (Model) - 最終修正版
配合資料庫欄位改名後的結構 (title, quantity, instruction)
"""
from config.database import get_db_conn


def fetch_all_recipes():
    """
    取得所有食譜。
    資料庫對應 (已改名)：
    - recipes.title
    - recipe_ingredients.quantity
    """
    sql = """
        SELECT
            r.id,
            r.title AS name,
            r.image_url,
            r.servings,       -- 直接讀取文字，不執行 floor() 避錯
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
    取得步驟。
    資料庫對應 (已改名)：recipe_steps.instruction
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