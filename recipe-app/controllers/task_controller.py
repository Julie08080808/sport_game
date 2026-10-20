from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from config.database import db_transaction
from services.reward_service import lock_user,reward_task
from services.exercise_rules import RuleError,goal_met
from controllers.exercise_controller import _call

router=APIRouter(prefix='/api/tasks',tags=['Task Progress'])
class TaskRequest(BaseModel):
    user_id:int=Field(gt=0)
    task_progress_id:int=Field(gt=0)

@router.get('')
def list_tasks(user_id:int):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT p.progress_id AS task_progress_id,p.task_id,t.task_name,t.task_kind,
              p.status,p.progress_count,p.progress_seconds,p.target_count,p.target_seconds,
              p.completed_at,p.rewarded_at,p.completion_viewed_at,
              p.snapshot_player_exp,p.snapshot_scene_exp,p.snapshot_money
              FROM user_task_progress p JOIN tasks t USING(task_id)
              WHERE p.user_id=%s ORDER BY p.progress_id DESC LIMIT 100""",(user_id,))
            return {'success':True,'tasks':cur.fetchall()}

@router.post('/result/viewed')
def viewed(req:TaskRequest):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""UPDATE user_task_progress SET completion_viewed_at=COALESCE(completion_viewed_at,CURRENT_TIMESTAMP)
              WHERE progress_id=%s AND user_id=%s AND status='rewarded' RETURNING progress_id""",
              (req.task_progress_id,req.user_id))
            if not cur.fetchone():
                raise HTTPException(409,'此任務尚未發獎或不存在')
            return {'success':True}

@router.post('/reward/retry')
def retry(req:TaskRequest):
    return {'success':True,'reward':_call(reward_task,user_id=req.user_id,progress_id=req.task_progress_id)}


def _abandon(user_id,progress_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            lock_user(cur,user_id)
            cur.execute('SELECT * FROM user_task_progress WHERE user_id=%s AND progress_id=%s FOR UPDATE',(user_id,progress_id))
            p=cur.fetchone()
            if not p:
                raise RuleError('找不到本人任務')
            if p['status']=='abandoned':
                return {'success':True,'idempotent_replay':True}
            if p['status'] not in ('accepted','in_progress','interrupted'):
                raise RuleError('已完成任務不能放棄')
            if p['snapshot_goal_type'] is None:
                raise RuleError('接取快照缺失')
            if goal_met(p['snapshot_goal_type'],p['progress_count'],p['progress_seconds'],p['target_count'],p['target_seconds']):
                raise RuleError('已達標任務應發獎，不能放棄')
            cur.execute("SELECT session_id FROM exercise_sessions WHERE task_progress_id=%s AND status IN ('created','active','paused')",(progress_id,))
            if cur.fetchone():
                raise RuleError('請先同步最後成果並結束 Session，再放棄')
            cur.execute("UPDATE item_task_bindings SET status='released',resolved_at=CURRENT_TIMESTAMP WHERE task_progress_id=%s AND status='reserved'",(progress_id,))
            cur.execute("UPDATE user_task_progress SET status='abandoned',abandoned_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE progress_id=%s",(progress_id,))
            cur.execute('UPDATE user_stats SET total_abandoned_tasks=total_abandoned_tasks+1 WHERE user_id=%s',(user_id,))
            return {'success':True,'idempotent_replay':False}

@router.post('/abandon')
def abandon(req:TaskRequest):
    return _call(_abandon,user_id=req.user_id,progress_id=req.task_progress_id)
