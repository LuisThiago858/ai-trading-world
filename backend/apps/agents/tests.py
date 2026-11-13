import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from celery.exceptions import SoftTimeLimitExceeded
from django.test import TestCase
from django.utils import timezone
from pydantic import ValidationError
from rest_framework.test import APIClient

from apps.market_data.models import MarketCandle
from apps.orders.models import TradeOrder, TradeProposal
from apps.orders.services import approve_proposal, create_manual_proposal
from apps.simulations.models import Simulation
from .indicators import calculate_indicators, ema, macd, rsi, sma, volatility
from .models import AgentResult, AnalysisRun
from .orchestrator import execute_analysis_run
from .providers import DeterministicMockProvider, LLMProviderError
from .schemas import AlexOutput, MayaOutput
from .services import create_analysis_run
from .tasks import process_analysis_run


class FailingProvider:
    name = "failing"
    model = "failure-v1"

    def generate(self, **kwargs):
        raise LLMProviderError(
            "Falha transitória controlada.", transient=True,
            code="LLM_TEMPORARILY_UNAVAILABLE",
        )


class IndicatorTests(TestCase):
    def test_indicators_are_decimal_and_handle_insufficient_history(self):
        values = [Decimal(index) for index in range(1, 41)]
        self.assertEqual(sma(values, 5), Decimal("38"))
        self.assertIsNotNone(ema(values, 12))
        self.assertEqual(rsi(values, 14), Decimal("100"))
        self.assertIsNotNone(macd(values))
        self.assertIsNotNone(volatility(values))
        self.assertIsNone(sma(values[:4], 5))
        self.assertIsNone(rsi(values[:14], 14))
        self.assertIsNone(macd(values[:20]))

    def test_output_schemas_reject_incoherent_or_extra_data(self):
        with self.assertRaises(ValidationError):
            MayaOutput.model_validate({
                "action": "HOLD", "asset": "BTC/USDT", "allocation_percent": "1",
                "favorable_arguments": [], "hold_arguments": [], "disagreements": [],
                "reasoning": "inválido", "unexpected": True,
            })
        with self.assertRaises(ValidationError):
            AlexOutput.model_validate({
                "assessments": [], "selected_asset": None, "action": "BUY", "summary": "inválido"
            })


class MultiAgentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        created = self.client.post("/api/simulations/", {}, format="json").data
        self.simulation = Simulation.objects.get(pk=created["id"])
        self.token = created["session_token"]
        self.headers = {"HTTP_X_DEMO_SESSION_TOKEN": self.token}

    def make_run(self, assets=("BTC/USDT",), key=None):
        return AnalysisRun.objects.create(
            simulation=self.simulation,
            market_snapshot=self.simulation.market_snapshots.first(),
            requested_assets=list(assets),
            request_idempotency_key=key or str(uuid.uuid4()),
            graph_thread_id=f"test-{uuid.uuid4()}",
            provider="deterministic_mock",
            provider_mode="mock",
            model_name="deterministic-mock-v1",
        )

    def seed_trend(self, symbol="BTC/USDT", *, rising=True):
        snapshot = self.simulation.market_snapshots.first()
        asset = snapshot.quotes.get(asset__symbol=symbol).asset
        start = Decimal("49000") if rising else Decimal("51000")
        direction = Decimal("25") if rising else Decimal("-25")
        for index in range(40):
            close = start + direction * index
            MarketCandle.objects.create(
                asset=asset,
                source=snapshot.source,
                interval_minutes=1,
                opened_at=snapshot.observed_at - timedelta(minutes=40 - index),
                open=close - direction,
                high=close + Decimal("10"),
                low=close - Decimal("10"),
                close=close,
                volume=Decimal("10"),
                trade_count=5,
                is_closed=True,
            )

    def test_full_mock_graph_with_fixture_persists_hold_history(self):
        run = self.make_run(("BTC/USDT", "ETH/USDT"))
        execute_analysis_run(run.id)
        run.refresh_from_db()
        self.assertEqual(run.status, AnalysisRun.Status.COMPLETED)
        self.assertEqual(run.conclusion["action"], "HOLD")
        self.assertEqual(run.agent_results.count(), 3)
        self.assertEqual(run.checkpoints.count(), 4)
        self.assertEqual(run.proposals.count(), 0)
        self.assertTrue(all(result.provider == "deterministic_mock" for result in run.agent_results.all()))

    def test_valid_ai_buy_creates_pending_proposal_but_no_order(self):
        self.seed_trend(rising=True)
        run = self.make_run()
        execute_analysis_run(run.id)
        run.refresh_from_db()
        proposal = run.proposals.get()
        self.assertEqual(run.conclusion["action"], "BUY")
        self.assertEqual(proposal.origin, TradeProposal.Origin.AI_AGENT)
        self.assertEqual(proposal.status, TradeProposal.Status.PENDING_APPROVAL)
        self.assertEqual(TradeOrder.objects.filter(simulation=self.simulation).count(), 0)
        approved, order, _ = approve_proposal(
            simulation=self.simulation,
            proposal_id=proposal.id,
            expected_version=proposal.version,
            idempotency_key="ai-buy-approval",
        )
        self.assertEqual(approved.status, TradeProposal.Status.EXECUTED)
        self.assertEqual(order.state, TradeOrder.State.FILLED)

    def test_valid_ai_sell_uses_existing_position(self):
        buy = create_manual_proposal(
            simulation=self.simulation,
            symbol="BTC/USDT",
            side="BUY",
            requested_amount=Decimal("500"),
        )
        approve_proposal(
            simulation=self.simulation, proposal_id=buy.id,
            expected_version=buy.version, idempotency_key="seed-position",
        )
        self.seed_trend(rising=False)
        run = self.make_run()
        execute_analysis_run(run.id)
        proposal = run.proposals.get()
        self.assertEqual(proposal.side, TradeProposal.Side.SELL)
        self.assertEqual(proposal.status, TradeProposal.Status.PENDING_APPROVAL)
        self.assertGreater(proposal.requested_quantity, 0)
        self.assertEqual(TradeOrder.objects.filter(simulation=self.simulation).count(), 1)

    def test_victor_keeps_risk_rejected_proposal_blocked(self):
        self.seed_trend(rising=True)
        policy = self.simulation.risk_policy
        policy.max_operation_percent = Decimal("1")
        policy.save()
        run = self.make_run()
        execute_analysis_run(run.id)
        run.refresh_from_db()
        proposal = run.proposals.get()
        victor = run.agent_results.get(agent=AgentResult.Agent.VICTOR)
        self.assertEqual(proposal.status, TradeProposal.Status.RISK_REJECTED)
        self.assertEqual(run.conclusion["action"], "HOLD")
        self.assertIn("MAX_OPERATION_EXPOSURE", victor.conclusion["risk_codes"])

    def test_stale_snapshot_fails_without_calling_llm_or_creating_proposal(self):
        run = self.make_run()
        run.market_snapshot.valid_until = timezone.now() - timedelta(seconds=1)
        run.market_snapshot.save(update_fields=("valid_until",))
        execute_analysis_run(run.id)
        run.refresh_from_db()
        self.assertEqual(run.status, AnalysisRun.Status.FAILED)
        self.assertEqual(run.error["code"], "STALE_MARKET_SNAPSHOT")
        self.assertEqual(run.proposals.count(), 0)

    def test_provider_unavailability_is_structured_and_recoverable(self):
        run = self.make_run()
        with self.assertRaises(LLMProviderError):
            execute_analysis_run(run.id, provider=FailingProvider())
        run.refresh_from_db()
        self.assertEqual(run.status, AnalysisRun.Status.FAILED)
        self.assertTrue(run.error["transient"])
        execute_analysis_run(run.id, provider=DeterministicMockProvider())
        run.refresh_from_db()
        self.assertEqual(run.status, AnalysisRun.Status.COMPLETED)
        self.assertEqual(run.attempts, 2)

    def test_task_timeout_records_failure(self):
        run = self.make_run()
        with patch("apps.agents.tasks.execute_analysis_run", side_effect=SoftTimeLimitExceeded()):
            result = process_analysis_run.apply(args=(str(run.id),), throw=False)
        run.refresh_from_db()
        self.assertTrue(result.failed())
        self.assertEqual(run.error["code"], "ANALYSIS_TIMEOUT")

    def test_task_retries_a_transient_provider_failure(self):
        run = self.make_run()
        transient = LLMProviderError("temporário", transient=True, code="LLM_TEMPORARILY_UNAVAILABLE")
        with patch("apps.agents.tasks.execute_analysis_run", side_effect=[transient, run]) as execute:
            result = process_analysis_run.apply(args=(str(run.id),), throw=False)
        self.assertTrue(result.successful(), result.result)
        self.assertEqual(execute.call_count, 2)

    def test_duplicate_request_and_session_isolation(self):
        with patch("apps.agents.services._dispatch"):
            first, created = create_analysis_run(
                simulation=self.simulation, assets=["BTC/USDT"], idempotency_key="same-analysis"
            )
            second, duplicated = create_analysis_run(
                simulation=self.simulation, assets=["BTC/USDT"], idempotency_key="same-analysis"
            )
        self.assertTrue(created)
        self.assertFalse(duplicated)
        self.assertEqual(first.id, second.id)
        other = self.client.post("/api/simulations/", {}, format="json").data
        wrong = self.client.get(
            f"/api/analysis-runs/{first.id}/",
            HTTP_X_DEMO_SESSION_TOKEN=other["session_token"],
        )
        own = self.client.get(f"/api/analysis-runs/{first.id}/", **self.headers)
        self.assertEqual(wrong.status_code, 404)
        self.assertEqual(own.status_code, 200)
        self.assertIn("mock determinístico", own.data["mock_notice"])

    def test_api_requires_idempotency_and_supports_cancel_and_pagination(self):
        url = f"/api/simulations/{self.simulation.id}/analysis-runs/"
        missing = self.client.post(url, {"assets": ["BTC/USDT"]}, format="json", **self.headers)
        self.assertEqual(missing.status_code, 400)
        with patch("apps.agents.services._dispatch"):
            created = self.client.post(
                url, {"assets": ["BTC/USDT"]}, format="json",
                HTTP_IDEMPOTENCY_KEY="api-analysis", **self.headers,
            )
        self.assertEqual(created.status_code, 202, created.data)
        listed = self.client.get(f"{url}?limit=1&offset=0", **self.headers)
        self.assertEqual(listed.data["count"], 1)
        cancelled = self.client.post(
            f"/api/analysis-runs/{created.data['id']}/cancel/", {}, format="json", **self.headers
        )
        self.assertEqual(cancelled.data["status"], "CANCELLED")

    def test_manual_proposals_remain_compatible(self):
        proposal = create_manual_proposal(
            simulation=self.simulation, symbol="ETH/USDT", side="BUY", requested_amount="100"
        )
        self.assertEqual(proposal.origin, TradeProposal.Origin.MANUAL)
        self.assertIsNone(proposal.analysis_run_id)
