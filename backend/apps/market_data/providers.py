import json
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


SUPPORTED_SYMBOLS = ("BTC/USDT", "ETH/USDT")


class MarketProviderError(RuntimeError):
    pass


class MarketProviderUnavailable(MarketProviderError):
    pass


class MarketProviderRateLimited(MarketProviderError):
    pass


@dataclass(frozen=True)
class QuotePoint:
    symbol: str
    price: Decimal
    observed_at: datetime


@dataclass(frozen=True)
class CandlePoint:
    symbol: str
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: int


@dataclass(frozen=True)
class MarketBatch:
    source: str
    observed_at: datetime
    quotes: tuple[QuotePoint, ...]
    candles: tuple[CandlePoint, ...]


class KrakenPublicProvider:
    """Read-only adapter for Kraken Spot public ticker and OHLC endpoints."""

    base_url = "https://api.kraken.com/0/public"

    def _request(self, endpoint, params):
        throttle_key = f"market-data:kraken:throttle:{endpoint}:{params.get('pair', '')}"
        interval = settings.MARKET_DATA_MIN_REQUEST_INTERVAL_SECONDS
        if not cache.add(throttle_key, True, timeout=interval):
            raise MarketProviderRateLimited("Coleta pública temporariamente limitada pelo cache local.")

        request = Request(
            f"{self.base_url}/{endpoint}?{urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": "AI-Trading-World-Demo/0.2"},
        )
        try:
            with urlopen(request, timeout=settings.MARKET_DATA_HTTP_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429:
                raise MarketProviderRateLimited("O provedor público limitou as requisições.") from exc
            raise MarketProviderUnavailable(f"HTTP {exc.code} do provedor público.") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise MarketProviderUnavailable("Provedor público indisponível ou resposta inválida.") from exc

        errors = payload.get("error") or []
        if errors:
            message = "; ".join(str(error) for error in errors)
            if "limit" in message.lower() or "throttled" in message.lower():
                raise MarketProviderRateLimited("O provedor público limitou as requisições.")
            raise MarketProviderUnavailable(f"Erro retornado pelo provedor público: {message[:180]}")
        return payload.get("result") or {}

    @staticmethod
    def _result_for_symbol(result, symbol):
        normalized = symbol.replace("/", "").replace("BTC", "XBT")
        for key, value in result.items():
            candidate = key.replace("/", "").replace("BTC", "XBT")
            if candidate == normalized:
                return value
        raise MarketProviderUnavailable(f"Par {symbol} ausente na resposta pública.")

    def fetch(self):
        cached = cache.get("market-data:kraken:batch")
        if cached is not None:
            return cached

        observed_at = timezone.now()
        ticker_result = self._request(
            "Ticker", {"pair": ",".join(SUPPORTED_SYMBOLS), "assetVersion": 1}
        )
        quotes = []
        for symbol in SUPPORTED_SYMBOLS:
            ticker = self._result_for_symbol(ticker_result, symbol)
            try:
                price = Decimal(str(ticker["c"][0]))
            except (KeyError, IndexError, InvalidOperation, TypeError) as exc:
                raise MarketProviderUnavailable(f"Ticker inválido para {symbol}.") from exc
            quotes.append(QuotePoint(symbol=symbol, price=price, observed_at=observed_at))

        candles = []
        for symbol in SUPPORTED_SYMBOLS:
            result = self._request(
                "OHLC", {"pair": symbol, "interval": 1, "assetVersion": 1}
            )
            rows = self._result_for_symbol(
                {key: value for key, value in result.items() if key != "last"}, symbol
            )
            # Kraken documents the last row as the still-open candle; it is not persisted.
            for row in rows[:-1][-60:]:
                try:
                    candles.append(
                        CandlePoint(
                            symbol=symbol,
                            opened_at=datetime.fromtimestamp(int(row[0]), tz=dt_timezone.utc),
                            open=Decimal(str(row[1])),
                            high=Decimal(str(row[2])),
                            low=Decimal(str(row[3])),
                            close=Decimal(str(row[4])),
                            volume=Decimal(str(row[6])),
                            trade_count=int(row[7]),
                        )
                    )
                except (IndexError, InvalidOperation, TypeError, ValueError) as exc:
                    raise MarketProviderUnavailable(f"Candle inválido para {symbol}.") from exc

        batch = MarketBatch(
            source="KRAKEN",
            observed_at=observed_at,
            quotes=tuple(quotes),
            candles=tuple(candles),
        )
        cache.set("market-data:kraken:batch", batch, timeout=30)
        return batch


class DeterministicFixtureProvider:
    prices = {"BTC/USDT": Decimal("50000.00000000"), "ETH/USDT": Decimal("3000.00000000")}

    def fetch(self):
        observed_at = timezone.now()
        minute = observed_at.replace(second=0, microsecond=0)
        quotes = tuple(
            QuotePoint(symbol=symbol, price=price, observed_at=observed_at)
            for symbol, price in self.prices.items()
        )
        candles = []
        for symbol, price in self.prices.items():
            candles.append(
                CandlePoint(
                    symbol=symbol,
                    opened_at=minute,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=Decimal("0"),
                    trade_count=0,
                )
            )
        return MarketBatch(
            source="DEMO_FIXTURE",
            observed_at=observed_at,
            quotes=quotes,
            candles=tuple(candles),
        )
