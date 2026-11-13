from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.risk.models import RiskAssessment
from apps.simulations.auth import SessionTokenMixin
from .exceptions import TradingError
from .models import TradeFill, TradeOrder, TradeProposal
from .serializers import (
    ProposalCreateSerializer,
    ProposalDecisionInputSerializer,
    TradeFillSerializer,
    TradeOrderSerializer,
    TradeProposalSerializer,
)
from .services import (
    approve_proposal,
    create_manual_proposal,
    prevalidate_proposal,
    reject_proposal,
)


def _idempotency_key(request):
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key or len(key) > 100:
        raise TradingError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Header Idempotency-Key é obrigatório e deve ter até 100 caracteres.",
            http_status=400,
        )
    return key


class TradingAPIView(SessionTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def simulation_or_response(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        return simulation if simulation is not None else self.missing_token_response()

    @staticmethod
    def trading_error(exc):
        return Response(exc.as_dict(), status=exc.http_status)


class ProposalListCreateView(TradingAPIView):
    def get(self, request, simulation_id):
        simulation = self.simulation_or_response(request, simulation_id)
        if isinstance(simulation, Response):
            return simulation
        proposals = simulation.trade_proposals.select_related("asset", "market_snapshot").all().order_by("-created_at")[:100]
        return Response(TradeProposalSerializer(proposals, many=True).data)

    def post(self, request, simulation_id):
        simulation = self.simulation_or_response(request, simulation_id)
        if isinstance(simulation, Response):
            return simulation
        serializer = ProposalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal = create_manual_proposal(
                simulation=simulation,
                symbol=serializer.validated_data["asset"],
                side=serializer.validated_data["side"],
                requested_amount=serializer.validated_data.get("amount"),
                requested_quantity=serializer.validated_data.get("quantity"),
                justification=serializer.validated_data.get("justification", ""),
            )
        except TradingError as exc:
            return self.trading_error(exc)
        return Response(TradeProposalSerializer(proposal).data, status=status.HTTP_201_CREATED)


class ProposalRiskView(TradingAPIView):
    def post(self, request, simulation_id, proposal_id):
        simulation = self.simulation_or_response(request, simulation_id)
        if isinstance(simulation, Response):
            return simulation
        proposal = get_object_or_404(TradeProposal, pk=proposal_id, simulation=simulation)
        decision = prevalidate_proposal(proposal)
        return Response(decision.as_dict())


class ProposalApproveView(TradingAPIView):
    def post(self, request, simulation_id, proposal_id):
        simulation = self.simulation_or_response(request, simulation_id)
        if isinstance(simulation, Response):
            return simulation
        serializer = ProposalDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal, order, duplicate = approve_proposal(
                simulation=simulation,
                proposal_id=proposal_id,
                expected_version=serializer.validated_data["version"],
                idempotency_key=_idempotency_key(request),
            )
        except TradeProposal.DoesNotExist:
            return Response({"detail": "Proposta não encontrada."}, status=404)
        except TradingError as exc:
            return self.trading_error(exc)
        payload = {
            "proposal": TradeProposalSerializer(proposal).data,
            "order": TradeOrderSerializer(order).data if order else None,
            "duplicate": duplicate,
        }
        if order is None:
            return Response(payload, status=status.HTTP_409_CONFLICT)
        return Response(payload)


class ProposalRejectView(TradingAPIView):
    def post(self, request, simulation_id, proposal_id):
        simulation = self.simulation_or_response(request, simulation_id)
        if isinstance(simulation, Response):
            return simulation
        serializer = ProposalDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proposal, duplicate = reject_proposal(
                simulation=simulation,
                proposal_id=proposal_id,
                expected_version=serializer.validated_data["version"],
                idempotency_key=_idempotency_key(request),
            )
        except TradeProposal.DoesNotExist:
            return Response({"detail": "Proposta não encontrada."}, status=404)
        except TradingError as exc:
            return self.trading_error(exc)
        return Response({"proposal": TradeProposalSerializer(proposal).data, "duplicate": duplicate})


class OrderListView(TradingAPIView):
    def get(self, request, simulation_id):
        simulation = self.simulation_or_response(request, simulation_id)
        if isinstance(simulation, Response):
            return simulation
        orders = TradeOrder.objects.filter(simulation=simulation).select_related("asset").prefetch_related("fills").order_by("-created_at")[:100]
        return Response(TradeOrderSerializer(orders, many=True).data)


class FillListView(TradingAPIView):
    def get(self, request, simulation_id):
        simulation = self.simulation_or_response(request, simulation_id)
        if isinstance(simulation, Response):
            return simulation
        fills = TradeFill.objects.filter(order__simulation=simulation).select_related("order__asset").order_by("-filled_at")[:100]
        return Response(TradeFillSerializer(fills, many=True).data)
