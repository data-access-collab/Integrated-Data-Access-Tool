from __future__ import annotations

from factory import Faker, fuzzy
from factory.django import DjangoModelFactory

from idat.dsa40.models import DSAQuestion, InputType, Vlopse, VLOPSEQuestion


class VlopseFactory(DjangoModelFactory[Vlopse]):
    name = Faker("name")
    platform_information = Faker("paragraph")
    account_required = Faker("pybool")
    application_link = Faker("url")
    modality = fuzzy.FuzzyChoice(Vlopse.ApplicationModality.values)

    class Meta:
        model = Vlopse
        skip_postgeneration_save = True


class VlopseQuestionFactory(DjangoModelFactory[VLOPSEQuestion]):
    id = Faker("word")
    text = Faker("sentence")
    required = Faker("pybool")
    input_type = fuzzy.FuzzyChoice(InputType.values)
    details = Faker("paragraph")

    class Meta:
        model = VLOPSEQuestion
        skip_postgeneration_save = True


class DsaQuestionFactory(DjangoModelFactory[DSAQuestion]):
    id = Faker("word")
    text = Faker("sentence")
    help_text = Faker("paragraph")
    input_type = fuzzy.FuzzyChoice(InputType.values)

    class Meta:
        model = DSAQuestion
        skip_postgeneration_save = True
