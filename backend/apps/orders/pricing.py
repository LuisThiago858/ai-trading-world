from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, ROUND_UP


PRICE_QUANTUM = Decimal("0.00000001")
QUANTITY_QUANTUM = Decimal("0.000000000001")
MONEY_QUANTUM = Decimal("0.00000001")
HUNDRED = Decimal("100")


def money(value, rounding=ROUND_HALF_UP):
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=rounding)


def quantity(value):
    return Decimal(value).quantize(QUANTITY_QUANTUM, rounding=ROUND_DOWN)


def price(value):
    return Decimal(value).quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ExecutionEstimate:
    execution_price: Decimal
    quantity: Decimal
    gross: Decimal
    fee: Decimal
    total: Decimal


def estimate_market_order(*, side, quote_price, policy, requested_amount=None, requested_quantity=None):
    spread_half = policy.spread_percent / HUNDRED / Decimal("2")
    slippage = policy.slippage_percent / HUNDRED
    direction = Decimal("1") if side == "BUY" else Decimal("-1")
    execution_price = price(quote_price * (Decimal("1") + direction * (spread_half + slippage)))

    if side == "BUY":
        if requested_amount is None:
            raise ValueError("Compras exigem valor em USDT.")
        requested_amount = money(requested_amount, ROUND_DOWN)
        order_quantity = quantity(requested_amount / execution_price)
    else:
        if requested_quantity is None:
            raise ValueError("Vendas exigem quantidade do ativo.")
        order_quantity = quantity(requested_quantity)

    if order_quantity <= 0:
        raise ValueError("Quantidade resultante deve ser positiva.")
    gross = money(order_quantity * execution_price, ROUND_HALF_UP)
    fee = money(gross * policy.fee_rate_percent / HUNDRED, ROUND_UP)
    total = money(gross + fee if side == "BUY" else gross - fee, ROUND_HALF_UP)
    return ExecutionEstimate(execution_price, order_quantity, gross, fee, total)
