from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.market_data.models import Asset, MarketSnapshot
from apps.simulations.models import Simulation
from .models import TradeOrder, TradeProposal


class OrderDomainTests(TestCase):
    def setUp(self):
        response = APIClient().post("/api/simulations/", {}, format="json")
        self.simulation = Simulation.objects.get(id=response.data["id"])
        self.asset = Asset.objects.get(symbol="BTC/USDT")
        self.snapshot = MarketSnapshot.objects.filter(simulation=self.simulation).first()

    def proposal(self, status=TradeProposal.Status.DRAFT, authorized_at=None):
        return TradeProposal.objects.create(
            simulation=self.simulation,
            market_snapshot=self.snapshot,
            asset=self.asset,
            side=TradeProposal.Side.BUY,
            requested_quantity=Decimal("0.010000000000"),
            reference_price=Decimal("50000.00000000"),
            status=status,
            authorized_at=authorized_at,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

    def test_order_requires_explicitly_authorized_proposal(self):
        draft = self.proposal()
        with self.assertRaises(ValidationError):
            TradeOrder.objects.create(
                simulation=self.simulation,
                proposal=draft,
                market_snapshot=self.snapshot,
                portfolio=self.simulation.portfolio,
                asset=self.asset,
                side=TradeProposal.Side.BUY,
                order_type=TradeOrder.OrderType.MARKET,
                requested_quantity=draft.requested_quantity,
                idempotency_key="draft-must-not-create-order",
            )

    def test_authorized_proposal_only_prepares_pending_order(self):
        proposal = self.proposal(TradeProposal.Status.AUTHORIZED, timezone.now())
        order = TradeOrder.objects.create(
            simulation=self.simulation,
            proposal=proposal,
            market_snapshot=self.snapshot,
            portfolio=self.simulation.portfolio,
            asset=self.asset,
            side=proposal.side,
            order_type=TradeOrder.OrderType.MARKET,
            requested_quantity=proposal.requested_quantity,
            idempotency_key="authorized-order-structure",
        )
        self.assertEqual(order.state, TradeOrder.State.PENDING_EXECUTION)
        self.assertEqual(order.fills.count(), 0)
        self.assertEqual(self.simulation.portfolio.positions.count(), 0)
