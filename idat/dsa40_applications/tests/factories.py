from __future__ import annotations

from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from idat.dsa40_applications.models import AccessCase, ResearchProject
from idat.users.tests.factories import UserFactory
from idat.vlopse.tests.factories import VlopseFactory


class ResearchProjectFactory(DjangoModelFactory[ResearchProject]):
    title = Faker("sentence")
    owner = SubFactory(UserFactory)

    class Meta:
        model = ResearchProject
        skip_postgeneration_save = True


class AccessCaseFactory(DjangoModelFactory[AccessCase]):
    project = SubFactory(ResearchProjectFactory)
    vlopse = SubFactory(VlopseFactory)

    class Meta:
        model = AccessCase
        skip_postgeneration_save = True
