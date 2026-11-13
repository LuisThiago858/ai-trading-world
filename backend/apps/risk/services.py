from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.market_data.services import latest_ready_snapshot
from apps.orders.models import TradeProposal
from apps.orders.pricing import estimate_market_order
from apps.portfolios.services import portfolio_valuation
from .models import DailyRiskState, RiskAssessment, RiskPolicy


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    codes: tuple[str, ...]
    metrics: dict
    policy_version: int

    def as_dict(self):
        return {
            "approved": self.approved,
            "codes": list(self.codes),
            "metrics": self.metrics,
            "policy_version": self.policy_version,
        }


def get_policy(simulation):
    policy, _ = RiskPolicy.objects.get_or_create(simulation=simulation)
    return policy


def _daily_state(simulation, portfolio, now):
    state, _ = DailyRiskState.objects.get_or_create(
        simulation=simulation,
        date=now.date(),
        defaults={
            "reference_equity": portfolio.total_equity,
            "opening_realized_pnl": portfolio.realized_pnl,
        },
    )
    return state


def evaluate_proposal(proposal, *, stage=RiskAssessment.Stage.PREVIEW, persist=True):
    now = timezone.now()
    policy = get_policy(proposal.simulation)
    portfolio = proposal.simulation.portfolio
    snapshot = latest_ready_snapshot(proposal.simulation)
    codes = []

    if proposal.requested_quantity <= 0:
        codes.append("INVALID_QUANTITY")
    if proposal.expires_at <= now:
        codes.append("PROPOSAL_EXPIRED")
    if stage == RiskAssessment.Stage.EXECUTION and proposal.status not in {
        TradeProposal.Status.PENDING_APPROVAL,
        TradeProposal.Status.AUTHORIZED,
    }:
        codes.append("INVALID_PROPOSAL_STATUS")
    if snapshot is None or snapshot.valid_until <= now:
        codes.append("STALE_MARKET_QUOTE")

    quote = None
    if snapshot:
        quote = snapshot.quotes.filter(asset=proposal.asset).first()
    if quote is None:
        codes.append("MISSING_MARKET_QUOTE")

    valuation = portfolio_valuation(portfolio)
    equity = valuation["total_equity"]
    quote_price = quote.price if quote else proposal.reference_price
    estimate = estimate_market_order(
        side=proposal.side,
        quote_price=quote_price,
        policy=policy,
        requested_amount=proposal.requested_amount,
        requested_quantity=proposal.requested_quantity,
    )
    operation_notional = estimate.gross
    operation_limit = equity * policy.max_operation_percent / Decimal("100")
    asset_limit = equity * policy.max_asset_exposure_percent / Decimal("100")
    existing_position = portfolio.positions.filter(asset=proposal.asset).first()
    existing_quantity = existing_position.quantity if existing_position else Decimal("0")
    reserved_quantity = existing_position.reserved_quantity if existing_position else Decimal("0")
    existing_exposure = existing_quantity * quote_price
    pending_exposure = sum(
        (
            item.estimated_notional
            for item in proposal.simulation.trade_proposals.filter(
                asset=proposal.asset,
                side=TradeProposal.Side.BUY,
                status__in=(TradeProposal.Status.PENDING_APPROVAL, TradeProposal.Status.AUTHORIZED),
            ).exclude(pk=proposal.pk)
        ),
        Decimal("0"),
    )
    projected_exposure = (
        existing_exposure + pending_exposure + operation_notional
        if proposal.side == TradeProposal.Side.BUY
        else max(Decimal("0"), existing_exposure - operation_notional)
    )

    daily_state = _daily_state(proposal.simulation, portfolio, now)
    daily_loss = max(
        Decimal("0"), daily_state.opening_realized_pnl - portfolio.realized_pnl
    )
    daily_loss_limit = daily_state.reference_equity * policy.daily_loss_limit_percent / Decimal("100")

    if proposal.side == TradeProposal.Side.BUY:
        if operation_notional > operation_limit:
            codes.append("MAX_OPERATION_EXPOSURE")
        if projected_exposure > asset_limit:
            codes.append("MAX_ASSET_EXPOSURE")
        if estimate.total > portfolio.available_balance:
            codes.append("INSUFFICIENT_AVAILABLE_BALANCE")
        if daily_loss >= daily_loss_limit:
            codes.append("DAILY_LOSS_LIMIT")
    else:
        available_quantity = existing_quantity - reserved_quantity
        if proposal.requested_quantity > available_quantity:
            codes.append("INSUFFICIENT_ASSET_QUANTITY")

    price_deviation = (
        abs(quote_price - proposal.reference_price) / proposal.reference_price * Decimal("100")
        if proposal.reference_price > 0
        else Decimal("100")
    )
    if stage == RiskAssessment.Stage.EXECUTION and price_deviation > policy.max_price_deviation_percent:
        codes.append("PRICE_CHANGED_REAPPROVAL_REQUIRED")

    metrics = {
        "equity": str(equity),
        "operation_notional": str(operation_notional),
        "operation_limit": str(operation_limit),
        "existing_asset_exposure": str(existing_exposure),
        "pending_asset_exposure": str(pending_exposure),
        "projected_asset_exposure": str(projected_exposure),
        "asset_exposure_limit": str(asset_limit),
        "daily_loss": str(daily_loss),
        "daily_loss_limit": str(daily_loss_limit),
        "available_balance": str(portfolio.available_balance),
        "available_asset_quantity": str(existing_quantity - reserved_quantity),
        "quote_price": str(quote_price),
        "price_deviation_percent": str(price_deviation),
        "estimated_fee": str(estimate.fee),
        "estimated_total": str(estimate.total),
    }
    decision = RiskDecision(not codes, tuple(dict.fromkeys(codes)), metrics, policy.version)
    if persist:
        RiskAssessment.objects.create(
            proposal=proposal,
            stage=stage,
            approved=decision.approved,
            codes=list(decision.codes),
            metrics=metrics,
            policy_version=policy.version,
        )
    return decision
