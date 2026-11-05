# ruff: noqa: E501
import json
from typing import TYPE_CHECKING

import pytest

from idat.conftest import api_prefix
from idat.dsa40_form_handler.tests.factories import VlopseQuestionFactory
from idat.vlopse.tests.factories import VlopseFactory

if TYPE_CHECKING:
    from django.test import Client

    from idat.dsa40_form_handler.models import VLOPSEQuestion
    from idat.vlopse.models import Vlopse


@pytest.fixture
def vlopse() -> Vlopse:
    return VlopseFactory.create()


@pytest.fixture
def vlopse_question(vlopse: Vlopse) -> VLOPSEQuestion:
    return VlopseQuestionFactory.create(vlopse=vlopse)


@pytest.mark.django_db
def test_list_vlopse_questions(client: Client, vlopse: Vlopse):
    question = VlopseQuestionFactory.create(vlopse=vlopse)
    response = client.get(
        f"{api_prefix}/vlopse/{vlopse.name}/question",
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "key": question.key,
            "text": question.text,
            "vlopse": question.vlopse.name,
            "required": question.required,
            "input_type": question.input_type,
            "details": question.details,
            "config": question.config,
        },
    ]


@pytest.mark.django_db
def test_get_single_vlopse_question(client: Client, vlopse_question: VLOPSEQuestion):

    response = client.get(
        f"{api_prefix}/vlopse/{vlopse_question.vlopse.name}/question/{vlopse_question.key}"
    )
    assert response.status_code == 200
    assert response.json() == {
        "key": vlopse_question.key,
        "text": vlopse_question.text,
        "vlopse": vlopse_question.vlopse.name,
        "required": vlopse_question.required,
        "input_type": vlopse_question.input_type,
        "details": vlopse_question.details,
        "config": vlopse_question.config,
    }


def boolean_selection():
    return {
        "key": "test_1",
        "text": "Are you affiliated with an academic institution?",
        "required": True,
        "input_type": "selection",
        "config": {"type": "selection", "options": ["Yes", "No"]},
        "details": "",
    }


def selection(key: str):
    return {
        "key": key,
        "text": """Are you affiliated with an academic institution or a not-for-profit body, organisation or association whose principal aim is to conduct research on a not-for-profit basis pursuant to a public-interest mission?""",
        "required": "true",
        "input_type": "selection",
        "config": {
            "type": "selection",
            "options": [
                "Academic institution",
                "Not-for-profit body, organization or association (based in the EU 27 Member States only)",
            ],
        },
    }


@pytest.mark.django_db
def test_create_vlopse_question(client: Client, vlopse: Vlopse):
    body = boolean_selection()
    response = client.post(
        f"{api_prefix}/vlopse/{vlopse.name}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


@pytest.mark.django_db
def test_get_nonexistent_vlopse_question(client: Client, vlopse: Vlopse):
    response = client.get(f"{api_prefix}/vlopse/{vlopse.name}/question/does-not-exist")
    assert response.status_code == 404


@pytest.mark.skip(reason="#35 Not implemented yet")
@pytest.mark.django_db
def test_create_duplicate_vlopse_question_conflicts(
    client: Client, vlopse_question: VLOPSEQuestion
):
    body = {
        "key": vlopse_question.key,
        "text": vlopse_question.text,
        "required": vlopse_question.required,
        "input_type": vlopse_question.input_type,
        "details": vlopse_question.details,
        "config": vlopse_question.config,
    }

    response = client.post(
        f"{api_prefix}/vlopse/{vlopse_question.vlopse.name}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_create_vlopse_question_malformed_body(client: Client, vlopse: Vlopse):
    body = {"id": "x"}
    response = client.post(
        f"{api_prefix}/vlopse/{vlopse.name}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 422


@pytest.mark.django_db
def test_adding_vlopse_selection_question(client: Client, vlopse: Vlopse):
    question_key = "test_key"
    body = selection(question_key)
    response = client.post(
        f"{api_prefix}/vlopse/{vlopse.name}/question",
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 200
    response = client.get(f"{api_prefix}/vlopse/{vlopse.name}/question/{question_key}")
    assert response.status_code == 200
    question = response.json()
    assert question["key"] == question_key
