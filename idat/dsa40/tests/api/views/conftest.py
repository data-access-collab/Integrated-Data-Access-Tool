import uuid

import pytest


@pytest.fixture
def unique_id() -> str:
    return str(uuid.uuid4())
