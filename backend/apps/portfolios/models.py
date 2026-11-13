from decimal import Decimal
from django.db import models


class Portfolio(models.Model):
    simulation = models.OneToOneField("simulations.Simulation", on_delete=models.CASCADE, related_name="portfolio")
    available_balance = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    reserved_balance = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    total_equity = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    realized_pnl = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("0"))
    updated_at = models.DateTimeField(auto_now=True)


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    asset = models.ForeignKey("market_data.Asset", on_delete=models.PROTECT, related_name="positions")
    quantity = models.DecimalField(max_digits=28, decimal_places=12, default=Decimal("0"))
    reserved_quantity = models.DecimalField(max_digits=28, decimal_places=12, default=Decimal("0"))
    average_cost = models.DecimalField(max_digits=28, decimal_places=8, default=Decimal("0"))
    realized_pnl = models.DecimalField(max_digits=28, decimal_places=8, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("portfolio", "asset"), name="unique_portfolio_asset_position"),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="position_quantity_non_negative"),
            models.CheckConstraint(condition=models.Q(reserved_quantity__gte=0), name="position_reserved_quantity_non_negative"),
            models.CheckConstraint(condition=models.Q(quantity__gte=models.F("reserved_quantity")), name="position_reserve_within_quantity"),
            models.CheckConstraint(condition=models.Q(average_cost__gte=0), name="position_average_cost_non_negative"),
        ]

    def cost_basis(self):
        return self.quantity * self.average_cost

    def market_value(self, price):
        return self.quantity * Decimal(price)

    def unrealized_pnl(self, price):
        return self.market_value(price) - self.cost_basis()


class PortfolioSnapshot(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="history")
    market_snapshot = models.ForeignKey(
        "market_data.MarketSnapshot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="portfolio_snapshots",
    )
    available_balance = models.DecimalField(max_digits=20, decimal_places=8)
    reserved_balance = models.DecimalField(max_digits=20, decimal_places=8)
    total_equity = models.DecimalField(max_digits=20, decimal_places=8)
    realized_pnl = models.DecimalField(max_digits=20, decimal_places=8)
    captured_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-captured_at",)

