from rest_framework.response import Response
from rest_framework.views import APIView

from apps.simulations.auth import SessionTokenMixin
from .models import MarketSnapshot
from .serializers import MarketOverviewSerializer
from .services import collect_market_snapshot


class MarketOverviewView(SessionTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []

    @staticmethod
    def _latest(simulation):
        return (
            MarketSnapshot.objects.filter(simulation=simulation)
            .select_related("fallback_snapshot")
            .prefetch_related("quotes__asset", "fallback_snapshot__quotes__asset")
            .first()
        )

    def get(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        if simulation is None:
            return self.missing_token_response()
        snapshot = self._latest(simulation) or collect_market_snapshot(simulation)
        return Response(MarketOverviewSerializer(snapshot).data)

    def post(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        if simulation is None:
            return self.missing_token_response()
        snapshot = collect_market_snapshot(simulation, force=True)
        return Response(MarketOverviewSerializer(snapshot).data)
