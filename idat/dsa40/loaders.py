from json import load
from pathlib import Path

from idat.dsa40.models import DSAQuestion

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_questions() -> int:
    q_file = _FIXTURES_DIR / "questions_all.json"

    with q_file.open() as f:
        qs = load(f)

    for q in qs:
        q = dict(q)  # noqa: PLW2901
        q.pop("category", None)
        q.pop("granularity", None)
        q["text"] = q.pop("text_en")
        input_type = q.pop("type")
        if "options" in q:
            q["config"] = {"type": input_type, "options": q.pop("options")}
        q["input_type"] = input_type

        DSAQuestion.objects.get_or_create(**q)

    return len(qs)
