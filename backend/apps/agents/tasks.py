from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone

from .models import AnalysisRun
from .orchestrator import execute_analysis_run
from .providers import LLMProviderError


@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    time_limit=settings.CELERY_TASK_TIME_LIMIT,
    acks_late=True,
)
def process_analysis_run(self, run_id):
    try:
        execute_analysis_run(run_id)
    except LLMProviderError as exc:
        if exc.transient and self.request.retries + 1 < settings.ANALYSIS_MAX_ATTEMPTS:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        raise
    except SoftTimeLimitExceeded:
        AnalysisRun.objects.filter(pk=run_id).update(
            status=AnalysisRun.Status.FAILED,
            error={"code": "ANALYSIS_TIMEOUT", "detail": "A análise excedeu o tempo permitido."},
            completed_at=timezone.now(),
        )
        raise
    return run_id
