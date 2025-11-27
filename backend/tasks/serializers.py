from rest_framework import serializers

class TaskInputSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    title = serializers.CharField()
    due_date = serializers.DateField(required=False, allow_null=True)
    estimated_hours = serializers.FloatField(required=False, default=1.0)
    importance = serializers.IntegerField(required=False, default=5, min_value=1, max_value=10)
    dependencies = serializers.ListField(child=serializers.CharField(), required=False, default=list)

class AnalyzeResponseTaskSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    title = serializers.CharField()
    due_date = serializers.DateField(required=False, allow_null=True)
    estimated_hours = serializers.FloatField()
    importance = serializers.IntegerField()
    dependencies = serializers.ListField(child=serializers.CharField())
    score = serializers.FloatField()
    reason = serializers.CharField()
