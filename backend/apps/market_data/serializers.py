from django.utils import timezone
from rest_framework import serializers

from .models import MarketSnapshot
from .services import effective_snapshot


class MarketOverviewSerializer(serializers.Serializer):
    def to_representation(self, snapshot):
        effective = effective_snapshot(snapshot)
        quotes = []
        if effective:
            quotes = [
                {
                    "symbol": quote.asset.symbol,
                    "price": format(quote.price, ".8f"),
                    "observed_at": quote.observed_at.isoformat().replace("+00:00", "Z"),
                }
                for quote in effective.quotes.select_related("asset").order_by("asset__symbol")
            ]
        stale = not effective or effective.valid_until <= timezone.now()
        return {
            "snapshot_id": str(effective.id) if effective else None,
            "source": effective.source if effective else snapshot.source,
            "status": snapshot.status,
            "observed_at": effective.observed_at if effective else snapshot.observed_at,
            "valid_until": effective.valid_until if effective else snapshot.valid_until,
            "stale": stale,
            "using_fallback": snapshot.status == MarketSnapshot.Status.UNAVAILABLE and effective is not None,
            "error": snapshot.error_message or None,
            "quotes": quotes,
            "demo_notice": "Cotações fixas e fictícias para desenvolvimento offline."
            if effective and effective.source == MarketSnapshot.Source.FIXTURE
            else None,
        }
