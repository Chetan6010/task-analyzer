🚀 Task Analyzer — AI-Powered Smart Task Prioritization

An intelligent task-analysis system that scores, sorts, and visualizes tasks using AI-driven heuristics, dependency graphing, deadline intelligence, and an Eisenhower Matrix.
Built with Django REST Framework (backend) + Vanilla JS + D3.js (frontend).

⭐ Features
✅ 1. Smart Task Scoring

Based on weighted factors:

Deadline urgency

Importance

Estimated effort

Dependency complexity

Impact score

Custom strategies (Fastest Wins, Smart Balance, High Impact, Deadline Driven)

🔁 2. Circular Dependency Detection

Finds cycles like:

t1 ➝ t2 ➝ t3 ➝ t1


Prevents impossible task execution flows.

📅 3. Date Intelligence

Understands:

Weekends

Holidays

Days left until deadline

📊 4. Dependency Graph Visualization (D3.js)

Interactive graph highlighting:

Normal nodes (green)

Nodes participating in cycles (red)

📈 5. Eisenhower Matrix (Urgent vs Important)

Automatically classifies tasks into:

Do First

Schedule

Delegate

Eliminate

🧠 6. Learning System (User Feedback)

Users can mark suggestions as “helpful”, improving future recommendations:

{"task_id": "t2", "helpful": true}

🏗️ Tech Stack
Backend (Django)

Django 5

Django REST Framework

Python 3.12

SQLite

Custom scoring engine (AI-like heuristics)

Frontend

HTML / CSS / JavaScript

D3.js for graph visualizations

Fetch API for backend communication

📦 Installation
1. Clone Repository
git clone https://github.com/Chetan6010/task-analyzer.git
cd task-analyzer/backend

2. Create Virtual Environment
python -m venv venv
venv\Scripts\activate

3. Install Dependencies
pip install -r requirements.txt

4. Run Server
python manage.py migrate
python manage.py runserver


Backend will run at:
📌 http://127.0.0.1:8000/

5. Run Frontend

Open:

task-analyzer/frontend/index.html

🔥 API Endpoints
▶ Analyze Tasks

POST /api/tasks/analyze/

▶ Suggestions

GET /api/tasks/suggest/

▶ Feedback

POST /api/tasks/feedback/

🧩 Example Task Input
[
  {
    "id": "t1",
    "title": "Fix login bug",
    "due_date": "2025-11-30",
    "estimated_hours": 2,
    "importance": 8,
    "dependencies": []
  }
]

📊 Dependency Graph Demo

Graph auto-generated using D3.js

Green = Valid nodes

Red = Nodes in a cycle

🎯 Eisenhower Matrix Logic
Quadrant	Meaning	Condition
Q1	Do First	urgent & important
Q2	Schedule	not urgent but important
Q3	Delegate	urgent but not important
Q4	Eliminate	neither urgent nor important
🧠 Algorithms Used
1. Weighted Score Algorithm
score = (urgency * w1) + (importance * w2) + (effort_inverse * w3) + (impact * w4)

2. Graph Cycle Detection (DFS)

Used for:

Circular dependency detection

Visual graph representation

3. Deadline Intelligence
days_left = (due_date - today).days
urgency = 1 - (days_left / threshold)

4. Eisenhower Classification

Based on:

importance

days_left <= 2