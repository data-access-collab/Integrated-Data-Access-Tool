import pycountry

# Shown first, above the alphabetical list.
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
