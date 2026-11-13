from django.urls import path

from .views import AnalysisCancelView, AnalysisDetailView, AgentResultListView


urlpatterns = [
    path("analysis-runs/<uuid:run_id>/", AnalysisDetailView.as_view(), name="analysis-detail"),
    path("analysis-runs/<uuid:run_id>/agent-results/", AgentResultListView.as_view(), name="analysis-agent-results"),
    path("analysis-runs/<uuid:run_id>/cancel/", AnalysisCancelView.as_view(), name="analysis-cancel"),
]
