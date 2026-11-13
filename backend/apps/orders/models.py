import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TradeProposal(models.Model):
    class Origin(models.TextChoices):
        MANUAL = "MANUAL", "Created manually by the player"
        AI_AGENT = "AI_AGENT", "Created by a multi-agent analysis"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending player approval"
        RISK_REJECTED = "RISK_REJECTED", "Rejected by deterministic risk"
        AUTHORIZED = "AUTHORIZED", "Authorized by player"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        INVALIDATED = "INVALIDATED", "Authorization invalidated"
        EXECUTED = "EXECUTED", "Executed virtually"
        FAILED = "FAILED", "Execution failed"

    class Side(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    simulation = models.ForeignKey("simulations.Simulation", on_delete=models.CASCADE, related_name="trade_proposals")
    market_snapshot = models.ForeignKey("market_data.MarketSnapshot", on_delete=models.PROTECT, related_name="trade_proposals")
    asset = models.ForeignKey("market_data.Asset", on_delete=models.PROTECT, related_name="trade_proposals")
    side = models.CharField(max_length=4, choices=Side.choices)
    origin = models.CharField(max_length=16, choices=Origin.choices, default=Origin.MANUAL)
    analysis_run = models.ForeignKey(
        "agents.AnalysisRun", on_delete=models.PROTECT, null=True, blank=True,
        related_name="proposals",
    )
    evidence = models.JSONField(default=dict, blank=True)
    requested_quantity = models.DecimalField(max_digits=28, decimal_places=12)
    requested_amount = models.DecimalField(max_digits=28, decimal_places=8, null=True, blank=True)
    reference_price = models.DecimalField(max_digits=28, decimal_places=8)
    estimated_notional = models.DecimalField(max_digits=28, decimal_places=8, default=0)
    estimated_fee = models.DecimalField(max_digits=28, decimal_places=8, default=0)
    estimated_total = models.DecimalField(max_digits=28, decimal_places=8, default=0)
    justification = models.CharField(max_length=300, default="Proposta manual do jogador")
    risk_summary = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    authorized_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(requested_quantity__gt=0), name="proposal_quantity_positive"),
            models.CheckConstraint(condition=models.Q(reference_price__gt=0), name="proposal_price_positive"),
        ]

    def clean(self):
        if self.origin == self.Origin.AI_AGENT and not self.analysis_run_id:
            raise ValidationError({"analysis_run": "Propostas de agentes exigem a análise de origem."})
        if self.analysis_run_id and self.analysis_run.simulation_id != self.simulation_id:
            raise ValidationError({"analysis_run": "Análise e proposta devem pertencer à mesma sessão."})


class TradeOrder(models.Model):
    class State(models.TextChoices):
        PENDING_EXECUTION = "PENDING_EXECUTION", "Pending simulated execution"
        RESERVED = "RESERVED", "Funds reserved"
        PARTIALLY_FILLED = "PARTIALLY_FILLED", "Partially filled"
        FILLED = "FILLED", "Filled"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    class OrderType(models.TextChoices):
        MARKET = "MARKET", "Market"
        LIMIT = "LIMIT", "Limit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    simulation = models.ForeignKey("simulations.Simulation", on_delete=models.PROTECT, related_name="trade_orders")
    proposal = models.OneToOneField(TradeProposal, on_delete=models.PROTECT, related_name="order")
    market_snapshot = models.ForeignKey(
        "market_data.MarketSnapshot", on_delete=models.PROTECT, related_name="trade_orders",
    )
    portfolio = models.ForeignKey("portfolios.Portfolio", on_delete=models.PROTECT, related_name="orders")
    asset = models.ForeignKey("market_data.Asset", on_delete=models.PROTECT, related_name="orders")
    side = models.CharField(max_length=4, choices=TradeProposal.Side.choices)
    order_type = models.CharField(max_length=8, choices=OrderType.choices)
    state = models.CharField(max_length=24, choices=State.choices, default=State.PENDING_EXECUTION)
    requested_quantity = models.DecimalField(max_digits=28, decimal_places=12)
    limit_price = models.DecimalField(max_digits=28, decimal_places=8, null=True, blank=True)
    reserved_amount = models.DecimalField(max_digits=28, decimal_places=8, default=0)
    total_fee = models.DecimalField(max_digits=28, decimal_places=8, default=0)
    execution_price = models.DecimalField(max_digits=28, decimal_places=8, null=True, blank=True)
    idempotency_key = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("simulation", "idempotency_key"), name="unique_order_idempotency_key"),
            models.CheckConstraint(condition=models.Q(requested_quantity__gt=0), name="order_quantity_positive"),
            models.CheckConstraint(condition=models.Q(reserved_amount__gte=0), name="order_reserve_non_negative"),
            models.CheckConstraint(condition=models.Q(total_fee__gte=0), name="order_fee_non_negative"),
        ]

    def clean(self):
        errors = {}
        if self.proposal_id:
            if self.proposal.status != TradeProposal.Status.AUTHORIZED or not self.proposal.authorized_at:
                errors["proposal"] = "A ordem exige uma proposta explicitamente autorizada."
            if self.simulation_id != self.proposal.simulation_id:
                errors["simulation"] = "Ordem e proposta devem pertencer à mesma simulação."
            if self.asset_id != self.proposal.asset_id or self.side != self.proposal.side:
                errors["asset"] = "Ativo e lado devem corresponder à proposta autorizada."
        if self.portfolio_id and self.simulation_id != self.portfolio.simulation_id:
            errors["portfolio"] = "A carteira deve pertencer à simulação da ordem."
        if self.order_type == self.OrderType.LIMIT and self.limit_price is None:
            errors["limit_price"] = "Ordens limitadas exigem preço limite."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class TradeFill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(TradeOrder, on_delete=models.PROTECT, related_name="fills")
    market_snapshot = models.ForeignKey(
        "market_data.MarketSnapshot", on_delete=models.PROTECT, related_name="fills",
    )
    source = models.CharField(max_length=24)
    execution_key = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=28, decimal_places=12)
    price = models.DecimalField(max_digits=28, decimal_places=8)
    fee = models.DecimalField(max_digits=28, decimal_places=8, default=0)
    filled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("order", "execution_key"), name="unique_fill_execution_key"),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="fill_quantity_positive"),
            models.CheckConstraint(condition=models.Q(price__gt=0), name="fill_price_positive"),
            models.CheckConstraint(condition=models.Q(fee__gte=0), name="fill_fee_non_negative"),
        ]


class ProposalDecision(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(TradeProposal, on_delete=models.PROTECT, related_name="decisions")
    simulation = models.ForeignKey(
        "simulations.Simulation", on_delete=models.PROTECT, related_name="proposal_decisions"
    )
    decision = models.CharField(max_length=8, choices=Decision.choices)
    proposal_version = models.PositiveIntegerField()
    idempotency_key = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("simulation", "idempotency_key"),
                name="unique_proposal_decision_idempotency",
            )
        ]
