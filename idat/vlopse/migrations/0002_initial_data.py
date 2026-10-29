import json
from pathlib import Path

from django.db import migrations

_VLOPSE_SEED_FILE = Path(__file__).parent / "data" / "0002_initial_data.json"


def _load_entries():
    with open(_VLOPSE_SEED_FILE) as f:
        data = json.load(f)
        yield from data


def load_vlopse(apps, schema_editor):
    Vlopse = apps.get_model("vlopse", "Vlopse")
    for entry in _load_entries():
        data = dict(entry)
        Vlopse.objects.update_or_create(**data)


def unload_vlopse(apps, schema_editor):
    Vlopse = apps.get_model("vlopse", "Vlopse")
    Vlopse.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("vlopse", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_vlopse, unload_vlopse),
    ]
