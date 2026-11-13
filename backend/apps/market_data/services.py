from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Asset, MarketCandle, MarketQuote, MarketSnapshot
from .providers import (
    DeterministicFixtureProvider,
    KrakenPublicProvider,
    MarketProviderError,
    SUPPORTED_SYMBOLS,
)


def latest_ready_snapshot(simulation):
    return (
        MarketSnapshot.objects.filter(
            simulation=simulation,
            status=MarketSnapshot.Status.READY,
        )
        .prefetch_related("quotes__asset")
        .first()
    )


def effective_snapshot(snapshot):
    if snapshot and snapshot.status == MarketSnapshot.Status.UNAVAILABLE:
        return snapshot.fallback_snapshot
    return snapshot


def collect_market_snapshot(simulation, *, provider=None, force=False):
    now = timezone.now()
    last_ready = latest_ready_snapshot(simulation)
    if last_ready and last_ready.valid_until > now and not force:
        return last_ready

    if provider is None:
        provider = KrakenPublicProvider() if settings.MARKET_DATA_MODE == "live" else DeterministicFixtureProvider()

    try:
        batch = provider.fetch()
    except MarketProviderError as exc:
        return MarketSnapshot.objects.create(
            simulation=simulation,
            source=MarketSnapshot.Source.KRAKEN,
            status=MarketSnapshot.Status.UNAVAILABLE,
            observed_at=now,
            valid_until=now,
            fallback_snapshot=last_ready,
            error_message=str(exc)[:300],
        )

    assets = Asset.objects.in_bulk(SUPPORTED_SYMBOLS, field_name="symbol")
    missing = set(SUPPORTED_SYMBOLS) - set(assets)
    if missing:
        raise RuntimeError(f"Ativos monitorados não cadastrados: {sorted(missing)}")

    with transaction.atomic():
        snapshot = MarketSnapshot.objects.create(
            simulation=simulation,
            source=batch.source,
            status=MarketSnapshot.Status.READY,
            observed_at=batch.observed_at,
            valid_until=batch.observed_at + timedelta(seconds=settings.MARKET_DATA_TTL_SECONDS),
        )
        MarketQuote.objects.bulk_create(
            [
                MarketQuote(
                    snapshot=snapshot,
                    asset=assets[quote.symbol],
                    price=quote.price,
                    observed_at=quote.observed_at,
                )
                for quote in batch.quotes
            ]
        )
        for candle in batch.candles:
            MarketCandle.objects.update_or_create(
                asset=assets[candle.symbol],
                source=batch.source,
                interval_minutes=1,
                opened_at=candle.opened_at,
                defaults={
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "trade_count": candle.trade_count,
                    "is_closed": batch.source != MarketSnapshot.Source.FIXTURE,
                },
            )
    return snapshot
