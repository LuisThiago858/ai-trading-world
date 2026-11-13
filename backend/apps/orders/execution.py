from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.ledger.models import LedgerAccount, LedgerTransaction
from apps.ledger.services import post_transaction
from apps.portfolios.models import Portfolio, PortfolioSnapshot, Position
from apps.portfolios.services import portfolio_valuation
from .models import TradeFill, TradeOrder, TradeProposal
from .pricing import estimate_market_order, money


def _account(portfolio, kind, asset_code):
    account, _ = LedgerAccount.objects.get_or_create(
        portfolio=portfolio, kind=kind, asset_code=asset_code
    )
    return account


@transaction.atomic
def execute_authorized_proposal(proposal, *, idempotency_key, failure_hook=None):
    proposal = TradeProposal.objects.select_for_update(of=("self",)).select_related(
        "simulation", "asset", "market_snapshot", "simulation__portfolio", "simulation__risk_policy"
    ).get(pk=proposal.pk)
    if proposal.status != TradeProposal.Status.AUTHORIZED:
        raise ValueError("A proposta precisa estar autorizada antes da execução.")
    if hasattr(proposal, "order"):
        return proposal.order

    portfolio = Portfolio.objects.select_for_update().get(simulation=proposal.simulation)
    latest_snapshot = proposal.simulation.market_snapshots.filter(status="READY").first()
    quote = latest_snapshot.quotes.select_related("asset").get(asset=proposal.asset)
    policy = proposal.simulation.risk_policy
    estimate = estimate_market_order(
        side=proposal.side,
        quote_price=quote.price,
        policy=policy,
        requested_amount=proposal.requested_amount,
        requested_quantity=proposal.requested_quantity,
    )
    now = timezone.now()
    order = TradeOrder.objects.create(
        simulation=proposal.simulation,
        proposal=proposal,
        portfolio=portfolio,
        asset=proposal.asset,
        market_snapshot=latest_snapshot,
        side=proposal.side,
        order_type=TradeOrder.OrderType.MARKET,
        state=TradeOrder.State.PENDING_EXECUTION,
        requested_quantity=estimate.quantity,
        reserved_amount=estimate.total if proposal.side == TradeProposal.Side.BUY else Decimal("0"),
        total_fee=estimate.fee,
        execution_price=estimate.execution_price,
        idempotency_key=idempotency_key,
    )

    quote_code = proposal.asset.quote_currency
    base_code = proposal.asset.base_currency
    cash_available = _account(portfolio, LedgerAccount.Kind.AVAILABLE, quote_code)
    cash_reserved = _account(portfolio, LedgerAccount.Kind.RESERVED, quote_code)
    asset_available = _account(portfolio, LedgerAccount.Kind.ASSET, base_code)
    asset_reserved = _account(portfolio, LedgerAccount.Kind.ASSET_RESERVED, base_code)
    quote_clearing = _account(portfolio, LedgerAccount.Kind.CLEARING, quote_code)
    asset_clearing = _account(portfolio, LedgerAccount.Kind.CLEARING, base_code)
    fee_account = _account(portfolio, LedgerAccount.Kind.FEE, quote_code)

    position, _ = Position.objects.select_for_update().get_or_create(
        portfolio=portfolio,
        asset=proposal.asset,
        defaults={"quantity": Decimal("0"), "reserved_quantity": Decimal("0")},
    )

    if proposal.side == TradeProposal.Side.BUY:
        portfolio.available_balance -= estimate.total
        portfolio.reserved_balance += estimate.total
        portfolio.save(update_fields=("available_balance", "reserved_balance", "updated_at"))
        post_transaction(
            simulation=proposal.simulation,
            kind=LedgerTransaction.Kind.RESERVATION,
            idempotency_key=f"order:{order.id}:reserve",
            description=f"Reserva virtual para compra de {proposal.asset.symbol}",
            entries=((cash_available, -estimate.total), (cash_reserved, estimate.total)),
        )
        if failure_hook:
            failure_hook("after_reservation")

        previous_cost = position.quantity * position.average_cost
        position.quantity += estimate.quantity
        position.average_cost = money(
            (previous_cost + estimate.gross + estimate.fee) / position.quantity
        )
        position.save()
        portfolio.reserved_balance -= estimate.total
        portfolio.save(update_fields=("reserved_balance", "updated_at"))
        post_transaction(
            simulation=proposal.simulation,
            kind=LedgerTransaction.Kind.FILL,
            idempotency_key=f"order:{order.id}:fill",
            description=f"Liquidação virtual da compra de {proposal.asset.symbol}",
            entries=(
                (cash_reserved, -estimate.gross),
                (quote_clearing, estimate.gross),
                (asset_available, estimate.quantity),
                (asset_clearing, -estimate.quantity),
            ),
        )
        post_transaction(
            simulation=proposal.simulation,
            kind=LedgerTransaction.Kind.FEE,
            idempotency_key=f"order:{order.id}:fee",
            description="Taxa virtual da compra simulada",
            entries=((cash_reserved, -estimate.fee), (fee_account, estimate.fee)),
        )
    else:
        position.reserved_quantity += estimate.quantity
        position.save(update_fields=("reserved_quantity", "updated_at"))
        post_transaction(
            simulation=proposal.simulation,
            kind=LedgerTransaction.Kind.RESERVATION,
            idempotency_key=f"order:{order.id}:reserve",
            description=f"Reserva virtual para venda de {proposal.asset.symbol}",
            entries=((asset_available, -estimate.quantity), (asset_reserved, estimate.quantity)),
        )
        if failure_hook:
            failure_hook("after_reservation")

        cost_released = estimate.quantity * position.average_cost
        position.quantity -= estimate.quantity
        position.reserved_quantity -= estimate.quantity
        realized = estimate.total - cost_released
        position.realized_pnl += realized
        if position.quantity == 0:
            position.average_cost = Decimal("0")
        position.save()
        portfolio.available_balance += estimate.total
        portfolio.realized_pnl += realized
        portfolio.save(update_fields=("available_balance", "realized_pnl", "updated_at"))
        post_transaction(
            simulation=proposal.simulation,
            kind=LedgerTransaction.Kind.FILL,
            idempotency_key=f"order:{order.id}:fill",
            description=f"Liquidação virtual da venda de {proposal.asset.symbol}",
            entries=(
                (asset_reserved, -estimate.quantity),
                (asset_clearing, estimate.quantity),
                (quote_clearing, -estimate.gross),
                (cash_available, estimate.gross),
            ),
        )
        post_transaction(
            simulation=proposal.simulation,
            kind=LedgerTransaction.Kind.FEE,
            idempotency_key=f"order:{order.id}:fee",
            description="Taxa virtual da venda simulada",
            entries=((cash_available, -estimate.fee), (fee_account, estimate.fee)),
        )

    TradeFill.objects.create(
        order=order,
        market_snapshot=latest_snapshot,
        source=latest_snapshot.source,
        execution_key=f"order:{order.id}:full-fill-v1",
        quantity=estimate.quantity,
        price=estimate.execution_price,
        fee=estimate.fee,
        filled_at=now,
    )
    valuation = portfolio_valuation(portfolio)
    portfolio.total_equity = money(valuation["total_equity"])
    portfolio.save(update_fields=("total_equity", "updated_at"))
    PortfolioSnapshot.objects.create(
        portfolio=portfolio,
        market_snapshot=latest_snapshot,
        available_balance=portfolio.available_balance,
        reserved_balance=portfolio.reserved_balance,
        total_equity=portfolio.total_equity,
        realized_pnl=portfolio.realized_pnl,
    )
    order.state = TradeOrder.State.FILLED
    order.executed_at = now
    order.save(update_fields=("state", "executed_at"))
    proposal.status = TradeProposal.Status.EXECUTED
    proposal.save(update_fields=("status",))
    return order
