from __future__ import annotations

from django.db import IntegrityError
from django.test import TestCase

from idat.dsa40_applications.tests.factories import (
    AccessApplicationFactory,
    AccessCaseFactory,
    PlatformSpecificAnswerFactory,
    ProjectAnswerFactory,
    ResearchProjectFactory,
)
from idat.dsa40_form_handler.tests.factories import DsaQuestionFactory


class AnswerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = ResearchProjectFactory.create()
        cls.question = DsaQuestionFactory.create(key="test-email", config=None)
        cls.application = AccessApplicationFactory.create()
        cls.access_case = AccessCaseFactory.create()

    def test_unique_project_answer_key_per_project(self):
        ProjectAnswerFactory.create(project=self.project, key=self.question.key)
        with self.assertRaises(IntegrityError):
            ProjectAnswerFactory.create(project=self.project, key=self.question.key)

    def test_multiple_platform_answers_per_project(self):
        PlatformSpecificAnswerFactory.create(application=self.application, key="key")

        case_b = AccessCaseFactory.create()
        application_b = AccessApplicationFactory.create(access_case=case_b)
        PlatformSpecificAnswerFactory.create(application=application_b, key="key")


class AccessCaseTest(TestCase):
    def test_platform_only_once_per_case_in_project(self):
        case = AccessCaseFactory.create()

        with self.assertRaises(IntegrityError):
            AccessCaseFactory.create(vlopse=case.vlopse, project=case.project)
