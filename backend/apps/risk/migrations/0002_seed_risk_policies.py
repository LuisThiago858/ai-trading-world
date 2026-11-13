from django.db import migrations


def seed_policies(apps, schema_editor):
    Simulation = apps.get_model("simulations", "Simulation")
    RiskPolicy = apps.get_model("risk", "RiskPolicy")
    for simulation in Simulation.objects.all():
        RiskPolicy.objects.get_or_create(simulation=simulation)


class Migration(migrations.Migration):
    dependencies = [("risk", "0001_initial")]
    operations = [migrations.RunPython(seed_policies, migrations.RunPython.noop)]
