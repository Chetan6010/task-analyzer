# backend/tasks/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import TaskInputSerializer
from .scoring import compute_scores, detect_circular_dependencies
import datetime
from pathlib import Path
import json

FEEDBACK_STORE = Path(__file__).resolve().parent / "feedback_store.json"

class AnalyzeTasksAPIView(APIView):
    def post(self, request):
        # Accepts list of tasks
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "expected a JSON array of tasks"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate entries
        validated = []
        errors = []
        for idx, item in enumerate(data):
            ser = TaskInputSerializer(data=item)
            if ser.is_valid():
                validated.append(ser.validated_data)
            else:
                errors.append({"index": idx, "errors": ser.errors})

        if errors:
            return Response({"validation_errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        strategy = request.query_params.get("strategy", "smart_balance")
        weights_param = request.data[0].get("weights") if request.data else None
        custom_weights = None
        if weights_param and isinstance(weights_param, dict):
            custom_weights = weights_param

        today_str = request.query_params.get("today")
        today = None
        if today_str:
            try:
                today = datetime.date.fromisoformat(today_str)
            except Exception:
                today = None

        # optional holidays may be passed as query param ?holidays=["2025-12-25",...]
        holidays = request.query_params.getlist("holidays") if hasattr(request.query_params, "getlist") else None
        results = compute_scores(validated, strategy=strategy, custom_weights=custom_weights, today=today, holidays=holidays)
        # detect cycles (detailed cycles as lists)
        has_cycle, cycles = detect_circular_dependencies(validated)
        return Response({"tasks": results, "cycles": cycles}, status=status.HTTP_200_OK)
    
class SuggestTasksAPIView(APIView):
    def get(self, request):
        tasks = request.data.get("tasks") if isinstance(request.data, dict) else None
        if tasks is None:
            return Response({"error": "provide tasks as JSON body under key 'tasks' (array)"}, status=400)

        validated = []
        errors = []
        for idx, item in enumerate(tasks):
            ser = TaskInputSerializer(data=item)
            if ser.is_valid():
                validated.append(ser.validated_data)
            else:
                errors.append({"index": idx, "errors": ser.errors})

        if errors:
            return Response({"validation_errors": errors}, status=400)

        strategy = request.query_params.get("strategy", "smart_balance")
        results = compute_scores(validated, strategy=strategy)
        top3 = results[:3]

        return Response({"suggestions": top3}, status=200)


class FeedbackAPIView(APIView):
    """
    POST payload: {"task_id": "t1", "helpful": true}
    Stores simple helpful / total counters in feedback_store.json
    """
    def post(self, request):
        data = request.data
        task_id = data.get("task_id")
        helpful = data.get("helpful")
        if not task_id or not isinstance(helpful, bool):
            return Response({"error": "provide task_id and boolean helpful"}, status=status.HTTP_400_BAD_REQUEST)

        store = {}
        if FEEDBACK_STORE.exists():
            try:
                with FEEDBACK_STORE.open("r", encoding="utf-8") as f:
                    store = json.load(f)
            except Exception:
                store = {}

        rec = store.get(task_id, {"helpful": 0, "total": 0})
        rec["total"] = rec.get("total", 0) + 1
        if helpful:
            rec["helpful"] = rec.get("helpful", 0) + 1
        store[task_id] = rec
        try:
            with FEEDBACK_STORE.open("w", encoding="utf-8") as f:
                json.dump(store, f)
        except Exception as e:
            return Response({"error": "unable to save feedback", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"status": "ok", "task_id": task_id, "helpful": helpful, "summary": store[task_id]}, status=status.HTTP_200_OK)
