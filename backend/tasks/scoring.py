# backend/tasks/scoring.py
import datetime
from collections import defaultdict, deque
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FEEDBACK_STORE = BASE_DIR / "feedback_store.json"

DEFAULT_WEIGHTS = {
    "urgency": 0.35,
    "importance": 0.35,
    "effort": 0.15,
    "dependency": 0.15,
}

STRATEGY_PRESETS = {
    "smart_balance": DEFAULT_WEIGHTS,
    "fastest_wins": {"urgency": 0.20, "importance": 0.20, "effort": 0.50, "dependency": 0.10},
    "high_impact": {"urgency": 0.20, "importance": 0.60, "effort": 0.10, "dependency": 0.10},
    "deadline_driven": {"urgency": 0.70, "importance": 0.15, "effort": 0.05, "dependency": 0.10},
}

# --- Helpers: cycles detection (returns list of cycles as lists) ---
def detect_circular_dependencies(tasks):
    """
    tasks: list of task dicts (each has 'id' and 'dependencies' list)
    returns: (has_cycle: bool, cycles: list_of_lists)
    """
    graph = {t['id']: [d for d in (t.get('dependencies') or [])] for t in tasks}
    visited = set()
    stack = []
    cycles = []
    onstack = set()

    def dfs(node):
        if node in onstack:
            # build cycle
            idx = stack.index(node)
            cycles.append(stack[idx:] + [node])
            return
        if node in visited:
            return
        visited.add(node)
        stack.append(node)
        onstack.add(node)
        for neigh in graph.get(node, []):
            if neigh in graph:  # only if neighbor is a known task id
                dfs(neigh)
        stack.pop()
        onstack.remove(node)

    for n in graph:
        if n not in visited:
            dfs(n)
    return (len(cycles) > 0), cycles

# --- Helpers: business days between two dates (excludes weekends & holidays) ---
def business_days_between(start_date, end_date, holidays=None):
    if holidays is None:
        holidays = set()
    if isinstance(holidays, list):
        holidays = set([datetime.date.fromisoformat(h) for h in holidays])
    days = 0
    cur = start_date
    step = 1 if end_date >= start_date else -1
    while cur != end_date:
        if cur.weekday() < 5 and cur not in holidays:
            days += 1 if step == 1 else -1
        cur += datetime.timedelta(days=step)
    # include end_date day if it's business day
    if end_date.weekday() < 5 and end_date not in holidays:
        days += 1 if step == 1 else -1
    return max(0, days) if step == 1 else min(0, days)

# --- Load feedback store (simple JSON file) ---
def load_feedback_store():
    if not FEEDBACK_STORE.exists():
        return {}
    try:
        with FEEDBACK_STORE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# --- normalize utility ---
def normalize(value, min_v, max_v):
    if max_v == min_v:
        return 0.0
    return (value - min_v) / (max_v - min_v)

# --- Main scoring function ---
def compute_scores(task_list, strategy="smart_balance", custom_weights=None, today=None, holidays=None):
    """
    task_list: list of task dicts
    holidays: list of 'YYYY-MM-DD' strings (optional)
    """
    if today is None:
        today = datetime.date.today()
    if isinstance(today, str):
        today = datetime.date.fromisoformat(today)

    weights = custom_weights if custom_weights else STRATEGY_PRESETS.get(strategy, DEFAULT_WEIGHTS)
    # prepare mapping, ensure id present
    tasks = {}
    for idx, t in enumerate(task_list):
        tid = str(t.get("id") or t.get("external_id") or t.get("title") + f"_{idx}")
        dd = t.get("due_date")
        if isinstance(dd, str):
            try:
                dd_parsed = datetime.date.fromisoformat(dd)
            except Exception:
                dd_parsed = None
        else:
            dd_parsed = dd
        tasks[tid] = {
            "id": tid,
            "title": t.get("title", ""),
            "due_date": dd_parsed,
            "estimated_hours": float(t.get("estimated_hours") or 1.0),
            "importance": int(t.get("importance") or 5),
            "dependencies": [str(d) for d in (t.get("dependencies") or [])],
            "_orig": t,
        }

    # detect cycles
    has_cycle, cycles = detect_circular_dependencies(list(tasks.values()))
    for t in tasks.values():
        t["cycle"] = any(t["id"] in c for c in cycles)

    # business-days urgency calculation
    raw_urgencies = {}
    for tid, t in tasks.items():
        dd = t["due_date"]
        if dd is None:
            raw_urgencies[tid] = 0.0
            continue
        try:
            days_left = business_days_between(today, dd, holidays=holidays or [])
        except Exception:
            # fallback to naive calendar days
            days_left = (dd - today).days
        # transform days_left into urgency: smaller business days -> larger urgency
        if days_left <= 0:
            raw_urgencies[tid] = 1.5 + (abs(days_left) / 365)
        else:
            raw_urgencies[tid] = 1.0 / (1 + days_left)

    efforts = {tid: t["estimated_hours"] for tid, t in tasks.items()}
    importance = {tid: t["importance"] for tid, t in tasks.items()}

    # dependency: how many tasks depend on this task
    blocked_count = {tid: 0 for tid in tasks}
    for tid, t in tasks.items():
        for dep in t["dependencies"]:
            if dep in blocked_count:
                blocked_count[dep] += 1

    # normalization min/max
    urg_vals = list(raw_urgencies.values()) or [0.0]
    min_urg, max_urg = min(urg_vals), max(urg_vals)
    min_eff, max_eff = min(efforts.values()), max(efforts.values())
    min_imp, max_imp = min(importance.values()), max(importance.values())
    min_block, max_block = min(blocked_count.values()), max(blocked_count.values())

    # learning feedback adjustments (per-task helpfulness ratio)
    feedback = load_feedback_store()
    helpful_ratio = {}
    for tid in tasks:
        rec = feedback.get(tid, {})
        helpful = rec.get("helpful", 0)
        total = rec.get("total", 0)
        ratio = (helpful / total) if total > 0 else 0.0
        helpful_ratio[tid] = ratio  # 0..1

    results = []
    for tid, t in tasks.items():
        n_urg = normalize(raw_urgencies[tid], min_urg, max_urg)
        n_imp = normalize(t["importance"], min_imp, max_imp)
        inv_effort = max_eff - t["estimated_hours"]
        n_eff = normalize(inv_effort, (max_eff - max_eff), (max_eff - min_eff)) if max_eff != min_eff else 0.0
        n_dep = normalize(blocked_count.get(tid, 0), min_block, max_block)

        score = (
            weights.get("urgency", 0) * n_urg
            + weights.get("importance", 0) * n_imp
            + weights.get("effort", 0) * n_eff
            + weights.get("dependency", 0) * n_dep
        )

        # feedback boost: if community found this task helpful earlier, small boost
        fb = helpful_ratio.get(tid, 0.0)
        if fb > 0:
            score = score + 0.08 * fb  # small boost (max +0.08)

        reasons = []
        if t["cycle"]:
            score *= 0.75
            reasons.append("circular dependency detected (penalized)")
        dd_map = t["due_date"]
        if dd_map is not None:
            try:
                dl = business_days_between(today, dd_map, holidays=holidays or [])
            except Exception:
                dl = (dd_map - today).days
            if dl <= 0:
                reasons.append("overdue or due today")
            elif dl <= 2:
                reasons.append(f"due in {dl} business day(s)")
        if blocked_count.get(tid, 0) > 0:
            reasons.append(f"blocks {blocked_count[tid]} other task(s)")
        if t["estimated_hours"] <= 2:
            reasons.append("quick win (low effort)")
        if fb > 0:
            reasons.append(f"user feedback helpfulness {round(fb,2)}")

        score = max(0.0, min(score, 1.0))
        results.append({
            "id": tid,
            "title": t["title"],
            "due_date": t["due_date"].isoformat() if t["due_date"] else None,
            "estimated_hours": t["estimated_hours"],
            "importance": t["importance"],
            "dependencies": t["dependencies"],
            "score": round(score, 4),
            "reason": "; ".join(reasons) if reasons else "balanced priority"
        })

    # sort: score desc, then earlier due date, higher importance, lower hours
    def sort_key(item):
        dd = item["due_date"]
        if dd is None:
            dd_val = datetime.date.max
        else:
            dd_val = datetime.date.fromisoformat(dd)
        return (-item["score"], dd_val, -item["importance"], item["estimated_hours"])

    results.sort(key=sort_key)
    return results
