from typing import Optional
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from config.database import db_transaction
from services.reward_service import lock_user,reward_task
from services.exercise_rules import RuleError,goal_met
from controllers.exercise_controller import _call
from models.npc_model import expire_stale_progress

router=APIRouter(prefix='/api/tasks',tags=['Task Progress'])
class TaskRequest(BaseModel):
    user_id:int=Field(gt=0)
    task_progress_id:int=Field(gt=0)

ABANDON_REASONS={'manual','challenge_timeout'}
class AbandonRequest(BaseModel):
    user_id:int=Field(gt=0)
    task_progress_id:int=Field(gt=0)
    reason:str='manual'

@router.get('')
def list_tasks(user_id:int):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            expire_stale_progress(cur,user_id)
            cur.execute("""SELECT p.progress_id AS task_progress_id,p.task_id,t.task_name,t.task_kind,
              p.status,p.progress_count,p.progress_seconds,p.target_count,p.target_seconds,
              p.completed_at,p.rewarded_at,p.completion_viewed_at,
              p.snapshot_player_exp,p.snapshot_scene_exp,p.snapshot_money
              FROM user_task_progress p JOIN tasks t USING(task_id)
              WHERE p.user_id=%s ORDER BY p.progress_id DESC LIMIT 100""",(user_id,))
            return {'success':True,'tasks':cur.fetchall()}

@router.get('/folder')
def folder(user_id:int,date:Optional[str]=None):
    # 資料夾＝歷史紀錄：query 帶 date(YYYY-MM-DD) 查某一天的完成/放棄紀錄，不帶 date 預設查今天。
    # 待領獎的任務(completed/claimable)不受 date 篩選，不管哪天都會出現，直到玩家領取為止。
    with db_transaction() as conn:
        with conn.cursor() as cur:
            expire_stale_progress(cur,user_id)
            cur.execute("""SELECT p.progress_id AS task_progress_id,p.task_id,p.source_npc_id AS npc_id,
              t.task_name,t.task_kind,t.task_category,
              p.status,p.abandon_reason,p.progress_count,p.progress_seconds,p.target_count,p.target_seconds,
              p.accepted_at,p.completed_at,
              COALESCE(p.abandoned_at,p.rewarded_at,p.completed_at) AS record_at,
              (p.status IN ('accepted','in_progress','interrupted')) AS can_resume,
              (p.status IN ('in_progress','interrupted')
                 AND CURRENT_TIMESTAMP - COALESCE(p.last_progress_at,p.accepted_at) > INTERVAL '1 hour') AS progress_will_reset
              FROM user_task_progress p JOIN tasks t USING(task_id)
              WHERE p.user_id=%s AND (
                p.status IN ('completed','claimable')
                OR COALESCE(p.abandoned_at,p.rewarded_at,p.completed_at)::date = COALESCE(%s::date,CURRENT_DATE)
              )
              ORDER BY p.accepted_at DESC""",(user_id,date))
            return {'success':True,'tasks':cur.fetchall()}

@router.get('/folder/calendar')
def folder_calendar(user_id:int,year:int,month:int):
    # 給月曆用：回傳該年月裡「有完成或放棄紀錄」的日期清單，前端用來在格子上畫標記點。
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT DISTINCT COALESCE(abandoned_at,rewarded_at,completed_at)::date AS d
              FROM user_task_progress
              WHERE user_id=%s AND status IN ('completed','claimable','abandoned','rewarded')
                AND EXTRACT(YEAR FROM COALESCE(abandoned_at,rewarded_at,completed_at))=%s
                AND EXTRACT(MONTH FROM COALESCE(abandoned_at,rewarded_at,completed_at))=%s""",
              (user_id,year,month))
            return {'success':True,'dates':[row['d'].isoformat() for row in cur.fetchall()]}

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


def _abandon(user_id,progress_id,reason='manual'):
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
            cur.execute("UPDATE user_task_progress SET status='abandoned',abandoned_at=CURRENT_TIMESTAMP,abandon_reason=%s,updated_at=CURRENT_TIMESTAMP WHERE progress_id=%s",(reason,progress_id))
            cur.execute('UPDATE user_stats SET total_abandoned_tasks=total_abandoned_tasks+1 WHERE user_id=%s',(user_id,))
            return {'success':True,'idempotent_replay':False}

@router.post('/abandon')
def abandon(req:AbandonRequest):
    reason=req.reason if req.reason in ABANDON_REASONS else 'manual'
    return _call(_abandon,user_id=req.user_id,progress_id=req.task_progress_id,reason=reason)
