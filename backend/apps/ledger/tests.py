from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.simulations.models import Simulation
from .models import LedgerAccount, LedgerTransaction
from .services import bootstrap_portfolio, post_transaction


class LedgerTests(TestCase):
    def setUp(self):
        response = APIClient().post("/api/simulations/", {}, format="json")
        self.simulation = Simulation.objects.get(id=response.data["id"])

    def test_opening_transaction_is_balanced_precise_and_idempotent(self):
        ledger_transaction = self.simulation.ledger_transactions.get()
        entries = list(ledger_transaction.entries.all())
        self.assertEqual(sum((entry.amount for entry in entries), Decimal("0")), Decimal("0"))
        self.assertEqual(
            max(entry.amount for entry in entries), Decimal("10000.000000000000")
        )

        repeated, created = bootstrap_portfolio(self.simulation.portfolio)
        self.assertFalse(created)
        self.assertEqual(repeated.id, ledger_transaction.id)
        self.assertEqual(self.simulation.ledger_transactions.count(), 1)

    def test_ledger_records_are_immutable(self):
        ledger_transaction = self.simulation.ledger_transactions.get()
        ledger_transaction.description = "tentativa de alteração"
        with self.assertRaises(ValidationError):
            ledger_transaction.save()
        with self.assertRaises(ValidationError):
            ledger_transaction.entries.first().delete()
        with self.assertRaises(ValidationError):
            LedgerTransaction.objects.filter(pk=ledger_transaction.pk).update(description="bypass")

    def test_transaction_rejects_unbalanced_and_cross_session_entries(self):
        second_response = APIClient().post("/api/simulations/", {}, format="json")
        second = Simulation.objects.get(id=second_response.data["id"])
        own_account = self.simulation.portfolio.ledger_accounts.get(kind=LedgerAccount.Kind.AVAILABLE)
        other_account = second.portfolio.ledger_accounts.get(kind=LedgerAccount.Kind.EQUITY)

        with self.assertRaises(ValidationError):
            post_transaction(
                simulation=self.simulation,
                kind=LedgerTransaction.Kind.RESERVATION,
                idempotency_key="invalid-cross-session",
                description="Deve falhar",
                entries=((own_account, Decimal("-1")), (other_account, Decimal("1"))),
            )
