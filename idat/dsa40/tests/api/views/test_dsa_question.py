import json
from typing import TYPE_CHECKING

import pytest

from idat.dsa40.tests.api.test_views import api_prefix
from idat.dsa40.tests.factories import DsaQuestionFactory, VlopseFactory

if TYPE_CHECKING:
    from django.test import Client

    from idat.dsa40.models import DSAQuestion, Vlopse


@pytest.fixture
def vlopse() -> Vlopse:
    return VlopseFactory.create()


@pytest.fixture
def dsa_question() -> DSAQuestion:
    return DsaQuestionFactory.create()


@pytest.mark.django_db
def test_list_dsa_questions(client: Client):
    question = DsaQuestionFactory.create()
    response = client.get(
        f"{api_prefix}/question",
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": question.id,
            "text": question.text,
            "help_text": question.help_text,
            "input_type": question.input_type,
            "config": question.config,
        },
    ]


@pytest.mark.django_db
def test_get_single_dsa_question(client: Client, dsa_question: DSAQuestion):

    response = client.get(f"{api_prefix}/question/{dsa_question.id}")
    assert response.status_code == 200
    assert response.json() == {
        "id": dsa_question.id,
        "text": dsa_question.text,
        "help_text": dsa_question.help_text,
        "input_type": dsa_question.input_type,
        "config": dsa_question.config,
    }


@pytest.mark.django_db
def test_create_dsa_question(client: Client):
    body = {
        "id": "U1",
        "text": "Are you affiliated with an academic institution?",
        "input_type": "selection",
        "config": {"type": "selection", "options": ["Yes", "No"]},
        "help_text": "Select an academic institution that you're affiliated with",
    }
    response = client.post(
        f"{api_prefix}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


@pytest.mark.django_db
def test_get_nonexistent_dsa_question(client: Client):
    response = client.get(f"{api_prefix}/question/does-not-exist")
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.skip(reason="Not implemented yet")
def test_create_duplicate_dsa_question_conflicts(
    client: Client, dsa_question: DSAQuestion
):
    body = {
        "id": dsa_question.id,
        "text": dsa_question.text,
        "help_text": dsa_question.help_text,
        "input_type": dsa_question.input_type,
        "config": dsa_question.config,
    }
    response = client.post(
        f"{api_prefix}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_create_dsa_question_malformed_body(client: Client):
    body = {"id": "x"}
    response = client.post(
        f"{api_prefix}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 422
