import decimal, uuid
import apps.simulations.models
from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(name="Simulation", fields=[
        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
        ("name", models.CharField(default="Empresa Demo", max_length=120)),
        ("initial_capital", models.DecimalField(decimal_places=8, default=decimal.Decimal("10000.00000000"), max_digits=20)),
        ("currency", models.CharField(default="USDT", max_length=12)), ("is_demo", models.BooleanField(default=True)),
        ("access_token", models.CharField(default=apps.simulations.models.create_access_token, editable=False, max_length=64, unique=True)),
        ("created_at", models.DateTimeField(auto_now_add=True)),
    ])]

