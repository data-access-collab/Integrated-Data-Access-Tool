from django.forms.renderers import TemplatesSetting

from idat.core.forms.boundfield import IdatBoundField


class IdatFormRenderer(TemplatesSetting):
    """Render every form with the UI library's field components.

    `{{ form }}` uses forms/form.html, `{{ field.as_field_group }}` forms/field.html,
    which picks the component from IdatBoundField.component. A field's own
    `template_name` still wins over field_template_name.
    """

    form_template_name = "forms/form.html"
    field_template_name = "forms/field.html"
    bound_field_class = IdatBoundField
