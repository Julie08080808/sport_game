from config.database import db_transaction
from services.exercise_rules import RuleError


def level_view(stats, levels):
    eligible=[r for r in levels if r['required_total_exp'] <= stats['player_exp']]
    if not eligible:
        raise RuleError('等級表缺少初始等級')
    current=max(eligible,key=lambda r:r['required_total_exp'])
    later=[r for r in levels if r['required_total_exp'] > stats['player_exp']]
    nxt=min(later,key=lambda r:r['required_total_exp']) if later else None
    return dict(stats,player_level=current['player_level'],
        expToNextLevel=nxt['required_total_exp']-stats['player_exp'] if nxt else 0,
        current_level_exp=stats['player_exp']-current['required_total_exp'],
        level_exp_required=nxt['required_total_exp']-current['required_total_exp'] if nxt else 0,
        next_level_total_exp=nxt['required_total_exp'] if nxt else None,
        is_max_level=nxt is None)


def get_player(user_id):
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT player_level,player_exp,money FROM user_stats WHERE user_id=%s',(user_id,))
            stats=cur.fetchone()
            if not stats:raise RuleError('找不到玩家資料')
            cur.execute('SELECT player_level,required_total_exp FROM player_level_definitions ORDER BY required_total_exp')
            return level_view(dict(stats),cur.fetchall())
