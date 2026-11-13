import uuid

from django.core.exceptions import ValidationError
from django.db import models


class LedgerAccount(models.Model):
    class Kind(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available balance"
        RESERVED = "RESERVED", "Reserved balance"
        ASSET = "ASSET", "Asset holding"
        ASSET_RESERVED = "ASSET_RESERVED", "Reserved asset holding"
        CLEARING = "CLEARING", "Virtual execution clearing"
        FEE = "FEE", "Virtual fee expense"
        EQUITY = "EQUITY", "Virtual opening equity"

    portfolio = models.ForeignKey("portfolios.Portfolio", on_delete=models.CASCADE, related_name="ledger_accounts")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    asset_code = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("portfolio", "kind", "asset_code"), name="unique_ledger_account")
        ]


class ImmutableLedgerModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Registros contábeis são imutáveis.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Registros contábeis são imutáveis.")


class ImmutableLedgerQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Registros contábeis são imutáveis.")

    def delete(self):
        raise ValidationError("Registros contábeis são imutáveis.")


class LedgerTransaction(ImmutableLedgerModel):
    class Kind(models.TextChoices):
        OPENING_BALANCE = "OPENING_BALANCE", "Opening virtual balance"
        RESERVATION = "RESERVATION", "Funds reservation"
        RELEASE = "RELEASE", "Funds release"
        FILL = "FILL", "Simulated fill"
        FEE = "FEE", "Simulated fee"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    simulation = models.ForeignKey("simulations.Simulation", on_delete=models.PROTECT, related_name="ledger_transactions")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    idempotency_key = models.CharField(max_length=100)
    description = models.CharField(max_length=240)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    objects = ImmutableLedgerQuerySet.as_manager()

    class Meta:
        ordering = ("-occurred_at", "-created_at")
        constraints = [
            models.UniqueConstraint(fields=("simulation", "idempotency_key"), name="unique_ledger_idempotency_key")
        ]


class LedgerEntry(ImmutableLedgerModel):
    transaction = models.ForeignKey(LedgerTransaction, on_delete=models.PROTECT, related_name="entries")
    account = models.ForeignKey(LedgerAccount, on_delete=models.PROTECT, related_name="entries")
    amount = models.DecimalField(max_digits=28, decimal_places=12)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = ImmutableLedgerQuerySet.as_manager()

    class Meta:
        ordering = ("created_at", "id")
        constraints = [models.CheckConstraint(condition=~models.Q(amount=0), name="ledger_entry_amount_non_zero")]
