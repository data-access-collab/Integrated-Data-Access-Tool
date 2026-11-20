from __future__ import annotations

from django.db import IntegrityError
from django.test import TestCase

from idat.dsa40_applications.tests.factories import (
    PlatformApplicationFactory,
    PlatformSpecificAnswerFactory,
    ProjectAnswerFactory,
    ResearchProjectFactory,
)
from idat.dsa40_form_handler.tests.factories import DsaQuestionFactory


class AnswerTests(TestCase):
    def setUp(self):
        self.project = ResearchProjectFactory.create()
        self.question = DsaQuestionFactory.create(key="test-email", config=None)
        self.application = PlatformApplicationFactory.create(project=self.project)

    def test_unique_project_answer_key_per_project(self):
        ProjectAnswerFactory.create(project=self.project, key=self.question.key)
        with self.assertRaises(IntegrityError):
            ProjectAnswerFactory.create(project=self.project, key=self.question.key)

    def test_multiple_platform_answers_per_project(self):
        application_a = PlatformApplicationFactory.create(project=self.project)
        application_b = PlatformApplicationFactory.create(project=self.project)
        PlatformSpecificAnswerFactory.create(application=application_a, key="key")
        PlatformSpecificAnswerFactory.create(application=application_b, key="key")


class PlatformApplicationTests(TestCase):
    def test_platform_only_once_per_application(self):
        platform = PlatformApplicationFactory.create()

        with self.assertRaises(IntegrityError):
            PlatformApplicationFactory.create(
                project=platform.project, vlopse=platform.vlopse
            )
