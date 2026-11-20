from __future__ import annotations

from factory import Sequence, SubFactory
from factory.django import DjangoModelFactory

from idat.dsa40_applications.models import (
    PlatformApplication,
    PlatformSpecificAnswer,
    ProjectAnswer,
    ResearchProject,
)
from idat.users.tests.factories import UserFactory
from idat.vlopse.tests.factories import VlopseFactory


class ResearchProjectFactory(DjangoModelFactory[ResearchProject]):
    owner = SubFactory(UserFactory, username=Sequence(lambda n: f"owner-{n}"))

    class Meta:
        model = ResearchProject


class PlatformApplicationFactory(DjangoModelFactory[PlatformApplication]):
    project = SubFactory(ResearchProjectFactory)
    vlopse = SubFactory(VlopseFactory)

    class Meta:
        model = PlatformApplication


class ProjectAnswerFactory(DjangoModelFactory[ProjectAnswer]):
    project = SubFactory(ResearchProjectFactory)

    class Meta:
        model = ProjectAnswer


class PlatformSpecificAnswerFactory(DjangoModelFactory[PlatformSpecificAnswer]):
    application = SubFactory(PlatformApplicationFactory)

    class Meta:
        model = PlatformSpecificAnswer
