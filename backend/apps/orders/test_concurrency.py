import threading
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.simulations.models import Simulation
from .models import TradeOrder
from .services import approve_proposal, create_manual_proposal


@skipUnless(connection.vendor == "postgresql", "Locks concorrentes exigem PostgreSQL real.")
class PostgreSQLApprovalConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_approvals_create_one_order_and_one_fill(self):
        created = APIClient().post("/api/simulations/", {}, format="json").data
        simulation = Simulation.objects.get(pk=created["id"])
        proposal = create_manual_proposal(
            simulation=simulation,
            symbol="BTC/USDT",
            side="BUY",
            requested_amount="500.00000000",
        )
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def approve(key):
            close_old_connections()
            try:
                local_simulation = Simulation.objects.get(pk=simulation.pk)
                barrier.wait(timeout=5)
                result = approve_proposal(
                    simulation=local_simulation,
                    proposal_id=proposal.id,
                    expected_version=proposal.version,
                    idempotency_key=key,
                )
                results.append(result)
            except Exception as exc:  # captured for an assertion in the parent test thread
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [
            threading.Thread(target=approve, args=("concurrent-a",)),
            threading.Thread(target=approve, args=("concurrent-b",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(errors, errors)
        self.assertEqual(len(results), 2)
        self.assertEqual(TradeOrder.objects.filter(simulation=simulation).count(), 1)
        self.assertEqual(TradeOrder.objects.get(simulation=simulation).fills.count(), 1)
