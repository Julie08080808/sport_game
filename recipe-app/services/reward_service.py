"""One reward transaction; persisted completed attempts are retryable after app exit."""
import logging
from config.database import db_transaction
from services.exercise_rules import RuleError,goal_met

log=logging.getLogger(__name__)


def lock_user(cur,user_id):
    cur.execute('SELECT * FROM user_stats WHERE user_id=%s FOR UPDATE',(user_id,))
    row=cur.fetchone()
    if not row:
        raise RuleError('找不到玩家資料')
    return row


def reward_task(user_id,progress_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            stats=lock_user(cur,user_id)
            cur.execute('SELECT * FROM user_task_progress WHERE progress_id=%s AND user_id=%s FOR UPDATE',
                        (progress_id,user_id))
            p=cur.fetchone()
            if not p:
                raise RuleError('找不到本人任務')
            cur.execute('SELECT * FROM reward_transactions WHERE task_progress_id=%s',(progress_id,))
            original=cur.fetchone()
            if original:
                return dict(original,idempotent_replay=True)
            if p['status'] not in ('completed','claimable'):
                raise RuleError('任務尚未完成')
            if not goal_met(p['snapshot_goal_type'],p['progress_count'],p['progress_seconds'],p['target_count'],p['target_seconds']):
                raise RuleError('任務未達標')
            if any(p[k] is None for k in ('snapshot_player_exp','snapshot_scene_exp','snapshot_money')):
                raise RuleError('獎勵快照缺失')
            cur.execute('SELECT scene_id,task_kind FROM tasks WHERE task_id=%s',(p['task_id'],))
            t=cur.fetchone()
            if t['task_kind']=='daily_challenge' and p['snapshot_scene_exp']!=0:
                raise RuleError('每日自主挑戰不能增加景點進度')
            if p['snapshot_scene_exp'] not in (0,1):
                raise RuleError('景點完成數必須為0或1')
            if p['daily_task_id'] is not None:
                cur.execute('SELECT * FROM daily_tasks WHERE daily_task_id=%s FOR UPDATE',(p['daily_task_id'],))
                d=cur.fetchone()
                if not d or d['user_id']!=user_id or d['eligibility_state']=='rewarded':
                    raise RuleError('每日資格不可再次發獎')
            cur.execute("SELECT * FROM item_task_bindings WHERE task_progress_id=%s AND status='reserved' FOR UPDATE",(progress_id,))
            b=cur.fetchone()
            bonus=b['bonus_money'] if b else 0
            if b:
                cur.execute('SELECT quantity FROM inventory WHERE user_id=%s AND item_id=%s FOR UPDATE',(user_id,b['item_id']))
                inventory=cur.fetchone()
                if b['user_id']!=user_id or not inventory or inventory['quantity']<1:
                    raise RuleError('加碼券庫存不足')
            money=p['snapshot_money']+bonus
            cur.execute("""INSERT INTO reward_transactions(completion_id,user_id,reward_source_type,
                task_progress_id,scene_id,player_exp,scene_exp,money,bonus_binding_id)
                VALUES(%s,%s,'task',%s,%s,%s,%s,%s,%s) RETURNING *""",
                ('task:'+str(progress_id),user_id,progress_id,t['scene_id'],p['snapshot_player_exp'],
                 p['snapshot_scene_exp'],money,b['binding_id'] if b else None))
            reward=cur.fetchone()  # DB guard verifies eligibility and immutable snapshots.
            total_exp=stats['player_exp']+p['snapshot_player_exp']
            cur.execute('SELECT max(player_level) AS level FROM player_level_definitions WHERE required_total_exp<=%s',(total_exp,))
            level=cur.fetchone()['level']
            if level is None:
                raise RuleError('等級表缺少初始等級')
            cur.execute("""UPDATE user_stats SET player_exp=%s,player_level=%s,money=money+%s,
                total_completed_tasks=total_completed_tasks+1,updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s RETURNING money""",(total_exp,level,money,user_id))
            balance=cur.fetchone()['money']
            if money:
                cur.execute("""INSERT INTO coin_ledger(user_id,request_key,entry_type,amount,balance_after,reward_transaction_id)
                    VALUES(%s,%s,'task_reward',%s,%s,%s)""",
                    (user_id,'task:'+str(progress_id),money,balance,reward['reward_transaction_id']))
            if p['snapshot_scene_exp']:
                cur.execute("""INSERT INTO user_scenes(user_id,scene_id,scene_level,scene_exp,completed_scene_tasks)
                    VALUES(%s,%s,1,0,1) ON CONFLICT(user_id,scene_id) DO UPDATE
                    SET completed_scene_tasks=user_scenes.completed_scene_tasks+1,updated_at=CURRENT_TIMESTAMP""",
                    (user_id,t['scene_id']))
            if b:
                cur.execute('UPDATE inventory SET quantity=quantity-1,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s AND item_id=%s',
                            (user_id,b['item_id']))
                cur.execute("UPDATE item_task_bindings SET status='consumed',resolved_at=CURRENT_TIMESTAMP WHERE binding_id=%s",(b['binding_id'],))
                cur.execute("""INSERT INTO item_usage_logs(user_id,item_id,task_progress_id,quantity_used,effect_applied,binding_id)
                    VALUES(%s,%s,%s,1,'bonus_coin',%s)""",(user_id,b['item_id'],progress_id,b['binding_id']))
            cur.execute("""UPDATE user_task_progress SET status='rewarded',rewarded_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP WHERE progress_id=%s""",(progress_id,))
            if p['daily_task_id'] is not None:
                cur.execute("UPDATE daily_tasks SET eligibility_state='rewarded' WHERE daily_task_id=%s",(p['daily_task_id'],))
            return dict(reward,idempotent_replay=False)


def try_reward(user_id,progress_id):
    try:
        return reward_task(user_id,progress_id)
    except Exception:
        log.exception('Reward pending for progress %s',progress_id)
        return None


def retry_pending():
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT user_id,progress_id FROM user_task_progress
                WHERE status IN ('completed','claimable') AND snapshot_at IS NOT NULL
                ORDER BY updated_at,progress_id LIMIT 100""")
            rows=cur.fetchall()
    for row in rows:
        try_reward(row['user_id'],row['progress_id'])
