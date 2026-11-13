from decimal import Decimal, localcontext


def _values(values):
    return tuple(Decimal(value) for value in values)


def sma(values, period):
    values = _values(values)
    if period <= 0 or len(values) < period:
        return None
    return sum(values[-period:], Decimal("0")) / Decimal(period)


def ema(values, period):
    values = _values(values)
    if period <= 0 or len(values) < period:
        return None
    multiplier = Decimal("2") / Decimal(period + 1)
    current = sum(values[:period], Decimal("0")) / Decimal(period)
    for value in values[period:]:
        current = (value - current) * multiplier + current
    return current


def rsi(values, period=14):
    values = _values(values)
    if len(values) <= period:
        return None
    changes = [right - left for left, right in zip(values, values[1:])]
    window = changes[-period:]
    gains = sum((max(change, Decimal("0")) for change in window), Decimal("0")) / period
    losses = sum((max(-change, Decimal("0")) for change in window), Decimal("0")) / period
    if losses == 0:
        return Decimal("100") if gains > 0 else Decimal("50")
    relative_strength = gains / losses
    return Decimal("100") - Decimal("100") / (Decimal("1") + relative_strength)


def macd(values, fast=12, slow=26, signal=9):
    values = _values(values)
    if len(values) < slow + signal - 1:
        return None
    fast_series, slow_series = [], []
    for end in range(slow, len(values) + 1):
        window = values[:end]
        fast_series.append(ema(window, fast))
        slow_series.append(ema(window, slow))
    line_series = [fast_value - slow_value for fast_value, slow_value in zip(fast_series, slow_series)]
    signal_value = ema(line_series, signal)
    if signal_value is None:
        return None
    return {"line": line_series[-1], "signal": signal_value, "histogram": line_series[-1] - signal_value}


def volatility(values, period=20):
    values = _values(values)
    if len(values) <= period:
        return None
    returns = [
        (right - left) / left
        for left, right in zip(values[-period - 1 :], values[-period:])
        if left != 0
    ]
    if len(returns) < period:
        return None
    mean = sum(returns, Decimal("0")) / Decimal(len(returns))
    variance = sum(((value - mean) ** 2 for value in returns), Decimal("0")) / Decimal(len(returns))
    with localcontext() as context:
        context.prec = 28
        return variance.sqrt()


def calculate_indicators(candles):
    ordered = tuple(candles)
    closes = [candle.close for candle in ordered]
    volumes = [candle.volume for candle in ordered]
    change = None
    if len(closes) >= 2 and closes[0] != 0:
        change = (closes[-1] - closes[0]) / closes[0] * Decimal("100")
    macd_values = macd(closes)

    def text(value):
        return str(value) if value is not None else None

    return {
        "candle_count": len(closes),
        "last_close": text(closes[-1] if closes else None),
        "change_percent": text(change),
        "sma_5": text(sma(closes, 5)),
        "sma_20": text(sma(closes, 20)),
        "ema_12": text(ema(closes, 12)),
        "ema_26": text(ema(closes, 26)),
        "rsi_14": text(rsi(closes, 14)),
        "volatility_20": text(volatility(closes, 20)),
        "volume_total": text(sum(volumes, Decimal("0"))),
        "macd": {key: text(value) for key, value in macd_values.items()} if macd_values else None,
        "history_sufficient": len(closes) >= 20,
    }
