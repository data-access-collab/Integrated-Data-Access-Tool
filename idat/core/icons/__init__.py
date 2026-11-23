"""The icons <c-icon> can render: idat/assets/icons/allowlist.json, built into
icons.json (next to this file) by `npm run build:icons`."""

import json
from functools import cache
from pathlib import Path
from typing import NamedTuple

from django.utils.safestring import SafeString, mark_safe

ICONS_FILE = Path(__file__).with_name("icons.json")


class Icon(NamedTuple):
    body: SafeString  # the shapes, without an <svg> root
    view_box: str  # the icon set's grid, e.g. "0 0 24 24"
    filled: bool  # True: a filled logo (Simple Icons); False: a stroked Lucide icon


class UnknownIconError(LookupError):
    """Raised for a name that is not in idat/assets/icons/allowlist.json."""


@cache
def icons() -> dict[str, Icon]:
    data = json.loads(ICONS_FILE.read_text(encoding="utf-8"))["icons"]
    return {
        # generated from pinned icon packages, not user input
        name: Icon(mark_safe(icon["body"]), icon["viewBox"], icon["filled"])  # noqa: S308
        for name, icon in data.items()
    }


def get_icon(name: str) -> Icon:
    """The icon called <name>. An unknown name raises UnknownIconError."""
    try:
        return icons()[name]
    except KeyError:
        msg = (
            f"No icon named {name!r}. Add it to idat/assets/icons/allowlist.json and "
            "run `npm run build:icons`."
        )
        raise UnknownIconError(msg) from None
