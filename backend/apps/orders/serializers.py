from decimal import Decimal

from rest_framework import serializers

from .models import TradeFill, TradeOrder, TradeProposal


class ProposalCreateSerializer(serializers.Serializer):
    asset = serializers.ChoiceField(choices=("BTC/USDT", "ETH/USDT"))
    side = serializers.ChoiceField(choices=TradeProposal.Side.choices)
    amount = serializers.DecimalField(
        max_digits=28, decimal_places=8, required=False, min_value=Decimal("0")
    )
    quantity = serializers.DecimalField(
        max_digits=28, decimal_places=12, required=False, min_value=Decimal("0")
    )
    justification = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["side"] == TradeProposal.Side.BUY:
            if attrs.get("amount") is None or attrs["amount"] <= 0:
                raise serializers.ValidationError({"amount": "Compras exigem valor positivo em USDT."})
            if attrs.get("quantity") is not None:
                raise serializers.ValidationError({"quantity": "Informe valor, não quantidade, para compras."})
        else:
            if attrs.get("quantity") is None or attrs["quantity"] <= 0:
                raise serializers.ValidationError({"quantity": "Vendas exigem quantidade positiva."})
            if attrs.get("amount") is not None:
                raise serializers.ValidationError({"amount": "Informe quantidade, não valor, para vendas."})
        return attrs


class ProposalDecisionInputSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)


class TradeProposalSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source="asset.symbol", read_only=True)
    snapshot_id = serializers.UUIDField(source="market_snapshot_id", read_only=True)

    class Meta:
        model = TradeProposal
        fields = (
            "id", "asset", "side", "origin", "analysis_run_id", "evidence",
            "requested_quantity", "requested_amount",
            "reference_price", "estimated_notional", "estimated_fee", "estimated_total",
            "justification", "risk_summary", "version", "status", "snapshot_id",
            "authorized_at", "expires_at", "created_at",
        )


class TradeFillSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source="order.asset.symbol", read_only=True)
    side = serializers.CharField(source="order.side", read_only=True)

    class Meta:
        model = TradeFill
        fields = (
            "id", "order_id", "asset", "side", "source", "quantity", "price",
            "fee", "filled_at", "created_at",
        )


class TradeOrderSerializer(serializers.ModelSerializer):
    asset = serializers.CharField(source="asset.symbol", read_only=True)
    fills = TradeFillSerializer(many=True, read_only=True)

    class Meta:
        model = TradeOrder
        fields = (
            "id", "proposal_id", "asset", "side", "order_type", "state",
            "requested_quantity", "execution_price", "reserved_amount", "total_fee",
            "market_snapshot_id", "created_at", "executed_at", "fills",
        )
