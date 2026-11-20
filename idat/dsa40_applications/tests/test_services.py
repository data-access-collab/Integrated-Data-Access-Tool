from __future__ import annotations

import pytest
from django.test import TestCase

from idat.dsa40_applications.services import create_research_project
from idat.dsa40_form_handler.models import DSAQuestion, InputType, VLOPSEQuestion
from idat.dsa40_form_handler.tests.factories import (
    DsaQuestionFactory,
    VlopseQuestionFactory,
)
from idat.dsa40_wizard.state import WizardState
from idat.users.tests.factories import UserFactory
from idat.vlopse.models import Vlopse
from idat.vlopse.tests.factories import VlopseFactory


class CreateAccessApplicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        VLOPSEQuestion.objects.all().delete()
        DSAQuestion.objects.all().delete()
        Vlopse.objects.all().delete()
        cls.user = UserFactory.create()
        cls.mastodon = VlopseFactory.create(name="Mastodon")
        cls.tiktok = VlopseFactory.create(name="TikTok")
        DsaQuestionFactory.create(key="email", input_type=InputType.TEXT, config=None)
        DsaQuestionFactory.create(key="title", input_type=InputType.TEXT, config=None)
        VlopseQuestionFactory.create(
            key="mastodon-email",
            input_type=InputType.TEXT,
            config=None,
            vlopse=cls.mastodon,
        )

    def state(self, **kwargs) -> WizardState:
        return WizardState(
            wizard_id="draft-1",
            vlopses=[self.mastodon.pk, self.tiktok.pk],
            answers=kwargs.get(
                "answers",
                {
                    "email": "a@x.org",
                    "title": "wizard",
                    "mastodon-email": "mastodon@x.org",
                },
            ),
        )

    @pytest.mark.skip(reason="Not implemented yet")
    def test_stores_platforms_answered_questions_overrides(self):
        project = create_research_project(
            self.user,
            self.state(),
        )
        assert project.owner == self.user
        assert [
            p.vlopse.name for p in project.applications.order_by("vlopse__name")
        ] == ["Mastodon", "TikTok"]

        shared = {a.key: a.value for a in project.answers.all()}
        assert shared == {"email": "a@x.org", "title": "wizard"}

        mastodon_application = project.applications.get(vlopse=self.mastodon)
        mastodon_answers = {
            answer.key: answer.value for answer in mastodon_application.answers
        }
        assert mastodon_answers == {
            "mastodon-email": "mastodon@x.org",
            "mastodon-title": "wizard",
        }
