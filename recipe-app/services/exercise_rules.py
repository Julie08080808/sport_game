"""Pure rules shared by API and offline tests."""
class RuleError(ValueError):
    pass

OPEN = ('active','paused')
TERMINAL = ('completed','partial','interrupted','abandoned')


def validate_goal(goal_type,count,seconds):
    if goal_type == 'count':
        if count is None or not 1<=count<=100 or seconds is not None:
            raise RuleError('次數目標需為1～100，時間目標留空')
    elif goal_type == 'time':
        if seconds is None or not 30<=seconds<=600 or seconds%30 or count is not None:
            raise RuleError('時間需為30～600秒、30秒倍數，次數目標留空')
    else:
        raise RuleError('goal_type 必須為 count 或 time')


def goal_met(goal_type,count,seconds,target_count,target_seconds):
    target=target_count if goal_type=='count' else target_seconds
    if target is None or target<=0:
        raise RuleError('接取目標缺失')
    return (count if goal_type=='count' else seconds)>=target


def evaluate_sync(session,sequence,count,seconds,state):
    if sequence<=0 or count<0 or seconds<0 or state not in ('active','paused','ended','interrupted'):
        raise RuleError('同步序號、成果或狀態不合法')
    last=session['last_sync_sequence']
    if sequence<last:
        return 'stale',0,0
    if sequence==last:
        if (count,seconds,state)!=(session['accepted_count'],session['accepted_seconds'],session['last_sync_state']):
            raise RuleError('同一同步序號不能改變內容')
        return 'replay',0,0
    if session['status'] not in OPEN:
        raise RuleError('本次運動已結束；新運動需要新的 Session')
    dc=count-session['accepted_count'];ds=seconds-session['accepted_seconds']
    if dc<0 or ds<0:
        raise RuleError('累積成果不能倒退')
    if session['status']=='paused' and (dc or ds):
        raise RuleError('暫停時不能增加成果，先送繼續再運動')
    return 'new',dc,ds
