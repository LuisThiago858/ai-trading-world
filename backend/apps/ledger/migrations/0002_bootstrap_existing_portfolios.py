from decimal import Decimal

from django.db import migrations


def bootstrap_existing_portfolios(apps, schema_editor):
    LedgerAccount = apps.get_model("ledger", "LedgerAccount")
    LedgerEntry = apps.get_model("ledger", "LedgerEntry")
    LedgerTransaction = apps.get_model("ledger", "LedgerTransaction")
    Portfolio = apps.get_model("portfolios", "Portfolio")
    PortfolioSnapshot = apps.get_model("portfolios", "PortfolioSnapshot")

    for portfolio in Portfolio.objects.select_related("simulation").all():
        available, _ = LedgerAccount.objects.get_or_create(
            portfolio=portfolio,
            kind="AVAILABLE",
            asset_code=portfolio.simulation.currency,
        )
        LedgerAccount.objects.get_or_create(
            portfolio=portfolio,
            kind="RESERVED",
            asset_code=portfolio.simulation.currency,
        )
        equity, _ = LedgerAccount.objects.get_or_create(
            portfolio=portfolio,
            kind="EQUITY",
            asset_code=portfolio.simulation.currency,
        )
        ledger_transaction, created = LedgerTransaction.objects.get_or_create(
            simulation=portfolio.simulation,
            idempotency_key="opening-balance-v1",
            defaults={
                "kind": "OPENING_BALANCE",
                "description": "Capital virtual inicial da sessão demo",
                "occurred_at": portfolio.simulation.created_at,
                "metadata": {"demo": True, "convertible": False, "migrated": True},
            },
        )
        if created:
            amount = Decimal(portfolio.simulation.initial_capital)
            LedgerEntry.objects.bulk_create(
                [
                    LedgerEntry(transaction=ledger_transaction, account=available, amount=amount),
                    LedgerEntry(transaction=ledger_transaction, account=equity, amount=-amount),
                ]
            )
        PortfolioSnapshot.objects.get_or_create(
            portfolio=portfolio,
            defaults={
                "available_balance": portfolio.available_balance,
                "reserved_balance": portfolio.reserved_balance,
                "total_equity": portfolio.total_equity,
                "realized_pnl": portfolio.realized_pnl,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("ledger", "0001_initial"),
        ("portfolios", "0002_portfolio_realized_pnl_portfolio_reserved_balance_and_more"),
    ]
    operations = [migrations.RunPython(bootstrap_existing_portfolios, migrations.RunPython.noop)]
