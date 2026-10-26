from __future__ import annotations

from factory import Faker, fuzzy
from factory.django import DjangoModelFactory

from idat.vlopse.models import Vlopse


class VlopseFactory(DjangoModelFactory[Vlopse]):
    name = Faker("name")
    platform_information = Faker("paragraph")
    account_required = Faker("pybool")
    application_link = Faker("url")
    modality = fuzzy.FuzzyChoice(Vlopse.ApplicationModality.values)

    class Meta:
        model = Vlopse
        skip_postgeneration_save = True
