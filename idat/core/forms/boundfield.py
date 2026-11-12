from django import forms
from django.forms.widgets import Input
from django.utils.choices import flatten_choices
from django.utils.formats import localize
from django.utils.translation import gettext as _

# UI library component per widget class, rendered by templates/forms/field.html.
WIDGET_COMPONENTS: dict[type[forms.Widget], str] = {
    forms.HiddenInput: "hidden",
    forms.Textarea: "textarea",
    forms.CheckboxInput: "checkbox",
    forms.DateInput: "date",
    # no component yet: native widget inside <c-field-layout>
    forms.DateTimeInput: "fallback",
    forms.TimeInput: "fallback",
    forms.CheckboxSelectMultiple: "multi-select",
    forms.SelectMultiple: "multi-select",
    forms.NullBooleanSelect: "yes-no",
    forms.Select: "select",
    forms.FileInput: "file-plain",
    # text, email, url, number, password, search … (c-text-field reads input_type)
    Input: "text",
}


def widget_component(widget: forms.Widget) -> str:
    """The UI component that renders a widget.

    A widget names its own with a `ui_component` attribute;
    otherwise WIDGET_COMPONENTS decides; "fallback" without a match.
    """
    if component := getattr(widget, "ui_component", None):
        return component
    for cls in type(widget).__mro__:
        if cls in WIDGET_COMPONENTS:
            return WIDGET_COMPONENTS[cls]
    return "fallback"


class IdatBoundField(forms.BoundField):
    """BoundField of every form (set globally by IdatFormRenderer)."""

    @property
    def component(self) -> str:
        """Which field component renders this field (see templates/forms/field.html)."""
        return widget_component(self.field.widget)

    @property
    def display_value(self) -> object:
        """The answer as a person reads it, for read-only views: choice labels
        instead of values, Yes / No for booleans, localized dates and numbers.

        Uses cleaned_data once the form is validated, else the raw value. Empty
        answers stay empty (None, "", []), so templates can use |default:"—".
        """
        data = getattr(self.form, "cleaned_data", {})
        value = data[self.name] if self.name in data else self.value()
        if value in (None, "", [], ()):
            return value
        if isinstance(value, bool):
            return _("Yes") if value else _("No")

        values = value if isinstance(value, (list, tuple)) else [value]
        choices = getattr(self.field, "choices", None)
        labels = {str(k): v for k, v in flatten_choices(choices)} if choices else {}
        shown = [str(labels.get(str(v), localize(v))) for v in values]
        return ", ".join(shown) if isinstance(value, (list, tuple)) else shown[0]
