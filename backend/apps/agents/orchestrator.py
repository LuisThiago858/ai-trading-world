from decimal import Decimal, ROUND_DOWN
from typing import TypedDict

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from langgraph.graph import END, START, StateGraph

from apps.market_data.models import MarketCandle
from apps.orders.models import TradeProposal
from apps.orders.services import create_agent_proposal
from .indicators import calculate_indicators
from .models import AgentResult, AnalysisCheckpoint, AnalysisRun
from .providers import LLMProviderError, get_provider
from .schemas import AlexOutput, MayaOutput, VictorOutput


class AnalysisCancelled(RuntimeError):
    pass


class AnalysisState(TypedDict, total=False):
    run_id: str
    indicators: dict
    portfolio: dict
    policy: dict
    alex: dict
    maya: dict
    victor: dict
    candidate_proposal_id: str | None
    conclusion: dict


AGENT_ROLES = {
    AgentResult.Agent.ALEX: "Análise técnica",
    AgentResult.Agent.MAYA: "Estratégia e composição de carteira",
    AgentResult.Agent.VICTOR: "Crítica e explicação do risco determinístico",
}


def _run(run_id):
    return AnalysisRun.objects.select_related(
        "simulation__portfolio", "simulation__risk_policy", "market_snapshot"
    ).get(pk=run_id)


def _ensure_active(run):
    run.refresh_from_db(fields=("cancel_requested", "status"))
    if run.cancel_requested or run.status == AnalysisRun.Status.CANCELLED:
        raise AnalysisCancelled("Análise cancelada pelo jogador.")


def _checkpoint(run, node, state):
    serializable = {key: value for key, value in state.items() if key != "run_id"}
    sequence = run.checkpoints.count() + 1
    AnalysisCheckpoint.objects.create(run=run, sequence=sequence, node=node, state=serializable)
    run.current_node = node
    run.checkpoint_state = serializable
    run.save(update_fields=("current_node", "checkpoint_state", "updated_at"))


def _completed_result(run, agent):
    return run.agent_results.filter(agent=agent, status=AgentResult.Status.COMPLETED).first()


def _invoke_agent(*, run, agent, schema, provider, context, indicators=None, evidence=None, hypotheses=None, disagreements=None):
    existing = _completed_result(run, agent)
    if existing:
        return existing.conclusion
    now = timezone.now()
    result, _ = AgentResult.objects.update_or_create(
        run=run,
        agent=agent,
        defaults={
            "role": AGENT_ROLES[agent],
            "status": AgentResult.Status.RUNNING,
            "provider": provider.name,
            "model_name": getattr(provider, "model", run.model_name),
            "started_at": now,
        },
    )
    try:
        generated = provider.generate(agent=agent, schema=schema, context=context)
    except Exception:
        result.status = AgentResult.Status.FAILED
        result.completed_at = timezone.now()
        result.save(update_fields=("status", "completed_at"))
        raise
    payload = generated.data.model_dump(mode="json")
    result.status = AgentResult.Status.COMPLETED
    result.provider = generated.provider
    result.model_name = generated.model
    result.indicators = indicators or {}
    result.evidence = evidence or context
    result.hypotheses = hypotheses or []
    result.conclusion = payload
    result.disagreements = disagreements or payload.get("disagreements", [])
    result.input_tokens = generated.input_tokens
    result.output_tokens = generated.output_tokens
    result.estimated_cost_usd = generated.estimated_cost_usd
    result.completed_at = timezone.now()
    result.save()
    return payload


def _base_state(run):
    snapshot = run.market_snapshot
    indicators = {}
    for symbol in run.requested_assets:
        candles = list(
            MarketCandle.objects.filter(
                asset__symbol=symbol,
                source=snapshot.source,
                opened_at__lte=snapshot.observed_at,
                is_closed=True,
            ).order_by("-opened_at")[:100]
        )
        candles.reverse()
        indicators[symbol] = calculate_indicators(candles)
    portfolio = run.simulation.portfolio
    positions = [
        {
            "symbol": position.asset.symbol,
            "quantity": str(position.quantity),
            "reserved_quantity": str(position.reserved_quantity),
            "available_quantity": str(position.quantity - position.reserved_quantity),
            "average_cost": str(position.average_cost),
        }
        for position in portfolio.positions.select_related("asset")
    ]
    policy = run.simulation.risk_policy
    return {
        "run_id": str(run.id),
        "indicators": indicators,
        "portfolio": {
            "equity": str(portfolio.total_equity),
            "available_balance": str(portfolio.available_balance),
            "realized_pnl": str(portfolio.realized_pnl),
            "positions": positions,
        },
        "policy": {
            "max_operation_percent": str(policy.max_operation_percent),
            "max_asset_exposure_percent": str(policy.max_asset_exposure_percent),
            "daily_loss_limit_percent": str(policy.daily_loss_limit_percent),
            "version": policy.version,
        },
    }


def build_graph(provider):
    def alex_node(state):
        run = _run(state["run_id"])
        _ensure_active(run)
        output = _invoke_agent(
            run=run,
            agent=AgentResult.Agent.ALEX,
            schema=AlexOutput,
            provider=provider,
            context={"assets": run.requested_assets, "indicators": state["indicators"]},
            indicators=state["indicators"],
        )
        update = {"alex": output}
        _checkpoint(run, "alex", {**state, **update})
        return update

    def maya_node(state):
        run = _run(state["run_id"])
        _ensure_active(run)
        context = {
            "alex": state["alex"],
            "equity": state["portfolio"]["equity"],
            "available_balance": state["portfolio"]["available_balance"],
            "positions": state["portfolio"]["positions"],
            "policy": state["policy"],
            "snapshot": {
                "id": str(run.market_snapshot_id),
                "observed_at": run.market_snapshot.observed_at.isoformat(),
                "valid_until": run.market_snapshot.valid_until.isoformat(),
            },
        }
        output = _invoke_agent(
            run=run,
            agent=AgentResult.Agent.MAYA,
            schema=MayaOutput,
            provider=provider,
            context=context,
            evidence={"alex": state["alex"], "portfolio": state["portfolio"], "policy": state["policy"]},
        )
        update = {"maya": output}
        _checkpoint(run, "maya", {**state, **update})
        return update

    def victor_node(state):
        run = _run(state["run_id"])
        _ensure_active(run)
        maya = state["maya"]
        proposal = run.proposals.first()
        if maya["action"] != "HOLD" and proposal is None:
            equity = Decimal(state["portfolio"]["equity"])
            allocation = Decimal(maya["allocation_percent"])
            target_notional = (equity * allocation / Decimal("100")).quantize(
                Decimal("0.00000001"), rounding=ROUND_DOWN
            )
            kwargs = {
                "simulation": run.simulation,
                "symbol": maya["asset"],
                "side": maya["action"],
                "justification": f"Análise multiagente {run.id}: {maya['reasoning']}",
                "evidence": {"alex": state["alex"], "maya": maya},
            }
            if maya["action"] == "BUY":
                kwargs["requested_amount"] = target_notional
            else:
                quote = run.market_snapshot.quotes.get(asset__symbol=maya["asset"])
                available = next(
                    (Decimal(item["available_quantity"]) for item in state["portfolio"]["positions"] if item["symbol"] == maya["asset"]),
                    Decimal("0"),
                )
                kwargs["requested_quantity"] = min(available, target_notional / quote.price).quantize(
                    Decimal("0.000000000001"), rounding=ROUND_DOWN
                )
            proposal = create_agent_proposal(analysis_run=run, **kwargs)
        risk = proposal.risk_summary if proposal else {"approved": True, "codes": [], "metrics": {}}
        context = {"maya": maya, "risk": risk, "proposal_id": str(proposal.id) if proposal else None}
        output = _invoke_agent(
            run=run,
            agent=AgentResult.Agent.VICTOR,
            schema=VictorOutput,
            provider=provider,
            context=context,
            evidence={"risk_assessment": risk, "maya": maya},
            hypotheses=["A execução permanece dependente de aprovação humana e nova revalidação."],
        )
        if proposal:
            proposal.evidence = {"alex": state["alex"], "maya": maya, "victor": output}
            proposal.save(update_fields=("evidence",))
        update = {"victor": output, "candidate_proposal_id": str(proposal.id) if proposal else None}
        _checkpoint(run, "victor", {**state, **update})
        return update

    def consolidate_node(state):
        run = _run(state["run_id"])
        _ensure_active(run)
        victor = state["victor"]
        proposal = run.proposals.first()
        action = victor["action"]
        if proposal and proposal.status == TradeProposal.Status.RISK_REJECTED:
            action = "HOLD"
        conclusion = {
            "action": action,
            "asset": state["maya"]["asset"] if action != "HOLD" else None,
            "summary": victor["reasoning"],
            "disagreements": state["maya"].get("disagreements", []),
            "proposal_id": str(proposal.id) if proposal else None,
            "requires_human_approval": bool(
                proposal and proposal.status == TradeProposal.Status.PENDING_APPROVAL
            ),
        }
        update = {"conclusion": conclusion}
        _checkpoint(run, "consolidate", {**state, **update})
        return update

    graph = StateGraph(AnalysisState)
    graph.add_node("alex", alex_node)
    graph.add_node("maya", maya_node)
    graph.add_node("victor", victor_node)
    graph.add_node("consolidate", consolidate_node)
    graph.add_edge(START, "alex")
    graph.add_edge("alex", "maya")
    graph.add_edge("maya", "victor")
    graph.add_edge("victor", "consolidate")
    graph.add_edge("consolidate", END)
    return graph.compile()


def execute_analysis_run(run_id, *, provider=None):
    with transaction.atomic():
        run = AnalysisRun.objects.select_for_update().select_related("market_snapshot").get(pk=run_id)
        if run.status == AnalysisRun.Status.COMPLETED:
            return run
        if run.cancel_requested or run.status == AnalysisRun.Status.CANCELLED:
            run.status = AnalysisRun.Status.CANCELLED
            run.completed_at = timezone.now()
            run.save(update_fields=("status", "completed_at", "updated_at"))
            return run
        if run.market_snapshot.valid_until <= timezone.now():
            run.status = AnalysisRun.Status.FAILED
            run.error = {"code": "STALE_MARKET_SNAPSHOT", "detail": "Snapshot de mercado desatualizado."}
            run.completed_at = timezone.now()
            run.save(update_fields=("status", "error", "completed_at", "updated_at"))
            return run
        run.status = AnalysisRun.Status.RUNNING
        run.started_at = run.started_at or timezone.now()
        run.attempts += 1
        run.error = {}
        run.save(update_fields=("status", "started_at", "attempts", "error", "updated_at"))
    provider = provider or get_provider()
    try:
        initial = _base_state(_run(run_id))
        final = build_graph(provider).invoke(initial)
    except AnalysisCancelled:
        AnalysisRun.objects.filter(pk=run_id).update(
            status=AnalysisRun.Status.CANCELLED, completed_at=timezone.now()
        )
        return AnalysisRun.objects.get(pk=run_id)
    except LLMProviderError as exc:
        AnalysisRun.objects.filter(pk=run_id).update(
            status=AnalysisRun.Status.FAILED,
            error={"code": exc.code, "detail": str(exc), "transient": exc.transient},
            completed_at=timezone.now(),
        )
        raise
    except Exception as exc:
        AnalysisRun.objects.filter(pk=run_id).update(
            status=AnalysisRun.Status.FAILED,
            error={"code": "ANALYSIS_FAILED", "detail": str(exc)[:300]},
            completed_at=timezone.now(),
        )
        raise
    totals = AgentResult.objects.filter(run_id=run_id).aggregate(
        input_tokens=Sum("input_tokens"), output_tokens=Sum("output_tokens"), cost=Sum("estimated_cost_usd")
    )
    AnalysisRun.objects.filter(pk=run_id).update(
        status=AnalysisRun.Status.COMPLETED,
        conclusion=final["conclusion"],
        input_tokens=totals["input_tokens"] or 0,
        output_tokens=totals["output_tokens"] or 0,
        estimated_cost_usd=totals["cost"] or Decimal("0"),
        completed_at=timezone.now(),
        current_node="completed",
    )
    return AnalysisRun.objects.get(pk=run_id)
