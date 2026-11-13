from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from .models import Simulation


class SessionTokenMixin:
    """Restrict a view to the demo session identified by its opaque local token."""

    def get_simulation(self, request, simulation_id):
        token = request.headers.get("X-Demo-Session-Token", "")
        if not token:
            return None
        return get_object_or_404(
            Simulation,
            id=simulation_id,
            access_token=token,
            is_demo=True,
        )

    @staticmethod
    def missing_token_response():
        return Response(
            {"detail": "Token da sessão demo é obrigatório."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
