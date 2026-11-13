import django.db.models.deletion
from django.db import migrations, models


def backfill_execution_market_data(apps, schema_editor):
    TradeOrder = apps.get_model("orders", "TradeOrder")
    TradeFill = apps.get_model("orders", "TradeFill")
    for order in TradeOrder.objects.filter(market_snapshot__isnull=True).select_related(
        "proposal__market_snapshot"
    ):
        order.market_snapshot_id = order.proposal.market_snapshot_id
        order.save(update_fields=("market_snapshot",))
    for fill in TradeFill.objects.filter(market_snapshot__isnull=True).select_related(
        "order__market_snapshot"
    ):
        fill.market_snapshot_id = fill.order.market_snapshot_id
        fill.source = fill.order.market_snapshot.source
        fill.save(update_fields=("market_snapshot", "source"))


class Migration(migrations.Migration):
    dependencies = [
        ("market_data", "0002_seed_supported_assets"),
        ("orders", "0002_tradefill_market_snapshot_tradefill_source_and_more"),
    ]
    operations = [
        migrations.RunPython(backfill_execution_market_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="tradeorder",
            name="market_snapshot",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="trade_orders",
                to="market_data.marketsnapshot",
            ),
        ),
        migrations.AlterField(
            model_name="tradefill",
            name="market_snapshot",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="fills",
                to="market_data.marketsnapshot",
            ),
        ),
        migrations.AlterField(
            model_name="tradefill",
            name="source",
            field=models.CharField(max_length=24),
        ),
    ]
