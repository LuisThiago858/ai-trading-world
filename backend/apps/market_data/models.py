import uuid

from django.db import models


class Asset(models.Model):
    symbol = models.CharField(max_length=16, unique=True)
    base_currency = models.CharField(max_length=12)
    quote_currency = models.CharField(max_length=12, default="USDT")
    provider_symbol = models.CharField(max_length=32)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("symbol",)

    def __str__(self):
        return self.symbol


class MarketSnapshot(models.Model):
    class Status(models.TextChoices):
        READY = "READY", "Ready"
        UNAVAILABLE = "UNAVAILABLE", "Unavailable"

    class Source(models.TextChoices):
        KRAKEN = "KRAKEN", "Kraken public market data"
        FIXTURE = "DEMO_FIXTURE", "Deterministic demo fixture"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    simulation = models.ForeignKey(
        "simulations.Simulation", on_delete=models.CASCADE, related_name="market_snapshots"
    )
    source = models.CharField(max_length=24, choices=Source.choices)
    status = models.CharField(max_length=16, choices=Status.choices)
    observed_at = models.DateTimeField()
    valid_until = models.DateTimeField()
    collected_at = models.DateTimeField(auto_now_add=True)
    fallback_snapshot = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="fallback_attempts"
    )
    error_message = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("-collected_at",)
        indexes = [models.Index(fields=("simulation", "status", "-collected_at"))]


class MarketQuote(models.Model):
    snapshot = models.ForeignKey(MarketSnapshot, on_delete=models.CASCADE, related_name="quotes")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="quotes")
    price = models.DecimalField(max_digits=28, decimal_places=8)
    observed_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("snapshot", "asset"), name="unique_snapshot_asset_quote"),
            models.CheckConstraint(condition=models.Q(price__gt=0), name="market_quote_price_positive"),
        ]


class MarketCandle(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="candles")
    source = models.CharField(max_length=24, choices=MarketSnapshot.Source.choices)
    interval_minutes = models.PositiveSmallIntegerField(default=1)
    opened_at = models.DateTimeField()
    open = models.DecimalField(max_digits=28, decimal_places=8)
    high = models.DecimalField(max_digits=28, decimal_places=8)
    low = models.DecimalField(max_digits=28, decimal_places=8)
    close = models.DecimalField(max_digits=28, decimal_places=8)
    volume = models.DecimalField(max_digits=28, decimal_places=12)
    trade_count = models.PositiveIntegerField(default=0)
    is_closed = models.BooleanField(default=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("asset", "-opened_at")
        constraints = [
            models.UniqueConstraint(
                fields=("asset", "source", "interval_minutes", "opened_at"),
                name="unique_market_candle",
            ),
            models.CheckConstraint(condition=models.Q(volume__gte=0), name="market_candle_volume_non_negative"),
        ]
