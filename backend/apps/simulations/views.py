from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ledger.services import bootstrap_portfolio
from apps.market_data.services import collect_market_snapshot
from apps.portfolios.models import Portfolio
from apps.portfolios.serializers import PortfolioSerializer
from apps.risk.models import RiskPolicy
from .auth import SessionTokenMixin
from .models import Simulation
from .serializers import SimulationCreatedSerializer, SimulationSerializer

class SimulationCreateView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        name = str(request.data.get("name", "Empresa Demo")).strip()[:120]
        with transaction.atomic():
            simulation = Simulation.objects.create(name=name or "Empresa Demo")
            portfolio = Portfolio.objects.create(
                simulation=simulation,
                available_balance=simulation.initial_capital,
                reserved_balance=0,
                total_equity=simulation.initial_capital,
                realized_pnl=0,
            )
            bootstrap_portfolio(portfolio)
            RiskPolicy.objects.create(simulation=simulation)
        collect_market_snapshot(simulation)
        return Response(SimulationCreatedSerializer(simulation).data, status=status.HTTP_201_CREATED)

class SimulationDetailView(SessionTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        if simulation is None:
            return self.missing_token_response()
        return Response(SimulationSerializer(simulation).data)

class PortfolioDetailView(SessionTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        if simulation is None:
            return self.missing_token_response()
        return Response(PortfolioSerializer(simulation.portfolio).data)

