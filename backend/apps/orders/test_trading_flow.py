from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ledger.models import LedgerEntry
from apps.market_data.models import MarketQuote, MarketSnapshot
from apps.portfolios.models import Position
from apps.risk.models import DailyRiskState
from apps.simulations.models import Simulation
from .execution import execute_authorized_proposal
from .models import TradeFill, TradeOrder, TradeProposal
from .services import approve_proposal


class TradingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        created = self.client.post("/api/simulations/", {}, format="json").data
        self.simulation = Simulation.objects.get(id=created["id"])
        self.token = created["session_token"]
        self.headers = {"HTTP_X_DEMO_SESSION_TOKEN": self.token}

    def create_proposal(self, *, side="BUY", amount="500.00000000", quantity=None):
        payload = {"asset": "BTC/USDT", "side": side}
        if side == "BUY":
            payload["amount"] = amount
        else:
            payload["quantity"] = quantity
        response = self.client.post(
            f"/api/simulations/{self.simulation.id}/proposals/",
            payload,
            format="json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def approve(self, proposal, key="approval-key"):
        return self.client.post(
            f"/api/simulations/{self.simulation.id}/proposals/{proposal['id']}/approve/",
            {"version": proposal["version"]},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
            **self.headers,
        )

    def assert_ledger_balanced(self):
        totals = (
            LedgerEntry.objects.filter(transaction__simulation=self.simulation)
            .values("account__asset_code")
            .annotate(total=Sum("amount"))
        )
        self.assertTrue(totals)
        self.assertTrue(all(row["total"] == 0 for row in totals), list(totals))

    def test_valid_buy_is_filled_once_and_updates_wallet_position_and_ledger(self):
        proposal = self.create_proposal()
        self.assertEqual(proposal["status"], "PENDING_APPROVAL")
        self.assertTrue(proposal["risk_summary"]["approved"])

        response = self.approve(proposal)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["proposal"]["status"], "EXECUTED")
        self.assertEqual(response.data["order"]["state"], "FILLED")
        self.assertEqual(len(response.data["order"]["fills"]), 1)

        portfolio = self.simulation.portfolio
        portfolio.refresh_from_db()
        position = portfolio.positions.get(asset__symbol="BTC/USDT")
        self.assertGreater(position.quantity, 0)
        self.assertEqual(position.reserved_quantity, 0)
        self.assertLess(portfolio.available_balance, Decimal("9500"))
        self.assertEqual(portfolio.reserved_balance, 0)
        self.assert_ledger_balanced()

    def test_decimal_rounding_and_fee_are_exact(self):
        proposal = self.create_proposal(amount="250.00000000")
        response = self.approve(proposal, "decimal-key")

        self.assertEqual(response.status_code, 200, response.data)
        fill = TradeFill.objects.get(order__simulation=self.simulation)
        self.assertEqual(fill.price, Decimal("50050.00000000"))
        self.assertEqual(fill.quantity, Decimal("0.004995004995"))
        self.assertEqual(fill.fee, Decimal("0.25000000"))
        self.simulation.portfolio.refresh_from_db()
        self.assertEqual(
            self.simulation.portfolio.available_balance,
            Decimal("9749.75000000"),
        )

    def test_incompatible_decimal_precision_is_rejected(self):
        response = self.client.post(
            f"/api/simulations/{self.simulation.id}/proposals/",
            {"asset": "BTC/USDT", "side": "BUY", "amount": "1.000000001"},
            format="json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.data)

    def test_valid_sell_updates_realized_pnl_and_closes_position(self):
        buy = self.create_proposal()
        self.assertEqual(self.approve(buy, "buy-key").status_code, 200)
        position = self.simulation.portfolio.positions.get(asset__symbol="BTC/USDT")
        sell = self.create_proposal(side="SELL", quantity=str(position.quantity))
        response = self.approve(sell, "sell-key")

        self.assertEqual(response.status_code, 200, response.data)
        position.refresh_from_db()
        self.simulation.portfolio.refresh_from_db()
        self.assertEqual(position.quantity, 0)
        self.assertEqual(position.reserved_quantity, 0)
        self.assertNotEqual(position.realized_pnl, 0)
        self.assertEqual(TradeOrder.objects.filter(simulation=self.simulation).count(), 2)
        self.assert_ledger_balanced()

    def test_buy_above_available_balance_and_operation_limit_is_rejected(self):
        proposal = self.create_proposal(amount="20000.00000000")
        self.assertEqual(proposal["status"], "RISK_REJECTED")
        self.assertIn("INSUFFICIENT_AVAILABLE_BALANCE", proposal["risk_summary"]["codes"])
        self.assertIn("MAX_OPERATION_EXPOSURE", proposal["risk_summary"]["codes"])

    def test_buy_above_asset_exposure_is_rejected(self):
        portfolio = self.simulation.portfolio
        portfolio.available_balance = Decimal("8500")
        portfolio.total_equity = Decimal("10000")
        portfolio.save()
        Position.objects.create(
            portfolio=portfolio,
            asset_id=self.simulation.market_snapshots.first().quotes.get(asset__symbol="BTC/USDT").asset_id,
            quantity=Decimal("0.030000000000"),
            average_cost=Decimal("50000"),
        )
        proposal = self.create_proposal(amount="250.00000000")
        self.assertIn("MAX_ASSET_EXPOSURE", proposal["risk_summary"]["codes"])

    def test_sell_above_available_position_is_rejected(self):
        proposal = self.create_proposal(side="SELL", quantity="0.010000000000")
        self.assertEqual(proposal["status"], "RISK_REJECTED")
        self.assertIn("INSUFFICIENT_ASSET_QUANTITY", proposal["risk_summary"]["codes"])

    def test_daily_loss_limit_blocks_new_buy(self):
        portfolio = self.simulation.portfolio
        portfolio.realized_pnl = Decimal("-250")
        portfolio.save()
        DailyRiskState.objects.update_or_create(
            simulation=self.simulation,
            date=timezone.now().date(),
            defaults={"reference_equity": Decimal("10000"), "opening_realized_pnl": Decimal("0")},
        )
        proposal = self.create_proposal(amount="100.00000000")
        self.assertIn("DAILY_LOSS_LIMIT", proposal["risk_summary"]["codes"])

    def test_expired_proposal_cannot_execute(self):
        proposal = self.create_proposal()
        TradeProposal.objects.filter(pk=proposal["id"]).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        response = self.approve(proposal)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["proposal"]["status"], "EXPIRED")
        self.assertEqual(TradeOrder.objects.filter(simulation=self.simulation).count(), 0)

    def test_stale_quote_rejects_proposal(self):
        MarketSnapshot.objects.filter(simulation=self.simulation).update(
            valid_until=timezone.now() - timedelta(seconds=1)
        )
        proposal = self.create_proposal(amount="100.00000000")
        self.assertIn("STALE_MARKET_QUOTE", proposal["risk_summary"]["codes"])

    def test_significant_price_change_invalidates_authorization(self):
        proposal = self.create_proposal()
        old = self.simulation.market_snapshots.first()
        current = MarketSnapshot.objects.create(
            simulation=self.simulation,
            source=old.source,
            status=MarketSnapshot.Status.READY,
            observed_at=timezone.now(),
            valid_until=timezone.now() + timedelta(minutes=5),
        )
        for quote in old.quotes.select_related("asset"):
            MarketQuote.objects.create(
                snapshot=current,
                asset=quote.asset,
                price=quote.price * (Decimal("1.02") if quote.asset.symbol == "BTC/USDT" else Decimal("1")),
                observed_at=timezone.now(),
            )
        response = self.approve(proposal)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["proposal"]["status"], "INVALIDATED")
        self.assertIn(
            "PRICE_CHANGED_REAPPROVAL_REQUIRED",
            response.data["proposal"]["risk_summary"]["codes"],
        )

    def test_duplicate_approval_never_duplicates_order_or_fill(self):
        proposal = self.create_proposal()
        first = self.approve(proposal, "same-key")
        second = self.approve(proposal, "same-key")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])
        self.assertEqual(TradeOrder.objects.filter(simulation=self.simulation).count(), 1)
        self.assertEqual(TradeOrder.objects.get().fills.count(), 1)

    def test_approval_requires_exact_version_and_idempotency_key(self):
        proposal = self.create_proposal()
        missing_key = self.client.post(
            f"/api/simulations/{self.simulation.id}/proposals/{proposal['id']}/approve/",
            {"version": proposal["version"]},
            format="json",
            **self.headers,
        )
        self.assertEqual(missing_key.status_code, 400)
        self.assertEqual(missing_key.data["code"], "IDEMPOTENCY_KEY_REQUIRED")

        stale_version = self.client.post(
            f"/api/simulations/{self.simulation.id}/proposals/{proposal['id']}/approve/",
            {"version": proposal["version"] + 1},
            format="json",
            HTTP_IDEMPOTENCY_KEY="version-key",
            **self.headers,
        )
        self.assertEqual(stale_version.status_code, 409)
        self.assertEqual(stale_version.data["code"], "PROPOSAL_VERSION_CONFLICT")
        self.assertEqual(TradeOrder.objects.filter(simulation=self.simulation).count(), 0)

    def test_execution_requires_prior_authorization(self):
        data = self.create_proposal()
        proposal = TradeProposal.objects.get(pk=data["id"])
        with self.assertRaises(ValueError):
            execute_authorized_proposal(proposal, idempotency_key="forbidden")

    def test_failure_rolls_back_reservation_order_and_decision(self):
        data = self.create_proposal()
        before = self.simulation.portfolio.available_balance

        def fail(stage):
            if stage == "after_reservation":
                raise RuntimeError("controlled failure")

        with self.assertRaises(RuntimeError):
            approve_proposal(
                simulation=self.simulation,
                proposal_id=data["id"],
                expected_version=data["version"],
                idempotency_key="rollback-key",
                failure_hook=fail,
            )
        self.simulation.portfolio.refresh_from_db()
        self.assertEqual(self.simulation.portfolio.available_balance, before)
        self.assertEqual(TradeOrder.objects.filter(simulation=self.simulation).count(), 0)
        self.assertEqual(self.simulation.proposal_decisions.count(), 0)

    def test_cross_session_cannot_read_or_approve_proposal(self):
        proposal = self.create_proposal()
        other = self.client.post("/api/simulations/", {}, format="json").data
        response = self.client.post(
            f"/api/simulations/{self.simulation.id}/proposals/{proposal['id']}/approve/",
            {"version": proposal["version"]},
            format="json",
            HTTP_X_DEMO_SESSION_TOKEN=other["session_token"],
            HTTP_IDEMPOTENCY_KEY="isolation-key",
        )
        self.assertEqual(response.status_code, 404)
