import datetime
from collections import defaultdict, deque

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

def detect_circular_dependencies(tasks):
    # tasks: dict id -> task dict (with dependencies list of ids)
    graph = defaultdict(list)
    for tid, t in tasks.items():
        for dep in t.get("dependencies", []):
            graph[dep].append(tid)  # edge dep -> tid (dep blocks tid)
    # detect cycle in graph nodes present in tasks
    visited = {}
    cycle_nodes = []

    def dfs(node, stack):
        if node not in tasks:
            return False
        if visited.get(node) == 1:
            # currently in recursion stack -> cycle
            cycle_nodes.extend(stack[stack.index(node):])
            return True
        if visited.get(node) == 2:
            return False
        visited[node] = 1
        for neigh in tasks[node].get("dependencies", []):
            if dfs(neigh, stack + [neigh]):
                return True
        visited[node] = 2
        return False

    for n in tasks:
        if visited.get(n) is None:
            if dfs(n, [n]):
                return True, list(set(cycle_nodes))
    return False, []

def normalize(value, min_v, max_v):
    if max_v == min_v:
        return 0.0
    return (value - min_v) / (max_v - min_v)

def compute_scores(task_list, strategy="smart_balance", custom_weights=None, today=None):
    """
    task_list: list of dicts. Each dict must have keys: id (optional), title, due_date (date or None), estimated_hours, importance (1-10), dependencies (list)
    returns: list of tasks augmented with score and reason
    """
    if today is None:
        today = datetime.date.today()

    weights = custom_weights if custom_weights else STRATEGY_PRESETS.get(strategy, DEFAULT_WEIGHTS)

    # Prepare id mapping — ensure each task has an 'id'
    tasks = {}
    for idx, t in enumerate(task_list):
        tid = str(t.get("id") or t.get("external_id") or t.get("title") + f"_{idx}")
        tasks[tid] = {
            "id": tid,
            "title": t.get("title", "<untitled>"),
            "due_date": t.get("due_date"),
            "estimated_hours": float(t.get("estimated_hours") or 1.0),
            "importance": int(t.get("importance") or 5),
            "dependencies": [str(d) for d in (t.get("dependencies") or [])],
            "_orig": t,
        }

    # Detect circular dependencies
    has_cycle, cycle_nodes = detect_circular_dependencies(tasks)
    if has_cycle:
        # Mark tasks in cycle with a penalty and include reason
        for tid in cycle_nodes:
            if tid in tasks:
                tasks[tid]["cycle"] = True
    else:
        for t in tasks.values():
            t["cycle"] = False

    # Compute urgency score: smaller days_left -> higher urgency
    days_left_map = {}
    for tid, t in tasks.items():
        dd = t["due_date"]
        if dd is None:
            days_left_map[tid] = None
            continue
        if isinstance(dd, str):
            dd = datetime.date.fromisoformat(dd)
        days_left = (dd - today).days
        days_left_map[tid] = days_left

    # For normalization we need min/max across tasks for days_left and effort and importance
    # Convert days_left to urgency raw value: negative (past-due) -> high urgency
    # We map days_left to raw_urgency where smaller days_left => larger raw_urgency
    raw_urgencies = {}
    for tid, days_left in days_left_map.items():
        if days_left is None:
            raw_urgencies[tid] = 0.0  # no due date => neutral urgency
        else:
            # transform so that:
            # past due (days_left < 0) get highest urgency
            # due today (0) -> high urgency
            # further out -> lower urgency
            if days_left < 0:
                raw_urgencies[tid] = 1.5 + (abs(days_left) / 365)  # give a bonus for being overdue
            else:
                # inverse of days_left with a soft cap: 1 / (1 + days_left)
                raw_urgencies[tid] = 1.0 / (1 + days_left)

    # For effort: lower estimated_hours => higher 'effort_score' (quick wins)
    efforts = {tid: t["estimated_hours"] for tid, t in tasks.items()}

    importance = {tid: t["importance"] for tid, t in tasks.items()}

    # Dependency score: tasks that are dependencies (i.e., some tasks depend on them) get higher score
    blocked_count = {tid: 0 for tid in tasks}
    for tid, t in tasks.items():
        for dep in t["dependencies"]:
            if dep in blocked_count:
                blocked_count[dep] += 1

    # Prepare normalization ranges
    urg_vals = list(raw_urgencies.values())
    # For normalization, handle constant case
    min_urg = min(urg_vals) if urg_vals else 0.0
    max_urg = max(urg_vals) if urg_vals else 1.0

    min_eff = min(efforts.values()) if efforts else 0.0
    max_eff = max(efforts.values()) if efforts else 1.0

    min_imp = min(importance.values()) if importance else 1
    max_imp = max(importance.values()) if importance else 10

    min_block = min(blocked_count.values()) if blocked_count else 0
    max_block = max(blocked_count.values()) if blocked_count else 1

    result = []
    for tid, t in tasks.items():
        # normalized urgency: higher => more urgent
        n_urg = normalize(raw_urgencies[tid], min_urg, max_urg)
        # normalized importance [0..1]
        n_imp = normalize(t["importance"], min_imp, max_imp)
        # normalized effort: lower estimated_hours => higher score
        inv_effort = max_eff - t["estimated_hours"]
        # map inv_effort to [0..1]
        n_eff = normalize(inv_effort, max_eff - max_eff, max_eff - min_eff) if max_eff != min_eff else 0.0
        # normalized dependency
        n_dep = normalize(blocked_count.get(tid, 0), min_block, max_block)

        # base score is weighted sum
        score = (
            weights.get("urgency", 0) * n_urg
            + weights.get("importance", 0) * n_imp
            + weights.get("effort", 0) * n_eff
            + weights.get("dependency", 0) * n_dep
        )

        # boosts / penalties
        reasons = []
        if t.get("cycle"):
            # penalize slightly because circular dependencies need manual resolution
            score *= 0.7
            reasons.append("circular dependency detected (penalized)")

        if days_left_map[tid] is not None:
            dl = days_left_map[tid]
            if dl < 0:
                reasons.append(f"overdue by {abs(dl)} day(s)")
            elif dl == 0:
                reasons.append("due today")
            elif dl <= 2:
                reasons.append(f"due in {dl} day(s)")

        if blocked_count.get(tid, 0) > 0:
            reasons.append(f"blocks {blocked_count[tid]} other task(s)")

        if t["estimated_hours"] <= 2:
            reasons.append("quick win (low effort)")

        # Compose explanation
        reason = "; ".join(reasons) if reasons else "balanced priority"

        # ensure score is within 0..1
        score = max(0.0, min(score, 1.0))

        result.append({
            "id": tid,
            "title": t["title"],
            "due_date": t["due_date"],
            "estimated_hours": t["estimated_hours"],
            "importance": t["importance"],
            "dependencies": t["dependencies"],
            "score": round(score, 4),
            "reason": reason,
        })

    # final sort: by descending score, tie-breakers: due date earlier, importance higher, lower estimated_hours
    def sort_key(item):
        dd = item["due_date"]
        if dd is None:
            dd_val = datetime.date.max
        else:
            if isinstance(dd, str):
                dd_val = datetime.date.fromisoformat(dd)
            else:
                dd_val = dd
        return (-item["score"], dd_val, -item["importance"], item["estimated_hours"])

    result.sort(key=sort_key)
    return result
