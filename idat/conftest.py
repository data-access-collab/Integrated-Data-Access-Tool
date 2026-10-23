from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from idat.dsa40.tests.factories import (
    DsaQuestionFactory,
    VlopseFactory,
    VlopseQuestionFactory,
)
from idat.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from idat.dsa40.models import DSAQuestion, Vlopse, VLOPSEQuestion
    from idat.users.models import User


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
def vlopse_question(vlopse: Vlopse) -> VLOPSEQuestion:
    return VlopseQuestionFactory.create(vlopse=vlopse)
