from rest_framework import serializers

from .models import PortfolioSnapshot
from .services import portfolio_valuation


class PortfolioSerializer(serializers.Serializer):
    def to_representation(self, portfolio):
        valuation = portfolio_valuation(portfolio)
        equity = valuation["total_equity"]
        positions = []
        for position, price, market_value, unrealized in valuation["positions"]:
            exposure = (market_value / equity * 100) if market_value is not None and equity else None
            positions.append(
                {
                    "symbol": position.asset.symbol,
                    "quantity": format(position.quantity, ".12f"),
                    "reserved_quantity": format(position.reserved_quantity, ".12f"),
                    "average_cost": format(position.average_cost, ".8f"),
                    "market_price": format(price, ".8f") if price is not None else None,
                    "market_value": format(market_value, ".8f") if market_value is not None else None,
                    "exposure_percent": format(exposure, ".4f") if exposure is not None else None,
                    "realized_pnl": format(position.realized_pnl, ".8f"),
                    "unrealized_pnl": format(unrealized, ".8f") if unrealized is not None else None,
                }
            )
        return {
            "simulation_id": str(portfolio.simulation_id),
            "available_balance": format(portfolio.available_balance, ".8f"),
            "reserved_balance": format(portfolio.reserved_balance, ".8f"),
            "positions_value": format(valuation["positions_value"], ".8f"),
            "total_equity": format(equity, ".8f"),
            "realized_pnl": format(portfolio.realized_pnl, ".8f"),
            "unrealized_pnl": format(valuation["unrealized_pnl"], ".8f"),
            "currency": portfolio.simulation.currency,
            "positions": positions,
            "market_snapshot_id": str(valuation["snapshot"].id) if valuation["snapshot"] else None,
            "demo_notice": "Dados fictícios. Nenhum ativo ou dinheiro real é utilizado.",
            "updated_at": portfolio.updated_at,
        }


class PortfolioSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioSnapshot
        fields = (
            "id",
            "available_balance",
            "reserved_balance",
            "total_equity",
            "realized_pnl",
            "market_snapshot_id",
            "captured_at",
        )
