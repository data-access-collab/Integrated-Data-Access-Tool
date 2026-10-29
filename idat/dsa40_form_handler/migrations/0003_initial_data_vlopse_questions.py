import json
from json import load
from pathlib import Path

from django.core.management import CommandError, CommandParser
from django.db import IntegrityError, migrations

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_VLOPSE_QUESTIONS_DIR = _FIXTURES_DIR / "questions"


def load_initial_vlopse_questions():
    for vlopse_file in _VLOPSE_QUESTIONS_DIR.glob("*.json"):
        name = vlopse_file.stem

        with vlopse_file.open() as f:
            qs= load(f)
        yield name, qs


def parse_input_type(entry):
    opts = entry.pop("Options", None)
    i_type = entry.pop("Type")
    result = {}
    match i_type:
        case "free form":
            result["input_type"] = "text"
        case "selection" | "multi-select":
            if opts == "New Research Program Application":
                result["input_type"] = "free form"
            elif opts == "[Date]":
                result["input_type"] = "date-select"
            elif opts in {"[EU Countries]", "[Countries]"}:
                result["input_type"] = i_type
                result["config"] = {"type": "selection", "options": opts}
            else:
                if opts in {"I agree", "I understand", None, ""}:
                    opts = "Yes, No"

                opts = opts.split("; ")
                if len(opts) <= 1:
                    opts = opts[0].split(", ")
                if len(opts) <= 1:
                    opts = opts[0].split()
                if len(opts) <= 1:
                    raise TypeError

                result["input_type"] = i_type
                result["config"] = {"type": i_type, "options": opts}
        case "file upload":
            result["input_type"] = "file_upload"

        case "date-select":
            result["input_type"] = i_type
        case _:
            raise NotImplementedError(f"{i_type} not yet implemented!")

    return result


def load_data(apps, schema_editor):
    Vlopse = apps.get_model("vlopse", "Vlopse")
    VLOPSEQuestion = apps.get_model("dsa40_form_handler", "VLOPSEQuestion")
    for vlopse_name, qs in load_initial_vlopse_questions():
        if vlopse_name == "X.com":
            vlopse_name = "X"
        vlopse = Vlopse.objects.get(name__iexact=vlopse_name)
        for entry in qs:
            base = {"key": entry.pop("id"), "text": entry.pop("Question")}
            details = entry.pop("details", None)
            if details is None:
                details = ""
            base["details"] = details
            required = entry.pop("Required")
            base["required"] = True if required == "N/A" else required.title()
            input_type = parse_input_type(entry)
            assert input_type["input_type"] is not None
            VLOPSEQuestion.objects.create(**base, **input_type, vlopse=vlopse)


def unload_data(apps, schema_editor):
    # Optional but nice for reversibility in dev
    apps.get_model("dsa40_form_handler", "VLOPSEQuestion").objects.all().delete()
    apps.get_model("dsa40_form_handler", "DSAQuestion").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dsa40_form_handler", "0002_initial_data_dsa_questions"),
        ("vlopse", "0002_initial_data"),
    ]

    operations = [migrations.RunPython(load_data, unload_data)]
