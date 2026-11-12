import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.forms.renderers import get_default_renderer
from django.test import SimpleTestCase
from django.utils.formats import date_format

from idat.core.forms.boundfield import IdatBoundField, widget_component
from idat.core.forms.fields import TOP_COUNTRIES, YesNoField, country_field
from idat.core.forms.renderers import IdatFormRenderer


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
    def test_idat_renderer_is_the_default(self):
        self.assertIsInstance(get_default_renderer(), IdatFormRenderer)

    def test_no_field_overrides_the_idat_bound_field(self):
        form = _AllFieldsForm()
        for name in form.fields:
            with self.subTest(field=name):
                self.assertIsInstance(form[name], IdatBoundField)

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


class DisplayValueTests(SimpleTestCase):
    class _Form(forms.Form):
        name = forms.CharField(required=False)
        role = forms.ChoiceField(
            choices=[("pi", "Principal investigator"), ("co", "Co-PI")]
        )
        topics = forms.MultipleChoiceField(
            choices=[("health", "Public health"), ("elections", "Elections")]
        )
        country = country_field()
        yes_no = YesNoField()
        maybe = forms.NullBooleanField()
        start = forms.DateField()
        team_size = forms.IntegerField()

    DATA = {
        "name": "",
        "role": "pi",
        "topics": ["health", "elections"],
        "country": "DE",
        "yes_no": "true",
        "maybe": "false",
        "start": "2027-03-14",
        "team_size": "12",
    }

    def test_validated_form_shows_labels_and_readable_values(self):
        form = self._Form(data=self.DATA)
        self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(
            {bf.name: bf.display_value for bf in form},
            {
                "name": "",
                "role": "Principal investigator",
                "topics": "Public health, Elections",
                "country": "Germany",
                "yes_no": "Yes",
                "maybe": "No",
                "start": date_format(datetime.date(2027, 3, 14)),
                "team_size": "12",
            },
        )

    def test_unvalidated_form_uses_raw_values(self):
        form = self._Form(data=self.DATA)

        self.assertEqual(form["role"].display_value, "Principal investigator")
        self.assertEqual(form["country"].display_value, "Germany")

    def test_value_without_a_choice_is_shown_as_is(self):
        form = self._Form(data={**self.DATA, "country": "Germany"})

        self.assertEqual(form["country"].display_value, "Germany")

    def test_empty_answers_stay_empty(self):
        form = self._Form(data={})

        for name in ("start", "topics", "maybe"):
            with self.subTest(name=name):
                self.assertIn(form[name].display_value, (None, "", []))


class CountryFieldTests(SimpleTestCase):
    def test_validates_codes_from_both_groups_and_rejects_placeholders(self):
        field = country_field()

        self.assertEqual(field.choices[0][0], "")
        self.assertEqual(field.clean(TOP_COUNTRIES[0]), TOP_COUNTRIES[0])
        self.assertEqual(field.clean("FR"), "FR")
        for value in ("", "---"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                field.clean(value)


class YesNoFieldTests(SimpleTestCase):
    def test_keeps_yes_no_answers_from_the_toggle(self):
        field = YesNoField()

        self.assertEqual(field.clean("true"), "Yes")
        self.assertEqual(field.clean("false"), "No")
        self.assertEqual(field.clean("Yes"), "Yes")
        with self.assertRaises(ValidationError):
            field.clean("maybe")
