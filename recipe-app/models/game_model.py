from uuid import UUID
from config.database import db_transaction
from services.exercise_rules import RuleError
from services.reward_service import lock_user


def upgrade_rule(scene, definition, money):
    if not definition:
        raise RuleError('此景點沒有下一階設定')
    if definition['scene_level'] != scene['scene_level']+1:
        raise RuleError('只能購買下一階')
    if scene['completed_scene_tasks'] < definition['required_total_tasks']:
        raise RuleError('景點任務完成數不足')
    if money < definition['unlock_cost']:
        raise RuleError('金幣不足')


def _scene(cur, user_id, scene_id):
    cur.execute(
        'SELECT scene_id FROM scenes WHERE scene_id=%s AND is_active', (scene_id,))
    if not cur.fetchone():
        raise RuleError('景點不存在或未啟用')
    cur.execute('INSERT INTO user_scenes(user_id,scene_id) VALUES(%s,%s) ON CONFLICT(user_id,scene_id) DO NOTHING', (user_id, scene_id))
    cur.execute(
        'SELECT * FROM user_scenes WHERE user_id=%s AND scene_id=%s FOR UPDATE', (user_id, scene_id))
    return cur.fetchone()


def get_all_scene_status(user_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            stats = lock_user(cur, user_id)
            cur.execute(
                'INSERT INTO user_scenes(user_id,scene_id) SELECT %s,scene_id FROM scenes WHERE is_active ON CONFLICT(user_id,scene_id) DO NOTHING', (user_id,))
            cur.execute('''SELECT us.*,s.scene_key,s.scene_name,a.required_level AS selected_level
                FROM user_scenes us JOIN scenes s USING(scene_id)
                LEFT JOIN scene_appearance_stages a ON a.appearance_stage_id=us.current_selected_appearance_stage_id
                WHERE us.user_id=%s AND s.is_active ORDER BY us.scene_id''', (user_id,))
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute(
                'SELECT * FROM scene_level_definitions ORDER BY scene_id,scene_level')
            definitions = cur.fetchall()
            for r in rows:
                nxt = next(
                    (d for d in definitions if d['scene_id'] == r['scene_id'] and d['scene_level'] == r['scene_level']+1), None)
                # compatibility alias; cumulative, never reset
                r['completion_count'] = r['completed_scene_tasks']
                r['display_level_cap'] = r.pop('selected_level') or -1
                r['next_level'] = dict(nxt) if nxt else None
                r['tasks_remaining'] = max(
                    0, nxt['required_total_tasks']-r['completed_scene_tasks']) if nxt else 0
                r['can_upgrade'] = bool(
                    nxt and r['tasks_remaining'] == 0 and stats['money'] >= nxt['unlock_cost'])
            return rows


def purchase_scene_level(user_id, scene_id, target_level, request_id):
    request = str(UUID(str(request_id)))
    with db_transaction() as conn:
        with conn.cursor() as cur:
            stats = lock_user(cur, user_id)
            cur.execute(
                'SELECT * FROM scene_level_purchases WHERE user_id=%s AND request_id=%s', (user_id, request))
            old = cur.fetchone()
            if old:
                if (old['scene_id'], old['scene_level']) != (scene_id, target_level):
                    raise RuleError('同一購買請求不能更換景點或階級')
                return dict(success=True, idempotent_replay=True, purchase=dict(old), money=stats['money'])
            scene = _scene(cur, user_id, scene_id)
            cur.execute(
                'SELECT * FROM scene_level_definitions WHERE scene_id=%s AND scene_level=%s', (scene_id, target_level))
            definition = cur.fetchone()
            upgrade_rule(scene, definition, stats['money'])
            cost = definition['unlock_cost']
            cur.execute(
                'UPDATE user_stats SET money=money-%s,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s RETURNING money', (cost, user_id))
            balance = cur.fetchone()['money']
            cur.execute("INSERT INTO coin_ledger(user_id,request_key,entry_type,amount,balance_after) VALUES(%s,%s,'scene_unlock',%s,%s) RETURNING ledger_id",
                        (user_id, 'scene:'+request, -cost, balance))
            ledger = cur.fetchone()['ledger_id']
            cur.execute('''INSERT INTO scene_level_purchases(user_id,scene_id,scene_level,request_id,required_total_tasks,cost,coin_ledger_id)
                VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING *''', (user_id, scene_id, target_level, request, definition['required_total_tasks'], cost, ledger))
            purchase = dict(cur.fetchone())
            cur.execute('UPDATE user_scenes SET scene_level=%s,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s AND scene_id=%s',
                        (target_level, user_id, scene_id))
            return dict(success=True, idempotent_replay=False, purchase=purchase, money=balance)


def get_appearances(user_id, scene_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            lock_user(cur, user_id)
            scene = _scene(cur, user_id, scene_id)
            cur.execute(
                'SELECT * FROM scene_appearance_stages WHERE scene_id=%s AND is_active ORDER BY required_level,sort_order,appearance_stage_id', (scene_id,))
            return [dict(r, is_unlocked=r['required_level'] <= scene['scene_level'], is_selected=r['appearance_stage_id'] == scene['current_selected_appearance_stage_id']) for r in cur.fetchall()]


def select_appearance(user_id, scene_id, appearance_stage_id=None, display_level=None):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            lock_user(cur, user_id)
            scene = _scene(cur, user_id, scene_id)
            chosen = None
            if appearance_stage_id is not None:
                cur.execute('SELECT * FROM scene_appearance_stages WHERE appearance_stage_id=%s AND scene_id=%s AND is_active',
                            (appearance_stage_id, scene_id))
                chosen = cur.fetchone()
            elif display_level != -1:
                if display_level is None or not 1 <= display_level <= scene['scene_level']:
                    raise RuleError('外觀階級必須已解鎖，或傳 -1 恢復自動')
                cur.execute('SELECT * FROM scene_appearance_stages WHERE scene_id=%s AND required_level=%s AND is_active ORDER BY is_default DESC,sort_order,appearance_stage_id LIMIT 1', (scene_id, display_level))
                chosen = cur.fetchone()
            if (appearance_stage_id is not None or display_level != -1) and not chosen:
                raise RuleError('尚未設定此景點外觀資產')
            if chosen and chosen['required_level'] > scene['scene_level']:
                raise RuleError('此外觀尚未解鎖')
            if chosen:
                cur.execute('INSERT INTO user_scene_appearance_unlocks(user_id,appearance_stage_id) VALUES(%s,%s) ON CONFLICT DO NOTHING',
                            (user_id, chosen['appearance_stage_id']))
            cur.execute('UPDATE user_scenes SET current_selected_appearance_stage_id=%s,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s AND scene_id=%s',
                        (chosen['appearance_stage_id'] if chosen else None, user_id, scene_id))
            return dict(success=True, scene_id=scene_id, scene_level=scene['scene_level'], current_selected_appearance_stage_id=chosen['appearance_stage_id'] if chosen else None, display_level_cap=chosen['required_level'] if chosen else -1)


def set_scene_display_level(user_id, scene_id, display_level):
    return select_appearance(user_id, scene_id, display_level=display_level)


def process_task_completion(*args, **kwargs):
    raise RuleError('請使用 Session 同步與後端發獎')
