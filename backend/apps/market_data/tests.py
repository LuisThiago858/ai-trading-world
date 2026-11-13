from django.test import TestCase
from rest_framework.test import APIClient

from .models import MarketCandle, MarketSnapshot
from .providers import MarketProviderUnavailable
from .serializers import MarketOverviewSerializer
from .services import collect_market_snapshot


class UnavailableProvider:
    def fetch(self):
        raise MarketProviderUnavailable("Falha pública controlada para teste.")


class MarketDataTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        response = self.client.post("/api/simulations/", {}, format="json")
        self.simulation_id = response.data["id"]
        self.token = response.data["session_token"]

    def test_fixture_is_deterministic_persisted_and_cached(self):
        from apps.simulations.models import Simulation

        simulation = Simulation.objects.get(id=self.simulation_id)
        first = MarketSnapshot.objects.filter(simulation=simulation).first()
        second = collect_market_snapshot(simulation)

        self.assertEqual(first.id, second.id)
        prices = {quote.asset.symbol: quote.price for quote in first.quotes.select_related("asset")}
        self.assertEqual(str(prices["BTC/USDT"]), "50000.00000000")
        self.assertEqual(str(prices["ETH/USDT"]), "3000.00000000")
        self.assertEqual(MarketCandle.objects.filter(source="DEMO_FIXTURE").count(), 2)

    def test_provider_unavailability_records_attempt_and_uses_fallback(self):
        from apps.simulations.models import Simulation

        simulation = Simulation.objects.get(id=self.simulation_id)
        failed = collect_market_snapshot(simulation, provider=UnavailableProvider(), force=True)
        payload = MarketOverviewSerializer(failed).data

        self.assertEqual(failed.status, MarketSnapshot.Status.UNAVAILABLE)
        self.assertIsNotNone(failed.fallback_snapshot)
        self.assertTrue(payload["using_fallback"])
        self.assertEqual(len(payload["quotes"]), 2)
        self.assertIn("Falha pública controlada", payload["error"])

    def test_market_endpoint_isolated_by_session_token(self):
        other = self.client.post("/api/simulations/", {}, format="json").data
        url = f"/api/simulations/{self.simulation_id}/market/"
        wrong = self.client.get(url, HTTP_X_DEMO_SESSION_TOKEN=other["session_token"])
        own = self.client.get(url, HTTP_X_DEMO_SESSION_TOKEN=self.token)
        self.assertEqual(wrong.status_code, 404)
        self.assertEqual(own.status_code, 200)
        self.assertEqual({quote["symbol"] for quote in own.data["quotes"]}, {"BTC/USDT", "ETH/USDT"})
