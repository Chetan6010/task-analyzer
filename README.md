# Smart Task Analyzer (Internship Assignment)

## Overview
This project implements a mini task management system that scores and sorts tasks using a configurable priority algorithm. Backend: Django + Django REST Framework. Frontend: simple HTML/CSS/JS that calls the API.

## Quick setup (Linux / macOS / Windows WSL)
1. Clone repo:
git clone <your-repo-url>
cd task-analyzer/backend

markdown
Copy code
2. Create virtualenv & install:
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt

markdown
Copy code
3. Run migrations and start server:
python manage.py migrate
python manage.py runserver

swift
Copy code
4. Open `frontend/index.html` in the browser (or serve static files via Django). The frontend expects API to be reachable at `/api/tasks/analyze/`.

## API Endpoints
- `POST /api/tasks/analyze/?strategy=<strategy>`  
Accepts JSON array of tasks. Returns tasks sorted with `score` and `reason`.

- `GET /api/tasks/suggest/`  
Provide JSON body: `{ "tasks": [...] }`. Returns top 3 suggestions with explanations.

### Task input format
Each task object:
```json
{
"id": "optional-id",
"title": "Fix login bug",
"due_date": "YYYY-MM-DD or null",
"estimated_hours": 3,
"importance": 8,
"dependencies": ["id1", "id2"]
}
Algorithm explanation (≈350 words)
The priority algorithm balances four factors: urgency, importance, effort, and dependency impact, with configurable weights and strategy presets.

Urgency: computed from days to due date. Tasks overdue receive a strong boost. A continuous transformation maps days-left into a raw urgency where immediate or overdue tasks score higher. This allows the algorithm to surface overdue and near-term items gracefully rather than using simple thresholds.

Importance: uses user-provided 1–10 rating, normalized across the current task set. This prevents a single high value from dominating when other tasks also have high importance.

Effort: lower estimated_hours are treated as "quick wins". Effort is inverted so smaller hours produce a higher normalized score. This encourages selecting short tasks where appropriate (e.g., "Fastest Wins" strategy).

Dependency: tasks that block others (i.e., are referenced by other tasks' dependencies) receive higher weight. This pushes upstream blockers forward because resolving them unlocks more work.
The algorithm normalizes each factor across the input set to produce values in [0,1], applies configurable weights, and composes a weighted sum. The smart_balance preset uses balanced weights (urgency ~0.35, importance ~0.35, effort ~0.15, dependency ~0.15). Other presets shift emphasis (e.g., deadline_driven centers on urgency, fastest_wins centers on low effort).
Circular dependency detection runs before scoring: if a cycle is detected, tasks in the cycle are flagged and slightly penalized (score multiplied by 0.7). This signals that human resolution is required. The algorithm is configurable — custom weight maps can be passed to the analyze endpoint if you want different trade-offs.
Finally, sorting uses (1) descending score, (2) earlier due date, (3) higher importance, (4) lower estimated hours as tie-breakers. The API returns per-task reason text summarizing why the score is high (e.g., "overdue", "blocks X tasks", "quick win") to aid user understanding.

Design decisions & trade-offs
Normalization per request: scores are relative to the current list; this fits the assignment where the API receives an ad-hoc list.

Overdue handling: overdue tasks get a fixed boost and scale with how long overdue they are; this avoids infinite escalation but ensures attention.

Circular dependencies: rather than auto-resolving, the algorithm flags cycles and penalizes to avoid misleading prioritization.

Persistence optional: a Task model exists for optional saving, but core APIs operate on provided in-memory lists for simplicity and testability.

Time Breakdown (approx)
Algorithm design & scoring: 60 min

Backend endpoints & serializers: 45 min

Frontend UI & JS: 30 min

Unit tests & README: 25 min
Total: ~3 hours

Unit tests
backend/tasks/tests.py contains tests for basic ordering, circular dependency detection, and overdue boosting.

Future improvements
Add dependency graph visualization (D3/vis.js).

Allow user weighting config UI and persistence.

Integrate calendar/holidays for more accurate urgency.

Add auth & persistent user tasks.

Add learning loop to adjust weights based on feedback.

markdown
Copy code

---

# 6 — Important notes, edge cases & behavior

- **Tasks with missing fields**: API validates and returns `400` with validation errors. `importance` defaults to 5 if missing via serializer defaults, `estimated_hours` defaults to 1.0.
- **Due dates in the past**: scored with a boost; overdue gets higher urgency. Overdue tasks also show reason like `overdue by X day(s)`.
- **Circular dependencies**: detected with DFS; tasks involved are flagged and penalized. The API does not auto-resolve cycles — it reports them in `reason`.
- **Configurability**: you may pass `?strategy=fastest_wins` etc. Custom weights can be passed as a `weights` object in the first task's payload (code reads `weights` if present) — this allows dynamic tuning.
- **Score scale**: normalized to 0..1 and rounded to 4 decimal places. Sorting then uses tie-breakers.

---

# 7 — How to proceed (recommended)

1. Copy files into the structure above.
2. `cd backend`, create venv, install `requirements.txt`.
3. `python manage.py migrate` then `python manage.py runserver`.
4. Serve `frontend/index.html` (open file locally; if the browser blocks `fetch` due to CORS when opening `file://`, run a simple static server, e.g. `python -m http.server` from `frontend/` and visit `http://localhost:8000/index.html` and ensure Django server is on same host/port or adjust fetch URL to `http://localhost:8000/api/tasks/analyze/`).

---

If you want, I can:
- Paste all files as ready-to-save text (I already did inline — but I can create a zip for download if you prefer), or
- Create a Git commit history example (a suggested sequence of commit messages and diffs), or
- Implement bonus features (dependency graph, holiday-aware urgency), or
- Convert backend to a standalone FastAPI solution.

Which of these would you like next?