from __future__ import annotations

import json
from unittest import mock

from django.test import SimpleTestCase, TestCase

from idat.dsa40_applications.services.applications import (
    build_application_preview,
    build_mapping_input,
    to_mapping_input_value,
)
from idat.dsa40_form_handler.models import InputType, VLOPSEQuestion
from idat.dsa40_form_handler.tests.factories import VlopseQuestionFactory
from idat.dsa40_form_handler.validation.config import VLOPSEConfiguration
from idat.vlopse.models import Vlopse
from idat.vlopse.tests.factories import VlopseFactory


class MappingInputTests(SimpleTestCase):
    def test_unanswered_is_none(self):
        for value in (None, "", []):
            with self.subTest(value=value):
                self.assertIsNone(to_mapping_input_value(value, InputType.TEXT))

    def test_country_code_becomes_the_name_make_iso_expects(self):
        self.assertEqual(to_mapping_input_value("DE", InputType.ISO_3166_1), "Germany")

    def test_multi_select_is_joined(self):
        self.assertEqual(
            to_mapping_input_value(["Posts", "Comments"], InputType.MULTI_SELECT),
            "Posts, Comments",
        )

    def test_file_metadata_stays_json(self):
        meta = {"name": "cv.pdf", "size": 1, "type": "application/pdf", "sha256": "a"}
        self.assertEqual(
            json.loads(to_mapping_input_value(meta, InputType.FILE_UPLOAD)), meta
        )

    def test_build_mapping_input_uses_each_questions_input_type(self):
        mapping_input = build_mapping_input(
            {"country": "NL", "title": "Audit"}, {"country": InputType.ISO_3166_1}
        )
        self.assertEqual(
            [(i.question_id, i.value) for i in mapping_input],
            [("country", "Netherlands"), ("title", "Audit")],
        )


CONFIG = VLOPSEConfiguration.model_validate(
    {
        "mappings": {
            "m-name": {"src": ["first-name", "last-name"], "operation": "join-space"},
            "m-country": {"src": "country", "operation": "make-iso"},
        },
        "conditions": {},
    }
)


class BuildApplicationPreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        VLOPSEQuestion.objects.all().delete()
        Vlopse.objects.all().delete()
        cls.vlopse = VlopseFactory.create(name="mastodon")
        for key, text, input_type in [
            ("m-name", "Full name", InputType.TEXT),
            ("m-country", "Country (ISO)", InputType.TEXT),
        ]:
            VlopseQuestionFactory.create(
                key=key, text=text, vlopse=cls.vlopse, input_type=input_type
            )

    def setUp(self):
        self.enterContext(
            mock.patch(
                "idat.dsa40_applications.services.applications.get_vlopse_configuration_for",
                return_value=CONFIG,
            )
        )

    def build(self, answers: dict):
        types = {"country": InputType.ISO_3166_1}
        return build_application_preview(
            self.vlopse, build_mapping_input(answers, types)
        )

    def test_answers_are_transformed_into_the_platforms_questions(self):
        preview = self.build(
            {"first-name": "Pirmin", "last-name": "Passugg", "country": "DE"}
        )

        self.assertEqual(preview.form["m-name"].value(), "Pirmin Passugg")
        self.assertEqual(preview.form["m-country"].value(), "DEU")
        self.assertEqual(preview.mapping_errors, {})

    def test_unusable_answer_is_reported_with_the_question_text(self):
        preview = self.build(
            {"first-name": "Pirmin", "last-name": "Passugg", "country": "XX"}
        )

        self.assertIsNone(preview.form["m-country"].value())
        self.assertEqual(list(preview.mapping_errors), ["Country (ISO)"])

    def test_unanswered_questions_are_empty_not_errors(self):
        preview = self.build({"first-name": None, "last-name": None, "country": None})

        self.assertIsNone(preview.form["m-name"].value())
        self.assertEqual(preview.mapping_errors, {})
