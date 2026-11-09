import pycountry
from django import forms

# COUNTRY FIELD ----------------------------------------------------------------

TOP_COUNTRIES = ["DE", "CH", "NL"]


def country_choices() -> list[tuple]:
    """Choices for a country ChoiceField (<c-country-select>): ISO 3166-1 alpha-2 codes

    An empty option first, so nothing is pre-selected, then TOP_COUNTRIES and all
    countries alphabetically. Nested lists render as <optgroup>.
    """
    names = {c.alpha_2: c.name for c in pycountry.countries}
    top = [(code, names[code]) for code in TOP_COUNTRIES]
    rest = sorted(
        ((code, name) for code, name in names.items() if code not in TOP_COUNTRIES),
        key=lambda item: item[1],
    )
    return [
        ("", "Select a country…"),
        ("---", top),
        ("All countries", rest),
    ]


def country_field() -> forms.ChoiceField:
    return forms.ChoiceField(choices=country_choices(), required=True)


# YES-NO FIELD -----------------------------------------------------------------


class YesNoField(forms.ChoiceField):
    """A Yes / No selection, shown as a Yes-No Toggle (<c-yes-no-toggle>).

    The toggle submits "true" / "false"; the answer stays "Yes" / "No", like
    the selection the question configures.
    """

    CHOICES = [("Yes", "Yes"), ("No", "No")]

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("choices", self.CHOICES)
        super().__init__(**kwargs)

    def to_python(self, value: object) -> str:
        value = super().to_python(value)
        return {"true": "Yes", "false": "No"}.get(value, value)
