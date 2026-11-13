from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.market_data.models import Asset
from apps.simulations.models import Simulation
from .models import Position


class PortfolioTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        response = self.client.post("/api/simulations/", {}, format="json")
        self.simulation = Simulation.objects.get(id=response.data["id"])
        self.token = response.data["session_token"]

    def test_position_calculations_use_decimal(self):
        position = Position(
            portfolio=self.simulation.portfolio,
            asset=Asset.objects.get(symbol="BTC/USDT"),
            quantity=Decimal("0.123456789012"),
            average_cost=Decimal("40000.12345678"),
        )
        price = Decimal("50000.87654321")
        self.assertIsInstance(position.market_value(price), Decimal)
        self.assertEqual(position.unrealized_pnl(price), position.market_value(price) - position.cost_basis())

    def test_portfolio_history_is_read_only_and_isolated(self):
        other = self.client.post("/api/simulations/", {}, format="json").data
        url = f"/api/simulations/{self.simulation.id}/portfolio/history/"
        self.assertEqual(
            self.client.get(url, HTTP_X_DEMO_SESSION_TOKEN=other["session_token"]).status_code,
            404,
        )
        response = self.client.get(url, HTTP_X_DEMO_SESSION_TOKEN=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["available_balance"], "10000.00000000")
