"""V1.2 sessions: lock user -> progress -> session; cumulative deltas only."""
from uuid import UUID
from config.database import db_transaction
from services.exercise_rules import RuleError, validate_goal, goal_met, evaluate_sync
from services.reward_service import lock_user, try_reward


class OpenSessionExists(RuleError):
    def __init__(self, session_id, task_progress_id):
        super().__init__('已有未結束運動，請繼續或結束原 Session')
        self.session_id = session_id
        self.task_progress_id = task_progress_id


def _progress(cur, user_id, progress_id):
    cur.execute('SELECT * FROM user_task_progress WHERE progress_id=%s AND user_id=%s FOR UPDATE',
                (progress_id, user_id))
    p = cur.fetchone()
    if not p:
        raise RuleError('找不到本人任務')
    return p


def get_session(user_id, session_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT * FROM exercise_sessions WHERE user_id=%s AND session_id=%s', (user_id, session_id))
            s = cur.fetchone()
            if not s:
                raise RuleError('找不到本人 Session')
            return _result(cur, s)


def get_open_session(user_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT * FROM exercise_sessions WHERE user_id=%s
                AND status IN ('created','active','paused')
                ORDER BY session_id DESC LIMIT 1""", (user_id,))
            s = cur.fetchone()
            if not s:
                return {'success': True, 'has_open_session': False, 'session': None}
            return dict(_result(cur, s), has_open_session=True)


def _result(cur, s):
    out = {'success': True, 'session': dict(s), 'task': None, 'reward': None}
    if s['task_progress_id'] is not None:
        cur.execute("""SELECT progress_id,status,progress_count,progress_seconds,target_count,target_seconds,
            completed_at,rewarded_at FROM user_task_progress WHERE progress_id=%s AND user_id=%s""",
                    (s['task_progress_id'], s['user_id']))
        out['task'] = dict(cur.fetchone())
        cur.execute(
            'SELECT * FROM reward_transactions WHERE task_progress_id=%s', (s['task_progress_id'],))
        r = cur.fetchone()
        out['reward'] = dict(r) if r else None
    cur.execute(
        'SELECT player_level,player_exp,money FROM user_stats WHERE user_id=%s', (s['user_id'],))
    out['player'] = dict(cur.fetchone())
    out['reward_pending'] = bool(
        out['task'] and out['task']['status'] in ('completed', 'claimable'))
    return out


def start_session(user_id, client_session_id, task_progress_id=None, exercise_id=None, goal_type=None, target_count=None, target_seconds=None):
    client = str(UUID(str(client_session_id)))
    with db_transaction() as conn:
        with conn.cursor() as cur:
            lock_user(cur, user_id)
            cur.execute(
                'SELECT * FROM exercise_sessions WHERE user_id=%s AND client_session_id=%s', (user_id, client))
            old = cur.fetchone()
            if old:
                if old['task_progress_id'] != task_progress_id:
                    raise RuleError('client_session_id 已用於其他運動')
                if task_progress_id is None and (old['exercise_id'], old['goal_type'], old['target_count'], old['target_seconds']) != (exercise_id, goal_type, target_count, target_seconds):
                    raise RuleError('同一 Session 請求不能變更目標')
                return dict(_result(cur, old), idempotent_replay=True)
            cur.execute(
                "SELECT session_id,task_progress_id FROM exercise_sessions WHERE user_id=%s AND status IN ('created','active','paused')", (user_id,))
            opened = cur.fetchone()
            if opened:
                raise OpenSessionExists(
                    opened['session_id'], opened['task_progress_id'])
            if task_progress_id is not None:
                if any(x is not None for x in (exercise_id, goal_type, target_count, target_seconds)):
                    raise RuleError('任務運動設定由快照決定，不另傳自訂目標')
                p = _progress(cur, user_id, task_progress_id)
                if p['status'] not in ('accepted', 'in_progress', 'interrupted') or p['snapshot_exercise_id'] is None:
                    raise RuleError('任務不可開始或缺少快照')
                exercise_id = p['snapshot_exercise_id']
                goal_type = p['snapshot_goal_type']
                target_count = p['target_count']
                target_seconds = p['target_seconds']
                if goal_met(goal_type, p['progress_count'], p['progress_seconds'], target_count, target_seconds):
                    raise RuleError('任務已達標，請查詢完成結果')
                cur.execute("UPDATE user_task_progress SET status='in_progress',started_at=COALESCE(started_at,CURRENT_TIMESTAMP),updated_at=CURRENT_TIMESTAMP WHERE progress_id=%s", (task_progress_id,))
            else:
                validate_goal(goal_type, target_count, target_seconds)
                cur.execute(
                    'SELECT 1 FROM exercise_goal_options WHERE exercise_id=%s', (exercise_id,))
                if not cur.fetchone():
                    raise RuleError('此運動尚未開放自主目標')
            cur.execute(
                'SELECT 1 FROM exercise_definitions WHERE exercise_id=%s AND is_active', (exercise_id,))
            if not cur.fetchone():
                raise RuleError('運動尚未啟用')
            cur.execute("""INSERT INTO exercise_sessions(client_session_id,user_id,task_progress_id,exercise_id,
                source_mode,goal_type,target_count,target_seconds,status,started_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'active',CURRENT_TIMESTAMP) RETURNING *""",
                        (client, user_id, task_progress_id, exercise_id, 'task' if task_progress_id is not None else 'free_training',
                         goal_type, target_count, target_seconds))
            return dict(_result(cur, cur.fetchone()), idempotent_replay=False)


def _write_log(cur, s):
    cur.execute(
        'SELECT exercise_key,exercise_category FROM exercise_definitions WHERE exercise_id=%s', (s['exercise_id'],))
    e = cur.fetchone()
    cur.execute("""INSERT INTO exercise_logs(user_id,exercise_type,exercise_body_part,task_mode,goal_type,
        target_count,target_seconds,actual_count,duration_seconds,result,started_at,ended_at,
        task_progress_id,source_mode,exercise_id,session_id)
        VALUES(%s,%s,%s,'basic',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT(session_id) WHERE session_id IS NOT NULL DO NOTHING RETURNING exercise_log_id""",
                (s['user_id'], e['exercise_key'], e['exercise_category'], s['goal_type'], s['target_count'], s['target_seconds'],
                 s['accepted_count'], s['accepted_seconds'], s['status'], s['started_at'], s['ended_at'],
                    s['task_progress_id'], s['source_mode'], s['exercise_id'], s['session_id']))
    if cur.fetchone():
        cur.execute("""UPDATE user_stats SET total_exercise_count=total_exercise_count+%s,
            total_exercise_seconds=total_exercise_seconds+%s,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s""",
                    (s['accepted_count'], s['accepted_seconds'], s['user_id']))


def sync_session(user_id, session_id, sync_sequence, cumulative_count, cumulative_seconds, state):
    pid = None
    with db_transaction() as conn:
        with conn.cursor() as cur:
            lock_user(cur, user_id)
            cur.execute(
                'SELECT task_progress_id FROM exercise_sessions WHERE session_id=%s AND user_id=%s', (session_id, user_id))
            row = cur.fetchone()
            if not row:
                raise RuleError('找不到本人 Session')
            pid = row['task_progress_id']
            p = _progress(cur, user_id, pid) if pid is not None else None
            cur.execute(
                'SELECT * FROM exercise_sessions WHERE session_id=%s AND user_id=%s FOR UPDATE', (session_id, user_id))
            s = cur.fetchone()
            kind, dc, ds = evaluate_sync(
                s, sync_sequence, cumulative_count, cumulative_seconds, state)
            if kind == 'new':
                if p and p['status'] not in ('accepted', 'in_progress', 'interrupted'):
                    raise RuleError('任務已結束，不接受新增成果')
                if p:
                    pc = p['progress_count']+dc
                    ps = p['progress_seconds']+ds
                    met = goal_met(p['snapshot_goal_type'], pc,
                                   ps, p['target_count'], p['target_seconds'])
                    cur.execute("""UPDATE user_task_progress SET progress_count=%s,progress_seconds=%s,
                      status=%s,completed_at=CASE WHEN %s THEN COALESCE(completed_at,CURRENT_TIMESTAMP) ELSE completed_at END,
                      last_progress_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE progress_id=%s""",
                                (pc, ps, 'completed' if met else 'in_progress', met, pid))
                else:
                    met = goal_met(s['goal_type'], cumulative_count,
                                   cumulative_seconds, s['target_count'], s['target_seconds'])
                new_status = 'completed' if met else (
                    'partial' if state == 'ended' else state)
                ended = new_status in ('completed', 'partial', 'interrupted')
                cur.execute("""UPDATE exercise_sessions SET accepted_count=%s,accepted_seconds=%s,last_sync_sequence=%s,
                    last_sync_state=%s,status=%s,ended_at=CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END,
                    updated_at=CURRENT_TIMESTAMP WHERE session_id=%s RETURNING *""",
                            (cumulative_count, cumulative_seconds, sync_sequence, state, new_status, ended, session_id))
                s = cur.fetchone()
                if ended:
                    _write_log(cur, s)
            result = _result(cur, s)
            result['sync_result'] = kind
    # Progress and completed state are committed FIRST. Reward failures remain retryable.
    if pid is not None and result['task']['status'] in ('completed', 'claimable'):
        try_reward(user_id, pid)
        result = dict(get_session(user_id, session_id), sync_result=kind)
    return result
