"""
運動分析（App 個人檔案 → 數據分析 → 打開運動分析 的網頁 /analytics 用）。

資料來源：exercise_logs（每次運動結束寫一筆：運動種類、手部／腳部、做了幾下、幾秒、完成或放棄）。
一次算好：累計（從第一次運動到現在）、今天、本週（週一～週日）、本月（每週一根、跟上個月比）、
連續運動天數、最近 7 天要加強的地方。

時間：exercise_logs.started_at 是不含時區的時間，照資料庫的時區存；這裡一律換成台灣時間再分日。
建議文字只用來鼓勵，不是醫療判斷；門檻集中在下面的常數，要調直接改這裡。
"""

from datetime import date, timedelta

from config.database import db_transaction

DAILY_GOAL_MINUTES = 5        # 每天目標分鐘數（任務一次大約 1 分鐘）
WEEK_ACTIVE_DAYS_GOAL = 3     # 最近 7 天至少要有幾天運動
BALANCE_MIN_SHARE = 0.30      # 手部或腳部至少要佔總分鐘的比例
DROP_WARN_RATIO = 0.30        # 比前 7 天少超過這個比例就提醒
COMPLETION_WARN = 0.50        # 完成率低於這個就建議選簡單一點的任務
MIN_ATTEMPTS_FOR_RATE = 3     # 少於這麼多次就不判斷完成率

WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]

# 資料庫的名稱有些跟現在 App 上的說法不同，這裡換成長輩看得懂的
NAME_OVERRIDES = {
    "LEG_KICK": "扶牆側抬腳",
    "HAND_BICEP_CURL": "二頭彎舉（搬地瓜）",
    "HAND_GRIP": "握球",
    "HAND_DUAL_PRESS": "雙手按球",
}
PART_LABELS = {"hand": "手部", "leg": "腳部"}


def _part(body_part):
    return body_part if body_part in ("hand", "leg") else "other"


def _minutes(seconds):
    return round((seconds or 0) / 60.0, 1)


def _empty():
    return {"count": 0, "seconds": 0}


def _add(bucket, row):
    bucket["count"] += row["actual_count"] or 0
    bucket["seconds"] += row["duration_seconds"] or 0


def _finish(bucket):
    return {"count": bucket["count"], "minutes": _minutes(bucket["seconds"])}


def get_exercise_summary(user_id: int) -> dict:
    with db_transaction() as conn:
        with conn.cursor() as cur:
            # 台灣時間的今天，以及每筆紀錄換成台灣時間後的日期
            cur.execute("SELECT (now() AT TIME ZONE 'Asia/Taipei')::date AS today")
            today = cur.fetchone()["today"]
            # 從上個月 1 號開始拿（本月＋跟上個月比；也涵蓋最近 14 天的建議）
            first_this = today.replace(day=1)
            since = min((first_this - timedelta(days=1)).replace(day=1), today - timedelta(days=13))
            cur.execute("""
                SELECT (l.started_at AT TIME ZONE current_setting('TimeZone') AT TIME ZONE 'Asia/Taipei')::date AS day,
                       l.exercise_body_part, l.exercise_type,
                       COALESCE(d.exercise_name, l.exercise_type) AS exercise_name,
                       COALESCE(l.actual_count, 0) AS actual_count,
                       COALESCE(l.duration_seconds, 0) AS duration_seconds,
                       l.result
                FROM exercise_logs l
                LEFT JOIN exercise_definitions d ON d.exercise_id = l.exercise_id
                WHERE l.user_id = %s
                  AND (l.started_at AT TIME ZONE current_setting('TimeZone') AT TIME ZONE 'Asia/Taipei')::date >= %s
            """, (user_id, since))
            rows = cur.fetchall()
            cur.execute("""
                SELECT DISTINCT (started_at AT TIME ZONE current_setting('TimeZone') AT TIME ZONE 'Asia/Taipei')::date AS day
                FROM exercise_logs WHERE user_id = %s
                ORDER BY day DESC LIMIT 400
            """, (user_id,))
            active_days_desc = [r["day"] for r in cur.fetchall()]

            # 累計：全部的紀錄（不限最近幾天），照手部／腳部分開加總
            cur.execute("""
                SELECT exercise_body_part,
                       count(*) AS sessions,
                       count(*) FILTER (WHERE result = 'completed') AS completed,
                       COALESCE(sum(actual_count), 0) AS reps,
                       COALESCE(sum(duration_seconds), 0) AS seconds,
                       min((started_at AT TIME ZONE current_setting('TimeZone') AT TIME ZONE 'Asia/Taipei')::date) AS first_day
                FROM exercise_logs WHERE user_id = %s
                GROUP BY exercise_body_part
            """, (user_id,))
            totals = cur.fetchall()

    result = _build(today, rows, active_days_desc)
    result["total"] = _total(totals, active_days_desc)
    return result


def _total(groups: list, active_days_desc: list) -> dict:
    """累計運動：做了幾次（每做一個任務或自主運動算一次）、完成幾次、手部／腳部各幾下幾分鐘、運動過幾天。"""
    parts = {"hand": {"count": 0, "seconds": 0}, "leg": {"count": 0, "seconds": 0}}
    sessions = completed = 0
    first = None
    for g in groups:
        sessions += g["sessions"]
        completed += g["completed"]
        if g["first_day"] is not None and (first is None or g["first_day"] < first):
            first = g["first_day"]
        p = _part(g["exercise_body_part"])
        if p in parts:
            parts[p]["count"] += int(g["reps"])
            parts[p]["seconds"] += int(g["seconds"])
    return {
        "sessions": sessions,
        "completed": completed,
        "active_days": len(active_days_desc),
        "since": first.isoformat() if first else None,
        "hand": _finish(parts["hand"]),
        "leg": _finish(parts["leg"]),
        "minutes": _minutes(parts["hand"]["seconds"] + parts["leg"]["seconds"]),
    }


def _build(today: date, rows: list, active_days_desc: list) -> dict:
    # ── 今天 ──
    today_parts = {"hand": _empty(), "leg": _empty()}
    today_sessions = today_completed = 0
    for r in rows:
        if r["day"] != today:
            continue
        today_sessions += 1
        if r["result"] == "completed":
            today_completed += 1
        p = _part(r["exercise_body_part"])
        if p in today_parts:
            _add(today_parts[p], r)
    today_seconds = sum(b["seconds"] for b in today_parts.values())

    # ── 本週（週一開始）每天 ──
    monday = today - timedelta(days=today.weekday())
    week_days = []
    week_parts = {"hand": _empty(), "leg": _empty()}
    for i in range(7):
        d = monday + timedelta(days=i)
        parts = {"hand": _empty(), "leg": _empty()}
        for r in rows:
            if r["day"] == d and _part(r["exercise_body_part"]) in parts:
                _add(parts[_part(r["exercise_body_part"])], r)
                _add(week_parts[_part(r["exercise_body_part"])], r)
        week_days.append({
            "date": d.isoformat(), "label": WEEKDAY_LABELS[i], "future": d > today, "is_today": d == today,
            "hand": _finish(parts["hand"]), "leg": _finish(parts["leg"]),
        })

    # ── 本月：固定分 4 段（1–7、8–14、15–21、22–月底），每段一根，長輩比較好懂 ──
    first = today.replace(day=1)
    next_first = (first + timedelta(days=32)).replace(day=1)
    month_weeks = []
    month_parts = {"hand": _empty(), "leg": _empty()}
    for n, (lo, hi) in enumerate([(1, 8), (8, 15), (15, 22), (22, None)], start=1):
        start = first.replace(day=lo)
        end = first.replace(day=hi) if hi else next_first
        parts = {"hand": _empty(), "leg": _empty()}
        for r in rows:
            if start <= r["day"] < end and _part(r["exercise_body_part"]) in parts:
                _add(parts[_part(r["exercise_body_part"])], r)
                _add(month_parts[_part(r["exercise_body_part"])], r)
        last = end - timedelta(days=1)
        month_weeks.append({
            "label": f"第{n}週",
            "range": f"{start.month}/{start.day}–{last.month}/{last.day}",
            "future": start > today, "is_current": start <= today < end,
            "hand": _finish(parts["hand"]), "leg": _finish(parts["leg"]),
        })

    prev_first = (first - timedelta(days=1)).replace(day=1)
    prev_parts = {"hand": _empty(), "leg": _empty()}
    for r in rows:
        if prev_first <= r["day"] < first and _part(r["exercise_body_part"]) in prev_parts:
            _add(prev_parts[_part(r["exercise_body_part"])], r)
    month_active_days = len({r["day"] for r in rows if first <= r["day"] <= today})

    # ── 本週做最多的運動 ──
    top = {}
    for r in rows:
        if monday <= r["day"] <= today:
            key = r["exercise_type"]
            t = top.setdefault(key, {
                "name": NAME_OVERRIDES.get(key, r["exercise_name"]),
                "part": PART_LABELS.get(_part(r["exercise_body_part"]), "其他"),
                "count": 0, "seconds": 0, "times": 0})
            t["count"] += r["actual_count"] or 0
            t["seconds"] += r["duration_seconds"] or 0
            t["times"] += 1
    top_list = sorted(top.values(), key=lambda t: (-t["times"], -t["seconds"]))[:5]
    for t in top_list:
        t["minutes"] = _minutes(t.pop("seconds"))

    return {
        "today": {
            "date": today.isoformat(),
            "minutes": _minutes(today_seconds),
            "goal_minutes": DAILY_GOAL_MINUTES,
            "sessions": today_sessions,
            "completed": today_completed,
            "hand": _finish(today_parts["hand"]),
            "leg": _finish(today_parts["leg"]),
        },
        "streak_days": _streak(today, active_days_desc),
        "week": {
            "start": monday.isoformat(),
            "days": week_days,
            "hand": _finish(week_parts["hand"]),
            "leg": _finish(week_parts["leg"]),
            "active_days": sum(1 for d in week_days if d["hand"]["minutes"] + d["leg"]["minutes"] > 0
                               or d["hand"]["count"] + d["leg"]["count"] > 0),
        },
        "month": {
            "label": f"{today.month} 月",
            "weeks": month_weeks,
            "hand": _finish(month_parts["hand"]),
            "leg": _finish(month_parts["leg"]),
            "active_days": month_active_days,
            "last_month": {"label": f"{prev_first.month} 月",
                           "hand": _finish(prev_parts["hand"]), "leg": _finish(prev_parts["leg"])},
        },
        "top_exercises": top_list,
        "advice": _advice(today, rows),
    }


def _streak(today: date, active_days_desc: list) -> int:
    """連續運動天數：今天還沒動的話，從昨天往回算（今天還有機會，不要一早就歸零）。"""
    days = set(active_days_desc)
    d = today if today in days else today - timedelta(days=1)
    n = 0
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


def _advice(today: date, rows: list) -> dict:
    """最近 7 天（含今天）的一則建議：一次只講最需要的一件事。"""
    recent = [r for r in rows if today - timedelta(days=6) <= r["day"] <= today]
    previous = [r for r in rows if today - timedelta(days=13) <= r["day"] <= today - timedelta(days=7)]

    def seconds(rs, part=None):
        return sum(r["duration_seconds"] or 0 for r in rs if part is None or _part(r["exercise_body_part"]) == part)

    total = seconds(recent)
    active_days = len({r["day"] for r in recent})
    attempts = len(recent)
    completed = sum(1 for r in recent if r["result"] == "completed")

    if attempts == 0:
        return {"level": "start", "title": "一起動起來",
                "text": "最近 7 天還沒有運動紀錄，去找 NPC 接一個任務，一起動一動吧！"}
    if active_days < WEEK_ACTIVE_DAYS_GOAL:
        more = WEEK_ACTIVE_DAYS_GOAL - active_days
        return {"level": "tip", "title": "可以多動幾天",
                "text": f"最近 7 天運動了 {active_days} 天，再多 {more} 天就達標，身體會更有力氣。"}
    if total >= 120:
        hand, leg = seconds(recent, "hand"), seconds(recent, "leg")
        if leg < total * BALANCE_MIN_SHARE:
            return {"level": "tip", "title": "腳部可以加強",
                    "text": f"腳部運動只佔 {round(leg * 100 / total)}%，找山林猴做踏步，腳會更有力、走路更穩。"}
        if hand < total * BALANCE_MIN_SHARE:
            return {"level": "tip", "title": "手部可以加強",
                    "text": f"手部運動只佔 {round(hand * 100 / total)}%，找咪兔搬地瓜，手臂會更有力。"}
    prev_total = seconds(previous)
    if prev_total > 0 and total < prev_total * (1 - DROP_WARN_RATIO):
        return {"level": "tip", "title": "比上週少動了一些",
                "text": f"最近 7 天運動 {_minutes(total)} 分鐘，比前 7 天少，一起加油，慢慢來就好。"}
    if attempts >= MIN_ATTEMPTS_FOR_RATE and completed < attempts * COMPLETION_WARN:
        return {"level": "tip", "title": "先從簡單的開始",
                "text": "有一半以上的運動沒有做完，可以先選次數少一點的任務，做完會更有成就感。"}
    return {"level": "good", "title": "表現很棒",
            "text": f"最近 7 天運動了 {active_days} 天，手腳都有動到，繼續保持！"}
