"""
商店資料模型 (Model)
負責商品清單查詢、購買結算(扣金幣、寫入庫存)、玩家庫存查詢。
"""
from config.database import get_db_conn


def fetch_shop_items():
    """
    取得所有上架中的商品,依分類/價格排序。
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT item_id, item_name, description, price, icon_url, category
                FROM shop_items
                WHERE is_active = TRUE
                ORDER BY category, price;
            """)
            return cur.fetchall()
    finally:
        conn.close()


def purchase_item(user_id: int, item_id: int, quantity: int = 1):
    """
    購買商品:
    1. 查商品單價(需為上架中)
    2. 扣款(SQL 層直接檢查 money 是否足夠,避免競爭條件下超扣)
    3. 寫入/累加玩家庫存(user_items)
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT price, item_name FROM shop_items WHERE item_id = %s AND is_active = TRUE;",
                (item_id,)
            )
            item = cur.fetchone()
            if not item:
                return {"success": False, "message": "商品不存在或已下架"}

            total_cost = item["price"] * quantity

            cur.execute("""
                UPDATE user_stats
                SET money = money - %s
                WHERE user_id = %s AND money >= %s
                RETURNING money;
            """, (total_cost, user_id, total_cost))
            stats = cur.fetchone()

            if not stats:
                conn.rollback()
                return {"success": False, "message": "金幣不足"}

            cur.execute("""
                INSERT INTO user_items (user_id, item_id, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = user_items.quantity + EXCLUDED.quantity
                RETURNING quantity;
            """, (user_id, item_id, quantity))
            owned = cur.fetchone()

            conn.commit()
            return {
                "success": True,
                "message": f"已購買「{item['item_name']}」x{quantity}",
                "item_id": item_id,
                "item_name": item["item_name"],
                "quantity_owned": owned["quantity"],
                "money": stats["money"],
            }
    except Exception as e:
        conn.rollback()
        print(f"[Database Error] 購買失敗: {e}")
        return {"success": False, "message": "購買失敗,請稍後再試"}
    finally:
        conn.close()


def fetch_user_inventory(user_id: int):
    """
    取得玩家已擁有的商品(數量 > 0)。
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT si.item_id, si.item_name, si.icon_url, si.category, ui.quantity
                FROM user_items ui
                JOIN shop_items si ON si.item_id = ui.item_id
                WHERE ui.user_id = %s AND ui.quantity > 0
                ORDER BY si.category, si.item_name;
            """, (user_id,))
            return cur.fetchall()
    finally:
        conn.close()
