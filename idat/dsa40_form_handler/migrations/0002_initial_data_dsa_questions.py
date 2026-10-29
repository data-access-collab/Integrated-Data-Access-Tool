from json import load
from pathlib import Path

from django.db import migrations

from idat.dsa40_form_handler.form_field_types import config_adapter

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_DSA_QUESTIONS_FILE = _FIXTURES_DIR / "questions_all.json"


def load_initial_dsa_questions():
    with _DSA_QUESTIONS_FILE.open() as f:
        qs = load(f)

    assert len(qs) > 2, "There should be a few questions"
    for q in qs:
        q = dict(q)
        yield q


def load_data(apps, schema_editor):
    DSAQuestion = apps.get_model("dsa40_form_handler", "DSAQuestion")

    for entry in load_initial_dsa_questions():
        config = None
        assert "config" not in entry, "You're importing old fixtures"
        entry.pop("category", None)
        entry.pop("granularity", None)
        entry["key"] = entry.pop("id")
        entry["text"] = entry.pop("text_en")
        input_type = entry.pop("type")
        if "options" in entry:
            config = {"type": input_type, "options": entry.pop("options")}
            config_adapter.validate_python(config)
        entry["input_type"] = input_type

        DSAQuestion.objects.create(**entry, config=config)


def unload_data(apps, schema_editor):
    # Optional but nice for reversibility in dev
    apps.get_model("dsa40_form_handler", "DSAQuestion").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dsa40_form_handler", "0001_initial"),
    ]

    operations = [migrations.RunPython(load_data, unload_data)]
