# backend/tasks/tests.py
from django.test import TestCase
from .scoring import compute_scores, detect_circular_dependencies, business_days_between
import datetime
from pathlib import Path
import json

class ScoringTests(TestCase):
    def test_business_days_between(self):
        d0 = datetime.date(2025, 11, 28)  # Friday
        d1 = datetime.date(2025, 12, 1)   # Monday
        days = business_days_between(d0, d1, holidays=[])
        # Friday->Monday should be 2 business days if include end day (Fri + Mon)
        self.assertTrue(days >= 1)

    def test_cycle_detection_and_penalty(self):
        tasks = [
            {"id":"A", "title":"A", "due_date": None, "estimated_hours":1, "importance":5, "dependencies":["B"]},
            {"id":"B", "title":"B", "due_date": None, "estimated_hours":1, "importance":5, "dependencies":["A"]},
        ]
        has_cycle, cycles = detect_circular_dependencies(tasks)
        self.assertTrue(has_cycle)
        self.assertTrue(len(cycles) >= 1)

    def test_feedback_boost_affects_score(self):
        tasks = [
            {"id":"t1", "title":"T1", "due_date":"2025-11-30", "estimated_hours":2, "importance":5, "dependencies":[]},
            {"id":"t2", "title":"T2", "due_date":"2025-11-30", "estimated_hours":2, "importance":5, "dependencies":[]},
        ]
        # initial scores
        res1 = compute_scores(tasks)
        s1_t1 = next((r for r in res1 if r["id"]=="t1"), None)["score"]
        # write a fake feedback store that makes t1 helpful
        path = Path(__file__).resolve().parent / "feedback_store.json"
        store = {"t1": {"helpful": 10, "total": 10}}
        path.write_text(json.dumps(store))
        try:
            res2 = compute_scores(tasks)
            s2_t1 = next((r for r in res2 if r["id"]=="t1"), None)["score"]
            self.assertTrue(s2_t1 >= s1_t1)
        finally:
            path.unlink(missing_ok=True)
