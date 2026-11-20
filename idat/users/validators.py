import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def _check_digit(base_digits: str) -> str:
    """Return the ORCID check digit (ISO 7064 Mod 11-2) for the first 15 digits."""
    total = 0
    for digit in base_digits:
        total = (total + int(digit)) * 2
    remainder = total % 11
    check_value = (12 - remainder) % 11  # 0-10
    return "X" if check_value == 10 else str(check_value)  # 10 = "X" # noqa: PLR2004


def validate_orcid(value: str) -> None:
    if not ORCID_RE.match(value):
        raise ValidationError(_("Enter an ORCID iD in the format 0000-0000-0000-0000."))
    digits = value.replace("-", "")
    if _check_digit(digits[:-1]) != digits[-1]:
        raise ValidationError(_("This ORCID iD is not valid. Please check for typos."))
