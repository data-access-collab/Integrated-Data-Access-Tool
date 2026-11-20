from django import forms


class YesNoWidget(forms.RadioSelect):
    """Yes / No answer, rendered as a Yes-No Toggle (<c-yes-no-toggle>)."""

    ui_component = "yes-no"

    def id_for_label(self, id_: str, index: str | None = None) -> str:
        # RadioSelect returns "" for the group; the toggle needs the id for its first
        # radio and the -error / -help ids
        return id_ if index is None else super().id_for_label(id_, index)


class CountrySelect(forms.Select):
    """ISO 3166-1 country, shown as a searchable Country Select (<c-country-select>)."""

    ui_component = "country"
