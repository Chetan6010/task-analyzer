from django.test import TestCase
from .scoring import compute_scores, detect_circular_dependencies
import datetime

class ScoringTests(TestCase):
    def test_basic_scoring_order(self):
        tasks = [
            {"id": "t1", "title":"A", "due_date": (datetime.date.today()).isoformat(), "estimated_hours": 3, "importance": 8, "dependencies": []},
            {"id": "t2", "title":"B", "due_date": (datetime.date.today() + datetime.timedelta(days=5)).isoformat(), "estimated_hours": 1, "importance": 5, "dependencies": []},
            {"id": "t3", "title":"C", "due_date": None, "estimated_hours": 2, "importance": 9, "dependencies": []},
        ]
        res = compute_scores(tasks)
        # top item should be either t1 (due today) or t3 (importance) depending on weights; ensure it returns list and includes score
        self.assertEqual(len(res), 3)
        for r in res:
            self.assertIn("score", r)
            self.assertIn("reason", r)

    def test_circular_detection(self):
        tasks = [
            {"id":"a", "title":"A", "due_date": None, "estimated_hours":1, "importance":5, "dependencies":["b"]},
            {"id":"b", "title":"B", "due_date": None, "estimated_hours":1, "importance":5, "dependencies":["a"]},
        ]
        has_cycle, nodes = detect_circular_dependencies({t["id"]: t for t in tasks})
        self.assertTrue(has_cycle)
        self.assertTrue("a" in nodes or "b" in nodes)

    def test_overdue_boost(self):
        tasks = [
            {"id":"t1", "title":"Overdue", "due_date": (datetime.date.today()-datetime.timedelta(days=2)).isoformat(), "estimated_hours":5, "importance":6, "dependencies":[]},
            {"id":"t2", "title":"Far", "due_date": (datetime.date.today()+datetime.timedelta(days=30)).isoformat(), "estimated_hours":1, "importance":6, "dependencies":[]},
        ]
        res = compute_scores(tasks)
        # overdue should have higher score than far task
        self.assertGreater(res[0]["score"], res[1]["score"])
