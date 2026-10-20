"""
商店資料模型 (Model)
負責商品清單查詢、購買結算(扣金幣、寫入庫存)、玩家庫存查詢。
"""
from uuid import UUID
from config.database import db_transaction
from services.exercise_rules import RuleError
from services.reward_service import lock_user


def purchase_terms(item, quantity, owned, money):
    if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 100:
        raise RuleError('購買份數必須為1到100')
    if not item or not item['is_active'] or not item['is_shop_item'] or not item['can_purchase']:
        raise RuleError('商品尚未開放購買或已下架')
    permanent = not item['is_consumable']
    if permanent and (quantity != 1 or owned > 0):
        raise RuleError('永久道具只能購買一次且每次一份')
    pack = item['purchase_quantity']
    price = item['price']
    if price is None or price < 0 or pack < 1 or (permanent and pack != 1):
        raise RuleError('商品價格或包裝設定不合法')
    cost = price*quantity
    if cost > money:
        raise RuleError('金幣不足')
    if cost > 2147483647 or pack*quantity+owned > 2147483647:
        raise RuleError('購買數量超出上限')
    return cost, pack*quantity, permanent


def fetch_shop_items():
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute('''SELECT *,image_key AS icon_url,item_type AS category FROM items
                WHERE is_active AND is_shop_item ORDER BY price,item_id''')
            return [dict(r) for r in cur.fetchall()]


def fetch_user_inventory(user_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            lock_user(cur, user_id)
            cur.execute('''SELECT i.item_id,i.item_key,i.item_name,i.image_key,i.image_key AS icon_url,
                i.item_type AS category,i.is_consumable,i.effect_type,i.effect_value,v.quantity,
                (SELECT count(*) FROM item_task_bindings b WHERE b.user_id=v.user_id AND b.item_id=v.item_id AND b.status='reserved') AS reserved_quantity
                FROM inventory v JOIN items i USING(item_id) WHERE v.user_id=%s AND v.quantity>0 ORDER BY i.item_id''', (user_id,))
            return [dict(r, available_quantity=max(0, r['quantity']-r['reserved_quantity'])) for r in cur.fetchall()]


def purchase_item(user_id, item_id, quantity, request_id):
    request = str(UUID(str(request_id)))
    with db_transaction() as conn:
        with conn.cursor() as cur:
            stats = lock_user(cur, user_id)
            cur.execute(
                'SELECT * FROM shop_purchases WHERE user_id=%s AND request_id=%s', (user_id, request))
            old = cur.fetchone()
            if old and (old['item_id'], old['quantity']) != (item_id, quantity):
                raise RuleError('同一購買請求不能改變商品或份數')
            if old:
                cur.execute(
                    'SELECT quantity FROM inventory WHERE user_id=%s AND item_id=%s', (user_id, item_id))
                row = cur.fetchone()
                return dict(success=True, idempotent_replay=True, purchase=dict(old), quantity_owned=row['quantity'] if row else 0, money=stats['money'])
            cur.execute(
                'SELECT * FROM items WHERE item_id=%s FOR SHARE', (item_id,))
            item = cur.fetchone()
            cur.execute(
                'SELECT quantity FROM inventory WHERE user_id=%s AND item_id=%s FOR UPDATE', (user_id, item_id))
            inv = cur.fetchone()
            owned = inv['quantity'] if inv else 0
            cost, added, permanent = purchase_terms(
                item, quantity, owned, stats['money'])
            if permanent:
                cur.execute(
                    'SELECT purchase_id FROM shop_purchases WHERE user_id=%s AND item_id=%s AND permanent_purchase', (user_id, item_id))
                if cur.fetchone():
                    raise RuleError('永久道具已購買')
            cur.execute(
                'UPDATE user_stats SET money=money-%s,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s RETURNING money', (cost, user_id))
            balance = cur.fetchone()['money']
            ledger = None
            if cost:
                cur.execute("INSERT INTO coin_ledger(user_id,request_key,entry_type,amount,balance_after) VALUES(%s,%s,'shop_purchase',%s,%s) RETURNING ledger_id",
                            (user_id, 'shop:'+request, -cost, balance))
                ledger = cur.fetchone()['ledger_id']
            cur.execute('''INSERT INTO inventory(user_id,item_id,quantity) VALUES(%s,%s,%s)
                ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=inventory.quantity+EXCLUDED.quantity,updated_at=CURRENT_TIMESTAMP RETURNING quantity''', (user_id, item_id, added))
            owned = cur.fetchone()['quantity']
            cur.execute('''INSERT INTO shop_purchases(user_id,item_id,request_id,quantity,unit_price,pack_size,total_cost,permanent_purchase,coin_ledger_id)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''', (user_id, item_id, request, quantity, item['price'], item['purchase_quantity'], cost, permanent, ledger))
            return dict(success=True, idempotent_replay=False, purchase=dict(cur.fetchone()), item_id=item_id, item_name=item['item_name'], quantity_owned=owned, money=balance)


def bind_bonus(user_id, task_progress_id, bind_request_id):
    request = str(UUID(str(bind_request_id)))
    with db_transaction() as conn:
        with conn.cursor() as cur:
            lock_user(cur, user_id)
            cur.execute(
                'SELECT * FROM item_task_bindings WHERE user_id=%s AND bind_request_id=%s', (user_id, request))
            old = cur.fetchone()
            if old:
                if old['task_progress_id'] != task_progress_id:
                    raise RuleError('同一綁定請求不能換任務')
                return dict(success=True, idempotent_replay=True, binding=dict(old))
            cur.execute('SELECT * FROM user_task_progress WHERE user_id=%s AND progress_id=%s FOR UPDATE',
                        (user_id, task_progress_id))
            p = cur.fetchone()
            if not p or p['status'] != 'accepted' or p['started_at'] is not None or p['progress_count'] or p['progress_seconds']:
                raise RuleError('只能在本人任務開始運動前綁定')
            if p['snapshot_money'] is None:
                raise RuleError('任務缺少獎勵快照')
            cur.execute(
                "SELECT 1 FROM item_task_bindings WHERE task_progress_id=%s AND status IN ('reserved','consumed')", (task_progress_id,))
            if cur.fetchone():
                raise RuleError('此任務已有加碼券')
            cur.execute(
                "SELECT item_id,effect_value FROM items WHERE item_key='REWARD_BONUS_TICKET' AND is_active")
            item = cur.fetchone()
            if not item:
                raise RuleError('加碼券尚未開放')
            cur.execute(
                'SELECT quantity FROM inventory WHERE user_id=%s AND item_id=%s FOR UPDATE', (user_id, item['item_id']))
            inv = cur.fetchone()
            cur.execute(
                "SELECT count(*) AS reserved FROM item_task_bindings WHERE user_id=%s AND item_id=%s AND status='reserved'", (user_id, item['item_id']))
            reserved = cur.fetchone()['reserved']
            if not inv or inv['quantity'] <= reserved:
                raise RuleError('沒有可用加碼券')
            cur.execute('''INSERT INTO item_task_bindings(user_id,item_id,task_progress_id,bonus_money,bind_request_id)
                VALUES(%s,%s,%s,%s,%s) RETURNING *''', (user_id, item['item_id'], task_progress_id, item['effect_value'], request))
            return dict(success=True, idempotent_replay=False, binding=dict(cur.fetchone()))
