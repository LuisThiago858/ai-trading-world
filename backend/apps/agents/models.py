import uuid

from django.db import models


class AnalysisRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    simulation = models.ForeignKey(
        "simulations.Simulation", on_delete=models.CASCADE, related_name="analysis_runs"
    )
    market_snapshot = models.ForeignKey(
        "market_data.MarketSnapshot", on_delete=models.PROTECT, related_name="analysis_runs"
    )
    requested_assets = models.JSONField(default=list)
    request_idempotency_key = models.CharField(max_length=100)
    graph_thread_id = models.CharField(max_length=100, unique=True)
    celery_task_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    current_node = models.CharField(max_length=32, blank=True)
    provider = models.CharField(max_length=24)
    provider_mode = models.CharField(max_length=16)
    model_name = models.CharField(max_length=100)
    checkpoint_state = models.JSONField(default=dict, blank=True)
    conclusion = models.JSONField(default=dict, blank=True)
    error = models.JSONField(default=dict, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=14, decimal_places=8, default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    cancel_requested = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("simulation", "request_idempotency_key"),
                name="unique_analysis_request_idempotency",
            )
        ]


class AgentResult(models.Model):
    class Agent(models.TextChoices):
        ALEX = "ALEX", "Alex — Technical Analyst"
        MAYA = "MAYA", "Maya — Portfolio Strategist"
        VICTOR = "VICTOR", "Victor — Risk Manager"

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE, related_name="agent_results")
    agent = models.CharField(max_length=8, choices=Agent.choices)
    role = models.CharField(max_length=80)
    status = models.CharField(max_length=16, choices=Status.choices)
    provider = models.CharField(max_length=24)
    model_name = models.CharField(max_length=100)
    schema_version = models.PositiveSmallIntegerField(default=1)
    indicators = models.JSONField(default=dict, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    hypotheses = models.JSONField(default=list, blank=True)
    conclusion = models.JSONField(default=dict, blank=True)
    disagreements = models.JSONField(default=list, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=14, decimal_places=8, default=0)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("run", "id")
        constraints = [
            models.UniqueConstraint(fields=("run", "agent"), name="unique_agent_result_per_run")
        ]


class AnalysisCheckpoint(models.Model):
    run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE, related_name="checkpoints")
    sequence = models.PositiveSmallIntegerField()
    node = models.CharField(max_length=32)
    state = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sequence",)
        constraints = [
            models.UniqueConstraint(fields=("run", "sequence"), name="unique_analysis_checkpoint")
        ]
