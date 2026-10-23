# ruff: noqa: EM101, EM102, TRY003
import json
from json import load
from pathlib import Path
from typing import Any

from django.core.management import CommandError, CommandParser
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from idat.dsa40.models import Vlopse, VLOPSEQuestion


class Command(BaseCommand):
    help = "Load vlopse questions from fixture file"

    def _reshape(self, q: dict[str, Any]) -> dict[str, Any]:
        req_data = {
            "key": q["id"],
            "text": q["Question"],
            "required": q["Required"].title(),
            "details": q["Details"] or "",
        }
        i_type = None
        match q["Type"]:
            case "free form":
                req_data["input_type"] = "text"
            case "selection":
                opts = q["Options"]
                opts = opts.split(", ")
                if len(opts) <= 1:
                    opts = opts[0].split("; ")
                if len(opts) <= 1:
                    raise TypeError("selections should have more than 1 value!")
                req_data["input_type"] = "selection"
                i_type = {"type": "selection", "options": opts}
            case "file upload":
                req_data["input_type"] = "file_upload"

            case "multi-select" | "date-select":
                raise NotImplementedError(f"{q['Type']} not yet implemented!")
        req_data["config"] = i_type
        return req_data

    def _load_serialized_questions(self, path: Path) -> list[dict[str, Any]]:
        with path.open() as f:
            qs: list[dict[str, Any]] = load(f)
        result = []
        for q in qs:
            q_id = q.get("id", "N/A")
            try:
                res = self._reshape(q)
                result.append(res)
            except Exception as e:  # noqa: BLE001
                self.stdout.write(self.style.WARNING(f"{q_id} caused {e}"))

        return result

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("paths", nargs="+", type=str)

    def handle(self, *args, **options) -> None:
        for p in options["paths"]:
            path = Path(p)
            vlopse_name = path.stem.lower()
            try:
                data = self._load_serialized_questions(path)
            except json.JSONDecodeError as e:
                raise CommandError from e

            vlopse, _new = Vlopse.objects.get_or_create(name=vlopse_name)
            self.stdout.write(f"Adding {len(data)} questions to {vlopse.key}")
            for q in data:
                q_id = q.get("id", "N/A")
                try:
                    VLOPSEQuestion.objects.get_or_create(vlopse=vlopse, **q)
                except IntegrityError as e:
                    self.stdout.write(self.style.WARNING(f"{q_id} caused {e}"))

            self.stdout.write(self.style.SUCCESS("Done"))
