from __future__ import annotations

from factory import Faker, SubFactory, fuzzy
from factory.django import DjangoModelFactory

from idat.dsa40_applications.models import (
    AccessApplication,
    AccessCase,
    ApplicationState,
    PlatformSpecificAnswer,
    ProjectAnswer,
    ResearchProject,
)
from idat.users.tests.factories import UserFactory
from idat.vlopse.tests.factories import VlopseFactory


class ResearchProjectFactory(DjangoModelFactory[ResearchProject]):
    title = Faker("word")
    owner = SubFactory(UserFactory)

    class Meta:
        model = ResearchProject


class AccessCaseFactory(DjangoModelFactory[AccessCase]):
    project = SubFactory(ResearchProjectFactory)
    state = fuzzy.FuzzyChoice(ApplicationState.values)
    vlopse = SubFactory(VlopseFactory)

    class Meta:
        model = AccessCase


class AccessApplicationFactory(DjangoModelFactory[AccessApplication]):
    access_case = SubFactory(AccessCaseFactory)
    submitted_at = Faker("date_time")

    class Meta:
        model = AccessApplication


class ProjectAnswerFactory(DjangoModelFactory[ProjectAnswer]):
    project = SubFactory(ResearchProjectFactory)

    class Meta:
        model = ProjectAnswer


class PlatformSpecificAnswerFactory(DjangoModelFactory[PlatformSpecificAnswer]):
    application = SubFactory(AccessApplicationFactory)

    class Meta:
        model = PlatformSpecificAnswer
