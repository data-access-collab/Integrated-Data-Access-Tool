from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from idat.dsa40_form_handler.tests.factories import (
    DsaQuestionFactory,
    VlopseQuestionFactory,
)
from idat.users.tests.factories import UserFactory
from idat.vlopse.tests.factories import VlopseFactory

if TYPE_CHECKING:
    from idat.dsa40_form_handler.models import DSAQuestion, VLOPSEQuestion
    from idat.users.models import User
    from idat.vlopse.models import Vlopse

api_prefix = "/api/v1"


@pytest.fixture
def unique_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:  # noqa: ANN001
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:  # noqa: ANN001
    return UserFactory.create()


@pytest.fixture
def vlopse() -> Vlopse:
    return VlopseFactory.create()


@pytest.fixture
def dsa_question() -> DSAQuestion:
    return DsaQuestionFactory.create()


@pytest.fixture
def vlopse_question() -> VLOPSEQuestion:
    vlopse = VlopseFactory.create()
    return VlopseQuestionFactory.create(vlopse=vlopse)
