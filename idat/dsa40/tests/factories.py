from __future__ import annotations

from factory import Faker, fuzzy
from factory.django import DjangoModelFactory

from idat.dsa40.models import DSAQuestion, InputType, VLOPSEQuestion


class VlopseQuestionFactory(DjangoModelFactory[VLOPSEQuestion]):
    key = Faker("word")
    text = Faker("sentence")
    required = Faker("pybool")
    input_type = fuzzy.FuzzyChoice(InputType.values)
    details = Faker("paragraph")

    class Meta:
        model = VLOPSEQuestion
        skip_postgeneration_save = True


class DsaQuestionFactory(DjangoModelFactory[DSAQuestion]):
    key = Faker("word")
    text = Faker("sentence")
    help_text = Faker("paragraph")
    input_type = fuzzy.FuzzyChoice(InputType.values)

    class Meta:
        model = DSAQuestion
        skip_postgeneration_save = True
