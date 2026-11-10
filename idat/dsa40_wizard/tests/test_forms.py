from __future__ import annotations

import json
import re
from html import unescape
from unittest import mock

from django import forms
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils.html import escape

from idat.core.forms.fields import TOP_COUNTRIES, YesNoField, country_field
from idat.dsa40_form_handler.models import InputType, QuestionCategory
from idat.dsa40_form_handler.tests.factories import DsaQuestionFactory
from idat.dsa40_wizard.forms import (
    DEFAULT_CLIENT_FILE_TYPES,
    ClientFileField,
    FormQuestion,
    QuestionsForm,
    get_question_field,
)
from idat.dsa40_wizard.sections import SECTION_META


class CountryFieldTests(SimpleTestCase):
    def test_validates_codes_from_both_groups_and_rejects_placeholders(self):
        field = country_field()

        self.assertEqual(field.clean(TOP_COUNTRIES[0]), TOP_COUNTRIES[0])
        self.assertEqual(field.clean("FR"), "FR")
        for value in ("", "---"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                field.clean(value)

    def test_defaults_to_empty_placeholder(self):
        self.assertEqual(country_field().choices[0][0], "")


class QuestionsFormTests(SimpleTestCase):
    def test_questions_form_requires_only_required_questions(self):
        required = DsaQuestionFactory.build(key="email", input_type=InputType.TEXT)
        optional = DsaQuestionFactory.build(key="nickname", input_type=InputType.TEXT)
        config = [FormQuestion(required, True), FormQuestion(optional, False)]

        with_required = QuestionsForm(
            data={"email": "a@example.org"}, form_questions=config
        )
        without_required = QuestionsForm(
            data={"nickname": "ada"}, form_questions=config
        )

        self.assertTrue(with_required.is_valid())
        self.assertFalse(without_required.is_valid())
        self.assertIn("email", without_required.errors)

    def test_questions_form_prefills_stored_answers(self):
        question = DsaQuestionFactory.build(key="email", input_type=InputType.TEXT)

        form = QuestionsForm(
            form_questions=[FormQuestion(question, True)],
            initial={"email": "a@example.org"},
        )

        self.assertEqual(form["email"].value(), "a@example.org")

    def test_selection_question_accepts_flat_option_list(self):
        question = DsaQuestionFactory.build(
            key="prev-experience",
            input_type=InputType.SELECTION,
            config={"type": "selection", "options": ["Yes", "No"]},
        )
        config = [FormQuestion(question, True)]

        valid = QuestionsForm(data={"prev-experience": "No"}, form_questions=config)
        invalid = QuestionsForm(
            data={"prev-experience": "Maybe"}, form_questions=config
        )

        self.assertTrue(valid.is_valid())
        self.assertFalse(invalid.is_valid())

    def test_iso_3166_1_question_uses_country_field(self):
        question = DsaQuestionFactory.build(
            key="country", input_type=InputType.ISO_3166_1
        )

        with mock.patch("idat.dsa40_wizard.forms.country_field") as factory:
            form = QuestionsForm(form_questions=[FormQuestion(question, True)])

        factory.assert_called_once_with()
        self.assertIs(form.fields["country"], factory.return_value)


class ClientFileFieldTests(SimpleTestCase):
    def file_meta(self, **overrides) -> dict:
        return {
            "name": "cv.pdf",
            "size": 1024,
            "type": "application/pdf",
            "sha256": "a" * 64,
            **overrides,
        }

    def test_accepts_metadata_as_json_or_dict(self):
        field = ClientFileField()

        self.assertEqual(field.clean(json.dumps(self.file_meta())), self.file_meta())
        self.assertEqual(field.clean(self.file_meta()), self.file_meta())

    def test_rejects_malformed_metadata(self):
        field = ClientFileField()
        for value in [
            "not json",
            "[]",
            self.file_meta(sha256="xyz"),
            self.file_meta(size="1024"),
            self.file_meta(size=0),
            self.file_meta(name=""),
            self.file_meta(name="x" * 256),
            self.file_meta(extra="field"),
            {"name": "cv.pdf", "size": 1024},
        ]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                field.clean(value)

    def test_empty_value_is_rejected_only_when_required(self):
        with self.assertRaises(ValidationError):
            ClientFileField().clean("")
        self.assertIsNone(ClientFileField(required=False).clean(""))

    def test_widget_submits_metadata_only_via_hidden_input(self):
        question = DsaQuestionFactory.build(key="cv", input_type=InputType.FILE_UPLOAD)
        form = QuestionsForm(
            form_questions=[FormQuestion(question, True)],
            initial={"cv": self.file_meta()},
        )

        html = str(form["cv"])

        value = escape(json.dumps(self.file_meta()))
        self.assertInHTML(
            f'<input type="hidden" name="cv" value="{value}" x-ref="metadataInput">',
            html,
        )
        self.assertNotIn('type="file" name=', html)
        self.assertNotIn("required", html)

    def test_widget_passes_the_fields_types_to_the_browser(self):

        def get_form_with_field(field: forms.Field) -> forms.Form:
            """A form with the given field as "file"."""
            return type("FileForm", (forms.Form,), {"file": field})()

        html = str(get_form_with_field(ClientFileField(types=(".png", ".txt")))["file"])

        self.assertIn('accept=".png,.txt"', html)
        types = json.loads(unescape(re.search(r'data-types="([^"]*)"', html)[1]))
        self.assertEqual(types, {".png": "image/png", ".txt": "text/plain"})

    def test_default_types_are_set(self):
        self.assertEqual(ClientFileField().types, DEFAULT_CLIENT_FILE_TYPES)

    def test_unknown_types_are_rejected(self):
        with self.assertRaisesMessage(ValueError, ".exe"):
            ClientFileField(types=(".pdf", ".exe"))


def text_question(key: str, category: str):
    return DsaQuestionFactory.build(
        key=key, input_type=InputType.TEXT, category=category
    )


class QuestionsFormSectionsTests(SimpleTestCase):
    def make_form(self, questions, data=None, initial=None):
        return QuestionsForm(
            data=data,
            form_questions=[FormQuestion(q, True) for q in questions],
            initial=initial,
        )

    def test_sections_follow_category_order_with_other_last(self):
        form = self.make_form(
            [
                text_question("misc", QuestionCategory.GENERAL),
                text_question("title", QuestionCategory.RESEARCH_PROJECT),
                text_question("email", QuestionCategory.CONTACT),
                text_question("question", QuestionCategory.RESEARCH_PROJECT),
            ]
        )

        self.assertEqual(
            [(s.category, [f.name for f in s.fields]) for s in form.sections],
            [
                ("contact_details", ["email"]),
                ("research_project", ["title", "question"]),
                ("general", ["misc"]),
            ],
        )
        self.assertEqual(form.sections[-1].label, "Other")
        self.assertEqual(form.sections[0].label, "Contact details")

    def test_unknown_category_is_shown_under_other(self):
        form = self.make_form(
            [
                text_question("email", QuestionCategory.CONTACT),
                text_question("legacy", "no_such_category"),
            ]
        )

        self.assertEqual(
            [(s.category, [f.name for f in s.fields]) for s in form.sections],
            [("contact_details", ["email"]), ("general", ["legacy"])],
        )

    def test_every_category_has_section_meta(self):
        self.assertEqual(set(SECTION_META), set(QuestionCategory))

    def test_sections_link_their_neighbours(self):
        form = self.make_form(
            [
                text_question("email", QuestionCategory.CONTACT),
                text_question("title", QuestionCategory.RESEARCH_PROJECT),
                text_question("terms", QuestionCategory.LEGAL),
            ]
        )
        first, middle, last = form.sections

        self.assertIsNone(first.previous)
        self.assertIs(first.next, middle)
        self.assertIs(middle.previous, first)
        self.assertIs(middle.next, last)
        self.assertIsNone(last.next)

    def test_section_counts_answered_fields(self):
        form = self.make_form(
            [
                text_question("email", QuestionCategory.CONTACT),
                text_question("phone", QuestionCategory.CONTACT),
                text_question("name", QuestionCategory.CONTACT),
            ],
            initial={"email": "a@example.org", "phone": "  "},
        )
        (section,) = form.sections

        self.assertEqual((section.answered, section.total), (1, 3))
        self.assertFalse(section.complete)

    def test_initial_section_is_the_first_with_errors(self):
        questions = [
            text_question("email", QuestionCategory.CONTACT),
            text_question("title", QuestionCategory.RESEARCH_PROJECT),
        ]
        unbound = self.make_form(questions)
        invalid = self.make_form(questions, data={"email": "a@example.org"})
        invalid.is_valid()

        self.assertEqual(unbound.initial_section, "contact_details")
        self.assertEqual(invalid.initial_section, "research_project")
        self.assertTrue(invalid.sections[1].has_errors)


class QuestionFieldComponentTests(SimpleTestCase):
    def test_yes_no_selection_becomes_yes_no_field(self):
        yes_no = DsaQuestionFactory.build(
            input_type=InputType.SELECTION,
            config={"type": "selection", "options": ["Yes", "No"]},
        )
        other = DsaQuestionFactory.build(
            input_type=InputType.SELECTION,
            config={"type": "selection", "options": ["Yes", "No", "Maybe"]},
        )

        self.assertIsInstance(get_question_field(yes_no), YesNoField)
        self.assertNotIsInstance(get_question_field(other), YesNoField)

    def test_yes_no_selection_is_detected_in_any_order(self):
        no_yes = DsaQuestionFactory.build(
            input_type=InputType.SELECTION,
            config={"type": "selection", "options": ["No", "Yes"]},
        )

        self.assertIsInstance(get_question_field(no_yes), YesNoField)

    def test_yes_no_field_keeps_yes_no_answers_from_the_toggle(self):
        field = YesNoField()

        self.assertEqual(field.clean("true"), "Yes")
        self.assertEqual(field.clean("false"), "No")
        self.assertEqual(field.clean("Yes"), "Yes")
        with self.assertRaises(ValidationError):
            field.clean("maybe")

    def test_selection_without_options_falls_back_to_text(self):
        for input_type in (InputType.SELECTION, InputType.MULTI_SELECT):
            question = DsaQuestionFactory.build(
                key="research-keywords", input_type=input_type, config=None
            )
            with (
                self.subTest(input_type=input_type),
                self.assertLogs("idat.dsa40_wizard.forms", "WARNING") as logs,
            ):
                form = QuestionsForm(form_questions=[FormQuestion(question, True)])

                self.assertIs(type(form.fields["research-keywords"]), forms.CharField)
                self.assertEqual(form["research-keywords"].component, "text")
                self.assertIn("research-keywords", logs.output[0])

    def test_bound_fields_name_their_component(self):
        questions = [
            DsaQuestionFactory.build(key="name", input_type=InputType.TEXT),
            DsaQuestionFactory.build(key="country", input_type=InputType.ISO_3166_1),
            DsaQuestionFactory.build(key="cv", input_type=InputType.FILE_UPLOAD),
            DsaQuestionFactory.build(key="start", input_type=InputType.DATE_SELECT),
            DsaQuestionFactory.build(
                key="role",
                input_type=InputType.SELECTION,
                config={"type": "selection", "options": ["PI", "Co-PI"]},
            ),
            DsaQuestionFactory.build(
                key="risks",
                input_type=InputType.MULTI_SELECT,
                config={"type": "selection", "options": ["A", "B"]},
            ),
            DsaQuestionFactory.build(
                key="ethics",
                input_type=InputType.SELECTION,
                config={"type": "selection", "options": ["Yes", "No"]},
            ),
        ]
        form = QuestionsForm(form_questions=[FormQuestion(q, True) for q in questions])

        self.assertEqual(
            {f.name: f.component for f in form},
            {
                "name": "text",
                "country": "country",
                "cv": "file",
                "start": "date",
                "role": "select",
                "risks": "multi-select",
                "ethics": "yes-no",
            },
        )
