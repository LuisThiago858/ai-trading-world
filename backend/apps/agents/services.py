import uuid

from django.conf import settings
from django.db import transaction

from apps.market_data.providers import SUPPORTED_SYMBOLS
from apps.market_data.services import latest_ready_snapshot
from .models import AnalysisRun


class AnalysisRequestError(RuntimeError):
    def __init__(self, code, detail, http_status=400):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.http_status = http_status


def _dispatch(run_id):
    from .tasks import process_analysis_run

    task_id = f"analysis-{run_id}"
    try:
        process_analysis_run.apply_async(args=(str(run_id),), task_id=task_id, expires=120)
        AnalysisRun.objects.filter(pk=run_id).update(celery_task_id=task_id)
    except Exception as exc:
        AnalysisRun.objects.filter(pk=run_id).update(
            status=AnalysisRun.Status.FAILED,
            error={"code": "TASK_DISPATCH_FAILED", "detail": str(exc)[:300]},
        )


def create_analysis_run(*, simulation, assets, idempotency_key):
    normalized = sorted(set(assets))
    if not normalized or set(normalized) - set(SUPPORTED_SYMBOLS):
        raise AnalysisRequestError("INVALID_ASSETS", "Selecione BTC/USDT, ETH/USDT ou ambos.")
    existing = AnalysisRun.objects.filter(
        simulation=simulation, request_idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing, False
    snapshot = latest_ready_snapshot(simulation)
    if snapshot is None:
        raise AnalysisRequestError("MARKET_UNAVAILABLE", "Snapshot persistido indisponível.", 409)
    provider = settings.LLM_PROVIDER
    with transaction.atomic():
        run = AnalysisRun.objects.create(
            simulation=simulation,
            market_snapshot=snapshot,
            requested_assets=normalized,
            request_idempotency_key=idempotency_key,
            graph_thread_id=f"analysis-{uuid.uuid4()}",
            provider="deterministic_mock" if provider == "mock" else provider,
            provider_mode="mock" if provider == "mock" else "real",
            model_name="deterministic-mock-v1" if provider == "mock" else settings.LLM_MODEL,
        )
        transaction.on_commit(lambda: _dispatch(run.id))
    run.refresh_from_db()
    return run, True


def cancel_analysis_run(run):
    if run.status in {AnalysisRun.Status.COMPLETED, AnalysisRun.Status.FAILED, AnalysisRun.Status.CANCELLED}:
        return run, False
    run.cancel_requested = True
    run.status = AnalysisRun.Status.CANCELLED
    run.save(update_fields=("cancel_requested", "status", "updated_at"))
    return run, True
