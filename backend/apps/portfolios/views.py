from rest_framework.response import Response
from rest_framework.views import APIView

from apps.simulations.auth import SessionTokenMixin
from .serializers import PortfolioSnapshotSerializer


class PortfolioHistoryView(SessionTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        if simulation is None:
            return self.missing_token_response()
        history = simulation.portfolio.history.all()[:100]
        return Response(PortfolioSnapshotSerializer(history, many=True).data)
