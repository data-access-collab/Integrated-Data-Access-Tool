from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from idat.vlopse.models import validate_icon_name


def test_validate_icon_name_accepts_existing_icon():
    validate_icon_name("check")


def test_validate_icon_name_rejects_unknown_icon():
    with pytest.raises(ValidationError):
        validate_icon_name("no-such-icon")
