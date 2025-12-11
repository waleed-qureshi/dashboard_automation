from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List
from sklearn.linear_model import LogisticRegression, LinearRegression
import math


def _fetchall_dict(db: Session, sql: str):
    res = db.execute(text(sql))
    cols = res.keys()
    return [dict(zip(cols, row)) for row in res.fetchall()]


def task_status_overview(db: Session) -> Dict[str, int]:
    rows = _fetchall_dict(db, 'select id, status, due_date, updated_at from tasks')
    now = datetime.utcnow()
    on_time = late = overdue = 0
    for r in rows:
        due = r.get('due_date')
        status = (r.get('status') or '').lower()
        if not due:
            on_time += 1
            continue
        due_dt = r['due_date']
        try:
            if isinstance(due_dt, str):
                due_dt = datetime.fromisoformat(due_dt)
        except Exception:
            due_dt = due_dt
        if status in ('done', 'closed'):
            updated = r.get('updated_at')
            if updated and ((isinstance(updated, str) and datetime.fromisoformat(updated) <= due_dt) or (not isinstance(updated, str) and updated <= due_dt)):
                on_time += 1
            else:
                late += 1
        else:
            if now > due_dt:
                overdue += 1
            else:
                late += 1
    return {"on_time": on_time, "late": late, "overdue": overdue}


def find_tasks_stuck_in_review(db: Session, days: int = 3) -> List[Dict[str, Any]]:
    rows = _fetchall_dict(db, "select id, review_started_at from tasks where review_started_at is not null")
    stuck = []
    now = datetime.utcnow()
    for r in rows:
        started = r.get('review_started_at')
        if not started:
            continue
        try:
            if isinstance(started, str):
                started_dt = datetime.fromisoformat(started)
            else:
                started_dt = started
        except Exception:
            continue
        if (now - started_dt).days > days:
            stuck.append({"task_id": int(r['id']), "days_in_review": (now - started_dt).days})
    return stuck


def detect_no_work_until_last_day(db: Session) -> List[int]:
    tasks = _fetchall_dict(db, 'select id,due_date from tasks where due_date is not null')
    logs = _fetchall_dict(db, 'select task_id, created_at from timelogs')
    logs_by_task = {}
    for l in logs:
        logs_by_task.setdefault(l['task_id'], []).append(l['created_at'])
    flagged = []
    for t in tasks:
        t_id = t['id']
        due = t['due_date']
        if not due:
            flagged.append(int(t_id))
            continue
        try:
            due_dt = datetime.fromisoformat(due) if isinstance(due, str) else due
        except Exception:
            due_dt = due
        task_logs = logs_by_task.get(t_id, [])
        if not task_logs:
            flagged.append(int(t_id))
            continue
        earliest = min([datetime.fromisoformat(x) if isinstance(x, str) else x for x in task_logs])
        if (due_dt - earliest).days <= 1:
            flagged.append(int(t_id))
    return flagged


def unusual_behaviors(db: Session) -> Dict[str, List[Any]]:
    tasks = _fetchall_dict(db, 'select id,status_change_count,due_date,blocked from tasks')
    timelogs = _fetchall_dict(db, 'select task_id,comment,files_attached,created_at from timelogs')
    high_status_changes = [int(t['id']) for t in tasks if (t.get('status_change_count') or 0) >= 5]
    odd_logs_task_ids = set()
    for l in timelogs:
        if (not l.get('comment')) and (not l.get('files_attached')):
            odd_logs_task_ids.add(int(l['task_id']))
    blocked_last = []
    now = datetime.utcnow()
    for t in tasks:
        if not t.get('blocked'):
            continue
        due = t.get('due_date')
        if not due:
            blocked_last.append(int(t['id']))
            continue
        try:
            due_dt = datetime.fromisoformat(due) if isinstance(due, str) else due
        except Exception:
            due_dt = due
        # if blocked and within 1 day of due
        # approximate using now - if due in next 1 day or past 1 day, consider last moment
        if abs((due_dt - now).days) <= 1:
            blocked_last.append(int(t['id']))
    return {"high_status_changes": high_status_changes, "logs_no_comment_no_files": list(odd_logs_task_ids), "blocked_last_moment": blocked_last}


# ----- Leads analytics
def rank_lead_sources(db: Session) -> List[Dict[str, Any]]:
    leads = _fetchall_dict(db, 'select source,converted,estimated_value from leads')
    if not leads:
        return []
    stats = {}
    for l in leads:
        s = l.get('source') or 'unknown'
        st = stats.setdefault(s, {'conversions': 0, 'count': 0, 'total_value': 0.0})
        st['count'] += 1
        if l.get('converted'):
            st['conversions'] += 1
        st['total_value'] += float(l.get('estimated_value') or 0.0)
    out = []
    for source, v in sorted(stats.items(), key=lambda x: x[1]['conversions'], reverse=True):
        out.append({'source': source, **v})
    return out


def lead_close_predictor(db: Session, model=None) -> List[Dict[str, Any]]:
    leads = _fetchall_dict(db, 'select id,priority,estimated_value,converted from leads')
    if len(leads) < 5:
        # return simple heuristic score
        return [{"lead_id": int(l['id']), "prob_close": min(0.9, 0.1 * (l.get('priority') or 1) + 0.0001 * (l.get('estimated_value') or 0))} for l in leads]
    X = []
    y = []
    for l in leads:
        X.append([l.get('priority') or 0, float(l.get('estimated_value') or 0.0)])
        y.append(1 if l.get('converted') else 0)
    clf = LogisticRegression(max_iter=200)
    clf.fit(X, y)
    probs = clf.predict_proba(X)[:, 1]
    return [{"lead_id": int(l['id']), "prob_close": float(p)} for l, p in zip(leads, probs.tolist())]


def forecast_pipeline(db: Session, months_ahead: int = 3) -> Dict[str, float]:
    leads = _fetchall_dict(db, 'select created_at,estimated_value from leads where converted=1')
    if not leads:
        return {f'month_{i+1}': 0.0 for i in range(months_ahead)}
    # group by month string
    months = {}
    for l in leads:
        dt = l.get('created_at')
        try:
            d = datetime.fromisoformat(dt) if isinstance(dt, str) else dt
        except Exception:
            continue
        key = d.strftime('%Y-%m')
        months[key] = months.get(key, 0.0) + float(l.get('estimated_value') or 0.0)
    sorted_months = sorted(months.items())
    if len(sorted_months) < 2:
        base = sum([v for _, v in sorted_months])
        return {f'month_{i+1}': base for i in range(months_ahead)}
    # simple linear trend on indices
    X = [[i] for i in range(len(sorted_months))]
    y = [v for _, v in sorted_months]
    lr = LinearRegression()
    lr.fit(X, y)
    last = len(sorted_months) - 1
    preds = {}
    for i in range(1, months_ahead + 1):
        val = lr.predict([[last + i]])[0]
        preds[f'month_{i}'] = float(max(0.0, val))
    return preds


def detect_unprofitable_projects(db: Session) -> List[Dict[str, Any]]:
    projects = _fetchall_dict(db, 'select id,name,actual_revenue,cost from projects')
    out = []
    for r in projects:
        rev = float(r.get('actual_revenue') or 0.0)
        cost = float(r.get('cost') or 0.0)
        if rev - cost < 0:
            out.append({"project_id": int(r['id']), "name": r.get('name'), "profit": rev - cost})
    return out


def compute_member_loads(db: Session, window_days: int = 14) -> List[Dict[str, Any]]:
    """Compute estimated workload vs capacity per member.

    - Sums `estimated_hours` for tasks assigned to the user and due within next `window_days`.
    - Reads `capacity_hours_per_week` from users table.
    - Returns percent utilization and status: 'overloaded' (>100%), 'ok' (30-100%), 'underloaded' (<30%).
    """
    users = _fetchall_dict(db, 'select id,name,capacity_hours_per_week from users')
    tasks = _fetchall_dict(db, "select id,assignee_id,estimated_hours,due_date,status from tasks where assignee_id is not null")
    timelogs = _fetchall_dict(db, 'select user_id,hours,created_at from timelogs')
    now = datetime.utcnow()
    res = []
    # index logs by user for last 7 days
    logs_by_user = {}
    for l in timelogs:
        try:
            dt = datetime.fromisoformat(l['created_at']) if isinstance(l['created_at'], str) else l['created_at']
        except Exception:
            dt = now
        if (now - dt).days <= 7:
            logs_by_user.setdefault(l['user_id'], 0.0)
            logs_by_user[l['user_id']] += float(l.get('hours') or 0.0)

    for u in users:
        uid = u['id']
        capacity = float(u.get('capacity_hours_per_week') or 40.0)
        est_sum = 0.0
        for t in tasks:
            if t.get('assignee_id') != uid:
                continue
            due = t.get('due_date')
            if not due:
                # include tasks without due if status not done
                if (t.get('status') or '').lower() not in ('done','closed'):
                    est_sum += float(t.get('estimated_hours') or 0.0)
                continue
            try:
                due_dt = datetime.fromisoformat(due) if isinstance(due, str) else due
            except Exception:
                due_dt = due
            if due_dt is None:
                continue
            if 0 <= (due_dt - now).days <= window_days and (t.get('status') or '').lower() not in ('done','closed'):
                est_sum += float(t.get('estimated_hours') or 0.0)

        logged_recent = float(logs_by_user.get(uid, 0.0))
        # percent utilization vs weekly capacity (normalize est_sum to per-week by dividing window days/7)
        weeks_window = max(1.0, window_days / 7.0)
        weekly_est = est_sum / weeks_window
        util_pct = (weekly_est / capacity) * 100.0 if capacity > 0 else 0.0
        status = 'ok'
        if util_pct > 100.0:
            status = 'overloaded'
        elif util_pct < 30.0:
            status = 'underloaded'
        res.append({
            'user_id': int(uid),
            'name': u.get('name'),
            'capacity_hours_per_week': capacity,
            'estimated_work_hours_next_window': round(est_sum, 2),
            'weekly_estimated_hours': round(weekly_est, 2),
            'recent_logged_hours_7d': round(logged_recent, 2),
            'utilization_pct': round(util_pct, 1),
            'status': status,
        })
    # sort by utilization desc
    res.sort(key=lambda x: x['utilization_pct'], reverse=True)
    return res
