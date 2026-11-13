from rest_framework import serializers

from apps.orders.serializers import TradeProposalSerializer
from .models import AgentResult, AnalysisRun


class AnalysisCreateSerializer(serializers.Serializer):
    assets = serializers.ListField(
        child=serializers.ChoiceField(choices=("BTC/USDT", "ETH/USDT")),
        min_length=1,
        max_length=2,
    )


class AgentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentResult
        fields = (
            "id", "agent", "role", "status", "provider", "model_name", "schema_version",
            "indicators", "evidence", "hypotheses", "conclusion", "disagreements",
            "input_tokens", "output_tokens", "estimated_cost_usd", "started_at", "completed_at",
        )


class AnalysisRunSerializer(serializers.ModelSerializer):
    snapshot_id = serializers.UUIDField(source="market_snapshot_id", read_only=True)
    agent_results = AgentResultSerializer(many=True, read_only=True)
    proposal = serializers.SerializerMethodField()
    mock_notice = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisRun
        fields = (
            "id", "simulation_id", "snapshot_id", "requested_assets", "status", "current_node",
            "provider", "provider_mode", "model_name", "conclusion", "error", "input_tokens",
            "output_tokens", "estimated_cost_usd", "attempts", "started_at", "completed_at",
            "created_at", "updated_at", "agent_results", "proposal", "mock_notice",
        )

    def get_proposal(self, obj):
        proposal = obj.proposals.select_related("asset", "market_snapshot").first()
        return TradeProposalSerializer(proposal).data if proposal else None

    def get_mock_notice(self, obj):
        if obj.provider_mode == "mock":
            return "Análise gerada pelo mock determinístico para desenvolvimento; não é resposta de um modelo real."
        return None
