from django.db import migrations


ASSETS = (
    {
        "symbol": "BTC/USDT",
        "base_currency": "BTC",
        "quote_currency": "USDT",
        "provider_symbol": "BTC/USDT",
    },
    {
        "symbol": "ETH/USDT",
        "base_currency": "ETH",
        "quote_currency": "USDT",
        "provider_symbol": "ETH/USDT",
    },
)


def seed_assets(apps, schema_editor):
    Asset = apps.get_model("market_data", "Asset")
    for asset in ASSETS:
        Asset.objects.update_or_create(symbol=asset["symbol"], defaults=asset)


def remove_assets(apps, schema_editor):
    Asset = apps.get_model("market_data", "Asset")
    Asset.objects.filter(symbol__in=[asset["symbol"] for asset in ASSETS]).delete()


class Migration(migrations.Migration):
    dependencies = [("market_data", "0001_initial")]
    operations = [migrations.RunPython(seed_assets, remove_assets)]
