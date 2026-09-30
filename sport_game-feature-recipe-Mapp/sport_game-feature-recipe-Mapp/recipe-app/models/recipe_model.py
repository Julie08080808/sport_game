"""
食譜資料模型 (Model) - 最終修正版
配合資料庫欄位改名後的結構 (title, quantity, instruction)
新增：標籤 (tags) 查詢
"""
from config.database import get_db_conn


def fetch_all_recipes():
    """
    取得所有食譜。
    資料庫對應 (已改名)：
    - recipes.title
    - recipe_ingredients.quantity
    新增：透過 recipe_tags / tags 撈出每道食譜的標籤陣列。

    這裡改用 LATERAL JOIN 而不是原本 GROUP BY + array_agg 的寫法：
    因為同時要撈「食材」和「標籤」兩個各自都是多對多關聯的資料，
    如果直接用兩個 LEFT JOIN 再 GROUP BY，食材和標籤會互相交叉相乘，
    導致食材筆數被重複放大（例如一道菜有 3 個食材 + 2 個標籤，
    會變成撈出 6 筆食材列）。LATERAL 讓每個子查詢各自獨立聚合，
    不會互相影響。
    """
    sql = """
        SELECT
            r.id,
            r.title AS name,
            r.image_url,
            r.servings,       -- 直接讀取文字，不執行 floor() 避錯
            r.category_id,
            COALESCE(ing.ingredients, ARRAY[]::text[]) AS ingredients,
            COALESCE(tg.tags, ARRAY[]::text[]) AS tags
        FROM recipes r
        LEFT JOIN LATERAL (
            SELECT array_agg(
                i.name || ' ' ||
                CASE
                    WHEN ri.quantity IS NULL THEN '適量'
                    ELSE ri.quantity::text || COALESCE(ri.unit, '')
                END
            ) AS ingredients
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = r.id
        ) ing ON true
        LEFT JOIN LATERAL (
            SELECT array_agg(t.name ORDER BY t.name) AS tags
            FROM recipe_tags rt
            JOIN tags t ON rt.tag_id = t.id
            WHERE rt.recipe_id = r.id
        ) tg ON true
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
def fetch_fruits_by_season():
    """取得依季節分組的水果清單（含份量），category_id = 8 為水果。"""
    sql = """
        SELECT s.name AS season, r.id, r.title AS name,
               r.image_url, fd.serving_desc
        FROM seasons s
        JOIN recipe_seasons rs ON s.id = rs.season_id
        JOIN recipes r ON rs.recipe_id = r.id
        JOIN fruit_details fd ON r.id = fd.recipe_id
        WHERE r.category_id = 8
        ORDER BY s.display_order, r.title;
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()

    grouped = {}
    for row in rows:
        grouped.setdefault(row["season"], []).append({
            "id": row["id"],
            "name": row["name"],
            "image_url": row["image_url"],
            "serving_desc": row["serving_desc"],
        })
    return [{"season": s, "fruits": grouped.get(s, [])}
            for s in ["全年", "春", "夏", "秋", "冬"]]