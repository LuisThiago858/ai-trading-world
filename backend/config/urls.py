from django.urls import include, path
from apps.health.views import HealthView

urlpatterns = [
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/simulations/", include("apps.simulations.urls")),
    path("api/", include("apps.agents.urls")),
]

