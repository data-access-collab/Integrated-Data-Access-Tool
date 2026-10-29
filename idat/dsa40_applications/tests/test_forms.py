from __future__ import annotations

import json
import re
from html import unescape

from django import forms
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils.html import escape

from idat.dsa40.models import InputType
from idat.dsa40.tests.factories import DsaQuestionFactory
from idat.dsa40_applications.forms import (
    DEFAULT_CLIENT_FILE_TYPES,
    ClientFileField,
    QuestionsForm,
)


class QuestionsFormTests(SimpleTestCase):
    def test_questions_form_requires_only_required_questions(self):
        required = DsaQuestionFactory.build(key="email", input_type=InputType.TEXT)
        optional = DsaQuestionFactory.build(key="nickname", input_type=InputType.TEXT)
        config = [(True, required), (False, optional)]

        with_required = QuestionsForm(
            data={"email": "a@example.org"}, question_config=config, answers={}
        )
        without_required = QuestionsForm(
            data={"nickname": "ada"}, question_config=config, answers={}
        )

        self.assertTrue(with_required.is_valid())
        self.assertFalse(without_required.is_valid())
        self.assertIn("email", without_required.errors)

    def test_questions_form_prefills_stored_answers(self):
        question = DsaQuestionFactory.build(key="email", input_type=InputType.TEXT)

        form = QuestionsForm(
            question_config=[(True, question)], answers={"email": "a@example.org"}
        )

        self.assertEqual(form["email"].value(), "a@example.org")

    def test_selection_question_accepts_flat_option_list(self):
        question = DsaQuestionFactory.build(
            key="prev-experience",
            input_type=InputType.SELECTION,
            config={"type": "selection", "options": ["Yes", "No"]},
        )
        config = [(True, question)]

        valid = QuestionsForm(
            data={"prev-experience": "No"}, question_config=config, answers={}
        )
        invalid = QuestionsForm(
            data={"prev-experience": "Maybe"}, question_config=config, answers={}
        )

        self.assertTrue(valid.is_valid())
        self.assertFalse(invalid.is_valid())


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
            question_config=[(True, question)], answers={"cv": self.file_meta()}
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
