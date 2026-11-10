from django import forms
from django.test import SimpleTestCase

from idat.core.forms.boundfield import IdatBoundField, widget_component
from idat.core.forms.fields import YesNoField, country_field


class _AllFieldsForm(forms.Form):
    """A plain form: the renderer still applies."""

    text = forms.CharField()
    email = forms.EmailField()
    number = forms.IntegerField()
    long_text = forms.CharField(widget=forms.Textarea)
    choice = forms.ChoiceField(choices=[("a", "A")])
    multiple = forms.MultipleChoiceField(choices=[("a", "A")])
    checkboxes = forms.MultipleChoiceField(
        choices=[("a", "A")], widget=forms.CheckboxSelectMultiple
    )
    date = forms.DateField()
    accept = forms.BooleanField()
    maybe = forms.NullBooleanField()
    yes_no = YesNoField()
    country = country_field()
    upload = forms.FileField()
    radio = forms.ChoiceField(
        choices=[("a", "A"), ("b", "B")], widget=forms.RadioSelect
    )
    time = forms.TimeField()
    secret = forms.CharField(widget=forms.HiddenInput)


EXPECTED_COMPONENTS = {
    "text": "text",
    "email": "text",
    "number": "text",
    "long_text": "textarea",
    "choice": "select",
    "multiple": "multi-select",
    "checkboxes": "multi-select",
    "date": "date",
    "accept": "checkbox",
    "maybe": "yes-no",
    "yes_no": "yes-no",
    "country": "country",
    "upload": "file-plain",
    "radio": "fallback",
    "time": "fallback",
    "secret": "hidden",
}


class WidgetComponentTests(SimpleTestCase):
    def test_every_form_gets_the_idat_bound_field(self):
        form = _AllFieldsForm()

        self.assertIsInstance(form["text"], IdatBoundField)

    def test_component_per_stock_widget(self):
        form = _AllFieldsForm()

        self.assertEqual({bf.name: bf.component for bf in form}, EXPECTED_COMPONENTS)

    def test_custom_widget_names_its_component(self):
        class _Widget(forms.TextInput):
            ui_component = "file"

        self.assertEqual(widget_component(_Widget()), "file")

    def test_yes_no_keeps_its_id(self):
        form = _AllFieldsForm()

        self.assertEqual(form["yes_no"].id_for_label, "id_yes_no")
        self.assertIn('id="id_yes_no"', form["yes_no"].as_field_group())

    def test_unknown_widget_falls_back(self):
        self.assertEqual(widget_component(forms.SplitDateTimeWidget()), "fallback")


class FormRenderingTests(SimpleTestCase):
    def test_form_renders_components_not_django_defaults(self):
        form = _AllFieldsForm(data={})
        form.is_valid()
        html = str(form)

        # cotton compiled every tag
        self.assertNotIn("<c-", html)
        # Django's default field template isn't used
        self.assertNotIn('class="helptext"', html)
        # components: text field, country combobox, yes-no radiogroup, date field
        self.assertIn('type="email"', html)
        self.assertIn('role="combobox"', html)
        self.assertIn('role="radiogroup"', html)
        self.assertIn('aria-invalid="true"', html)
        # the hidden field's error is reported on the form
        self.assertIn("(Hidden field secret)", html)

    def test_fallback_keeps_label_and_native_widget(self):
        form = _AllFieldsForm()
        html = form["time"].as_field_group()  # fallback field

        self.assertIn(f'for="{form["time"].id_for_label}"', html)
        self.assertIn('name="time"', html)

    def test_field_template_name_still_wins(self):
        class _Form(forms.Form):
            name = forms.CharField(template_name="django/forms/field.html")

        html = _Form()["name"].as_field_group()

        self.assertIn("<label", html)
        self.assertNotIn("type-label-lg", html)
