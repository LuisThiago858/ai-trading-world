from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from apps.portfolios.models import Portfolio
from apps.ledger.models import LedgerTransaction
from apps.market_data.models import MarketQuote
from .models import Simulation

class SimulationApiTests(TestCase):
    def setUp(self): self.client = APIClient()
    def create_session(self, name="Mesa Demo"):
        response = self.client.post("/api/simulations/", {"name": name}, format="json")
        self.assertEqual(response.status_code, 201)
        return response
    def test_creates_session_with_exact_decimal_balance(self):
        response = self.create_session()
        simulation = Simulation.objects.get(id=response.data["id"])
        portfolio = Portfolio.objects.get(simulation=simulation)
        self.assertIsInstance(simulation.initial_capital, Decimal)
        self.assertEqual(simulation.initial_capital, Decimal("10000.00000000"))
        self.assertEqual(portfolio.available_balance, Decimal("10000.00000000"))
        self.assertEqual(portfolio.reserved_balance, Decimal("0"))
        self.assertEqual(response.data["initial_capital"], "10000.00000000")
        self.assertEqual(LedgerTransaction.objects.filter(simulation=simulation).count(), 1)
        self.assertEqual(MarketQuote.objects.filter(snapshot__simulation=simulation).count(), 2)
    def test_portfolio_is_empty_and_requires_own_session_token(self):
        first, second = self.create_session("Primeira"), self.create_session("Segunda")
        url = f'/api/simulations/{first.data["id"]}/portfolio/'
        self.assertEqual(self.client.get(url).status_code, 401)
        wrong = self.client.get(url, HTTP_X_DEMO_SESSION_TOKEN=second.data["session_token"])
        self.assertEqual(wrong.status_code, 404)
        own = self.client.get(url, HTTP_X_DEMO_SESSION_TOKEN=first.data["session_token"])
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.data["positions"], [])
        self.assertEqual(own.data["available_balance"], "10000.00000000")
        self.assertEqual(own.data["reserved_balance"], "0.00000000")
    def test_health_marks_virtual_demo_mode(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["trading"], "virtual-only")
