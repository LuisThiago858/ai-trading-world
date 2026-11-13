import secrets
import uuid
from decimal import Decimal
from django.db import models

def create_access_token():
    return secrets.token_urlsafe(32)

class Simulation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, default="Empresa Demo")
    initial_capital = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal("10000.00000000"))
    currency = models.CharField(max_length=12, default="USDT")
    is_demo = models.BooleanField(default=True)
    access_token = models.CharField(max_length=64, unique=True, default=create_access_token, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

