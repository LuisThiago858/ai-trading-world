from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.simulations.auth import SessionTokenMixin
from .models import AnalysisRun
from .serializers import AgentResultSerializer, AnalysisCreateSerializer, AnalysisRunSerializer
from .services import AnalysisRequestError, cancel_analysis_run, create_analysis_run


def _idempotency_key(request):
    value = request.headers.get("Idempotency-Key", "").strip()
    if not value or len(value) > 100:
        return None
    return value


class AnalysisListCreateView(SessionTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        if simulation is None:
            return self.missing_token_response()
        try:
            limit = min(max(int(request.query_params.get("limit", 20)), 1), 100)
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except ValueError:
            return Response({"detail": "Paginação inválida."}, status=400)
        queryset = simulation.analysis_runs.select_related("market_snapshot").prefetch_related("agent_results", "proposals__asset")
        return Response({
            "count": queryset.count(),
            "limit": limit,
            "offset": offset,
            "results": AnalysisRunSerializer(queryset[offset : offset + limit], many=True).data,
        })

    def post(self, request, simulation_id):
        simulation = self.get_simulation(request, simulation_id)
        if simulation is None:
            return self.missing_token_response()
        key = _idempotency_key(request)
        if key is None:
            return Response({"code": "IDEMPOTENCY_KEY_REQUIRED", "detail": "Idempotency-Key é obrigatório."}, status=400)
        serializer = AnalysisCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            run, created = create_analysis_run(
                simulation=simulation,
                assets=serializer.validated_data["assets"],
                idempotency_key=key,
            )
        except AnalysisRequestError as exc:
            return Response({"code": exc.code, "detail": exc.detail}, status=exc.http_status)
        return Response(
            {**AnalysisRunSerializer(run).data, "duplicate": not created},
            status=status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK,
        )


class RunTokenMixin(SessionTokenMixin):
    def get_run(self, request, run_id):
        token = request.headers.get("X-Demo-Session-Token", "")
        if not token:
            return None
        return get_object_or_404(
            AnalysisRun.objects.select_related("simulation", "market_snapshot").prefetch_related("agent_results", "proposals__asset"),
            pk=run_id,
            simulation__access_token=token,
            simulation__is_demo=True,
        )


class AnalysisDetailView(RunTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, run_id):
        run = self.get_run(request, run_id)
        return self.missing_token_response() if run is None else Response(AnalysisRunSerializer(run).data)


class AgentResultListView(RunTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, run_id):
        run = self.get_run(request, run_id)
        return self.missing_token_response() if run is None else Response(AgentResultSerializer(run.agent_results.all(), many=True).data)


class AnalysisCancelView(RunTokenMixin, APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, run_id):
        run = self.get_run(request, run_id)
        if run is None:
            return self.missing_token_response()
        run, changed = cancel_analysis_run(run)
        return Response({**AnalysisRunSerializer(run).data, "changed": changed})
