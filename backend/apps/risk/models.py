from decimal import Decimal

from django.db import models


class RiskPolicy(models.Model):
    simulation = models.OneToOneField(
        "simulations.Simulation", on_delete=models.CASCADE, related_name="risk_policy"
    )
    max_operation_percent = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("5.0000")
    )
    max_asset_exposure_percent = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("15.0000")
    )
    daily_loss_limit_percent = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("2.0000")
    )
    max_price_deviation_percent = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("1.0000")
    )
    fee_rate_percent = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("0.1000")
    )
    spread_percent = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("0.1000")
    )
    slippage_percent = models.DecimalField(
        max_digits=7, decimal_places=4, default=Decimal("0.0500")
    )
    proposal_ttl_seconds = models.PositiveIntegerField(default=300)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)


class DailyRiskState(models.Model):
    simulation = models.ForeignKey(
        "simulations.Simulation", on_delete=models.CASCADE, related_name="daily_risk_states"
    )
    date = models.DateField()
    reference_equity = models.DecimalField(max_digits=28, decimal_places=8)
    opening_realized_pnl = models.DecimalField(max_digits=28, decimal_places=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("simulation", "date"), name="unique_daily_risk_state"
            )
        ]


class RiskAssessment(models.Model):
    class Stage(models.TextChoices):
        PREVIEW = "PREVIEW", "Proposal preview"
        EXECUTION = "EXECUTION", "Execution revalidation"

    proposal = models.ForeignKey(
        "orders.TradeProposal", on_delete=models.CASCADE, related_name="risk_assessments"
    )
    stage = models.CharField(max_length=12, choices=Stage.choices)
    approved = models.BooleanField()
    codes = models.JSONField(default=list)
    metrics = models.JSONField(default=dict)
    policy_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
