from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import TaskInputSerializer, AnalyzeResponseTaskSerializer
from .scoring import compute_scores, STRATEGY_PRESETS, detect_circular_dependencies
import datetime

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

        # compute today optionally
        today_str = request.query_params.get("today")
        today = None
        if today_str:
            try:
                today = datetime.date.fromisoformat(today_str)
            except Exception:
                today = None

        results = compute_scores(validated, strategy=strategy, custom_weights=custom_weights, today=today)
        return Response({"tasks": results}, status=status.HTTP_200_OK)

class SuggestTasksAPIView(APIView):
    def get(self, request):
        # Expect tasks to be passed via query param or body: allow body
        tasks = request.data.get("tasks") if isinstance(request.data, dict) else None
        if tasks is None:
            # fallback to query param 'tasks' containing JSON string is not implemented; require JSON body
            return Response({"error": "provide tasks as JSON body under key 'tasks' (array)"}, status=status.HTTP_400_BAD_REQUEST)

        # validate:
        validated = []
        from .serializers import TaskInputSerializer
        errors = []
        for idx, item in enumerate(tasks):
            ser = TaskInputSerializer(data=item)
            if ser.is_valid():
                validated.append(ser.validated_data)
            else:
                errors.append({"index": idx, "errors": ser.errors})
        if errors:
            return Response({"validation_errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        strategy = request.query_params.get("strategy", "smart_balance")
        results = compute_scores(validated, strategy=strategy)
        # top 3
        top3 = results[:3]
        # add human-friendly explanations (already 'reason')
        return Response({"suggestions": top3}, status=status.HTTP_200_OK)
