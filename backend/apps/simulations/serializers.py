from rest_framework import serializers
from .models import Simulation

class SimulationSerializer(serializers.ModelSerializer):
    initial_capital = serializers.DecimalField(max_digits=20, decimal_places=8)
    class Meta:
        model = Simulation
        fields = ("id", "name", "initial_capital", "currency", "is_demo", "created_at")

class SimulationCreatedSerializer(SimulationSerializer):
    session_token = serializers.CharField(source="access_token", read_only=True)
    class Meta(SimulationSerializer.Meta):
        fields = SimulationSerializer.Meta.fields + ("session_token",)


