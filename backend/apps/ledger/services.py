from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.portfolios.models import Portfolio, PortfolioSnapshot
from apps.simulations.models import Simulation
from .models import LedgerAccount, LedgerEntry, LedgerTransaction


@transaction.atomic
def post_transaction(*, simulation, kind, idempotency_key, description, entries, metadata=None, occurred_at=None):
    Simulation.objects.select_for_update().get(pk=simulation.pk)
    existing = LedgerTransaction.objects.filter(
        simulation=simulation, idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing, False

    if len(entries) < 2:
        raise ValidationError("Uma transação contábil exige ao menos dois lançamentos.")

    balances = defaultdict(lambda: Decimal("0"))
    portfolio_id = simulation.portfolio.id
    normalized_entries = []
    for account, amount in entries:
        amount = Decimal(amount)
        if account.portfolio_id != portfolio_id:
            raise ValidationError("Todas as contas devem pertencer à mesma sessão.")
        if amount == 0:
            raise ValidationError("Lançamentos com valor zero não são permitidos.")
        balances[account.asset_code] += amount
        normalized_entries.append((account, amount))
    if any(total != 0 for total in balances.values()):
        raise ValidationError("A transação contábil deve estar balanceada por ativo.")

    ledger_transaction = LedgerTransaction.objects.create(
        simulation=simulation,
        kind=kind,
        idempotency_key=idempotency_key,
        description=description,
        occurred_at=occurred_at or timezone.now(),
        metadata=metadata or {},
    )
    LedgerEntry.objects.bulk_create(
        [
            LedgerEntry(transaction=ledger_transaction, account=account, amount=amount)
            for account, amount in normalized_entries
        ]
    )
    return ledger_transaction, True


@transaction.atomic
def bootstrap_portfolio(portfolio):
    portfolio = Portfolio.objects.select_for_update().select_related("simulation").get(pk=portfolio.pk)
    available, _ = LedgerAccount.objects.get_or_create(
        portfolio=portfolio,
        kind=LedgerAccount.Kind.AVAILABLE,
        asset_code=portfolio.simulation.currency,
    )
    LedgerAccount.objects.get_or_create(
        portfolio=portfolio,
        kind=LedgerAccount.Kind.RESERVED,
        asset_code=portfolio.simulation.currency,
    )
    equity, _ = LedgerAccount.objects.get_or_create(
        portfolio=portfolio,
        kind=LedgerAccount.Kind.EQUITY,
        asset_code=portfolio.simulation.currency,
    )
    ledger_transaction, created = post_transaction(
        simulation=portfolio.simulation,
        kind=LedgerTransaction.Kind.OPENING_BALANCE,
        idempotency_key="opening-balance-v1",
        description="Capital virtual inicial da sessão demo",
        entries=(
            (available, portfolio.simulation.initial_capital),
            (equity, -portfolio.simulation.initial_capital),
        ),
        metadata={"demo": True, "convertible": False},
        occurred_at=portfolio.simulation.created_at,
    )
    if not PortfolioSnapshot.objects.filter(portfolio=portfolio).exists():
        PortfolioSnapshot.objects.create(
            portfolio=portfolio,
            available_balance=portfolio.available_balance,
            reserved_balance=portfolio.reserved_balance,
            total_equity=portfolio.total_equity,
            realized_pnl=portfolio.realized_pnl,
        )
    return ledger_transaction, created
