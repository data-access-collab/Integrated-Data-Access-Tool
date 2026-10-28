from idat.vlopse.loaders import list_all_vlopse_files, _load_json
import json
from pathlib import Path

from django.db import migrations



def _load_entries():
    for vlopse_name in list_all_vlopse_files():
        with open(vlopse_name) as f:
            yield json.load(f)


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
