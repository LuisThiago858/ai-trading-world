from decimal import Decimal

from apps.market_data.services import effective_snapshot, latest_ready_snapshot


def portfolio_valuation(portfolio):
    market_snapshot = effective_snapshot(latest_ready_snapshot(portfolio.simulation))
    prices = {}
    if market_snapshot:
        prices = {
            quote.asset_id: quote.price
            for quote in market_snapshot.quotes.select_related("asset").all()
        }

    positions = []
    positions_value = Decimal("0")
    unrealized_total = Decimal("0")
    for position in portfolio.positions.select_related("asset").all():
        price = prices.get(position.asset_id)
        market_value = position.market_value(price) if price is not None else None
        unrealized = position.unrealized_pnl(price) if price is not None else None
        if market_value is not None:
            positions_value += market_value
            unrealized_total += unrealized
        positions.append((position, price, market_value, unrealized))

    equity = portfolio.available_balance + portfolio.reserved_balance + positions_value
    return {
        "snapshot": market_snapshot,
        "positions": positions,
        "positions_value": positions_value,
        "unrealized_pnl": unrealized_total,
        "total_equity": equity,
    }
