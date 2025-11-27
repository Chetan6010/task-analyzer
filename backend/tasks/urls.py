from django.urls import path
from .views import AnalyzeTasksAPIView, FeedbackAPIView, SuggestTasksAPIView

urlpatterns = [
    path("analyze/", AnalyzeTasksAPIView.as_view()),
    path("feedback/", FeedbackAPIView.as_view()),
    path("suggest/", SuggestTasksAPIView.as_view()),
]
