import decimal
from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    initial = True
    dependencies = [("simulations", "0001_initial")]
    operations = [migrations.CreateModel(name="Portfolio", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("available_balance", models.DecimalField(decimal_places=8, default=decimal.Decimal("0"), max_digits=20)),
        ("total_equity", models.DecimalField(decimal_places=8, default=decimal.Decimal("0"), max_digits=20)),
        ("updated_at", models.DateTimeField(auto_now=True)),
        ("simulation", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="portfolio", to="simulations.simulation")),
    ])]

