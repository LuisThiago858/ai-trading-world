from rest_framework import serializers

from .models import LedgerEntry, LedgerTransaction


class LedgerEntrySerializer(serializers.ModelSerializer):
    account_kind = serializers.CharField(source="account.kind", read_only=True)
    asset_code = serializers.CharField(source="account.asset_code", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = ("account_kind", "asset_code", "amount", "created_at")


class LedgerTransactionSerializer(serializers.ModelSerializer):
    entries = LedgerEntrySerializer(many=True, read_only=True)

    class Meta:
        model = LedgerTransaction
        fields = (
            "id",
            "kind",
            "idempotency_key",
            "description",
            "occurred_at",
            "created_at",
            "entries",
        )
