from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.market_data.models import Asset
from apps.market_data.services import latest_ready_snapshot
from apps.risk.models import RiskAssessment
from apps.risk.services import evaluate_proposal, get_policy
from .exceptions import TradingError
from .execution import execute_authorized_proposal
from .models import ProposalDecision, TradeProposal
from .pricing import estimate_market_order


def create_trade_proposal(
    *, simulation, symbol, side, requested_amount=None, requested_quantity=None,
    justification="", origin=TradeProposal.Origin.MANUAL, analysis_run=None, evidence=None,
):
    try:
        asset = Asset.objects.get(symbol=symbol, is_active=True)
    except Asset.DoesNotExist as exc:
        raise TradingError("UNSUPPORTED_ASSET", "Ativo não suportado.", http_status=400) from exc
    snapshot = latest_ready_snapshot(simulation)
    if snapshot is None:
        raise TradingError("MARKET_UNAVAILABLE", "Nenhum snapshot de mercado disponível.")
    quote = snapshot.quotes.filter(asset=asset).first()
    if quote is None:
        raise TradingError("MARKET_UNAVAILABLE", "Cotação do ativo indisponível.")
    policy = get_policy(simulation)
    try:
        estimate = estimate_market_order(
            side=side,
            quote_price=quote.price,
            policy=policy,
            requested_amount=requested_amount,
            requested_quantity=requested_quantity,
        )
    except ValueError as exc:
        raise TradingError("INVALID_ORDER_VALUE", str(exc), http_status=400) from exc

    proposal = TradeProposal.objects.create(
        simulation=simulation,
        market_snapshot=snapshot,
        asset=asset,
        side=side,
        origin=origin,
        analysis_run=analysis_run,
        evidence=evidence or {},
        requested_quantity=estimate.quantity,
        requested_amount=requested_amount if side == TradeProposal.Side.BUY else None,
        reference_price=quote.price,
        estimated_notional=estimate.gross,
        estimated_fee=estimate.fee,
        estimated_total=estimate.total,
        justification=(justification or "Proposta manual do jogador")[:300],
        expires_at=timezone.now() + timedelta(seconds=policy.proposal_ttl_seconds),
    )
    decision = evaluate_proposal(proposal, stage=RiskAssessment.Stage.PREVIEW)
    proposal.risk_summary = decision.as_dict()
    proposal.status = (
        TradeProposal.Status.PENDING_APPROVAL
        if decision.approved
        else TradeProposal.Status.RISK_REJECTED
    )
    proposal.save(update_fields=("risk_summary", "status"))
    return proposal


def create_manual_proposal(**kwargs):
    return create_trade_proposal(**kwargs, origin=TradeProposal.Origin.MANUAL)


def create_agent_proposal(*, analysis_run, **kwargs):
    return create_trade_proposal(
        **kwargs,
        analysis_run=analysis_run,
        origin=TradeProposal.Origin.AI_AGENT,
    )


def prevalidate_proposal(proposal):
    return evaluate_proposal(proposal, stage=RiskAssessment.Stage.PREVIEW)


def _validate_version(proposal, expected_version):
    if proposal.version != expected_version:
        raise TradingError(
            "PROPOSAL_VERSION_CONFLICT",
            "A proposta mudou; revise os dados antes de autorizar.",
            data={"current_version": proposal.version},
        )


def approve_proposal(*, simulation, proposal_id, expected_version, idempotency_key, failure_hook=None):
    with transaction.atomic():
        simulation.__class__.objects.select_for_update().get(pk=simulation.pk)
        proposal = TradeProposal.objects.select_for_update(of=("self",)).select_related(
            "simulation", "asset", "market_snapshot", "simulation__portfolio"
        ).get(pk=proposal_id, simulation=simulation)
        existing_decision = ProposalDecision.objects.filter(
            simulation=simulation, idempotency_key=idempotency_key
        ).first()
        if existing_decision:
            if existing_decision.proposal_id != proposal.id or existing_decision.decision != ProposalDecision.Decision.APPROVE:
                raise TradingError("IDEMPOTENCY_CONFLICT", "Chave de idempotência já utilizada.")
            return proposal, getattr(proposal, "order", None), True
        if hasattr(proposal, "order"):
            return proposal, proposal.order, True

        _validate_version(proposal, expected_version)
        decision_record = ProposalDecision.objects.create(
            proposal=proposal,
            simulation=simulation,
            decision=ProposalDecision.Decision.APPROVE,
            proposal_version=proposal.version,
            idempotency_key=idempotency_key,
        )
        if proposal.expires_at <= timezone.now():
            proposal.status = TradeProposal.Status.EXPIRED
            proposal.save(update_fields=("status",))
            return proposal, None, False

        risk = evaluate_proposal(proposal, stage=RiskAssessment.Stage.EXECUTION)
        if not risk.approved:
            proposal.status = TradeProposal.Status.INVALIDATED
            proposal.risk_summary = risk.as_dict()
            proposal.save(update_fields=("status", "risk_summary"))
            return proposal, None, False

        proposal.status = TradeProposal.Status.AUTHORIZED
        proposal.authorized_at = decision_record.created_at
        proposal.save(update_fields=("status", "authorized_at"))
        order = execute_authorized_proposal(
            proposal, idempotency_key=idempotency_key, failure_hook=failure_hook
        )
        proposal.refresh_from_db()
        return proposal, order, False


def reject_proposal(*, simulation, proposal_id, expected_version, idempotency_key):
    with transaction.atomic():
        proposal = TradeProposal.objects.select_for_update().get(
            pk=proposal_id, simulation=simulation
        )
        existing = ProposalDecision.objects.filter(
            simulation=simulation, idempotency_key=idempotency_key
        ).first()
        if existing:
            if existing.proposal_id != proposal.id or existing.decision != ProposalDecision.Decision.REJECT:
                raise TradingError("IDEMPOTENCY_CONFLICT", "Chave de idempotência já utilizada.")
            return proposal, True
        _validate_version(proposal, expected_version)
        if proposal.status != TradeProposal.Status.PENDING_APPROVAL:
            raise TradingError("INVALID_PROPOSAL_STATUS", "A proposta não está pendente de aprovação.")
        ProposalDecision.objects.create(
            proposal=proposal,
            simulation=simulation,
            decision=ProposalDecision.Decision.REJECT,
            proposal_version=proposal.version,
            idempotency_key=idempotency_key,
        )
        proposal.status = TradeProposal.Status.REJECTED
        proposal.save(update_fields=("status",))
        return proposal, False
