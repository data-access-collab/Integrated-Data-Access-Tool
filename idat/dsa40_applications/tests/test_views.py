from __future__ import annotations

from http import HTTPStatus

import pytest
from django.test import RequestFactory
from django.urls import reverse

from idat.dsa40_applications.models import AccessCase
from idat.dsa40_applications.tests.factories import (
    AccessCaseFactory,
    ResearchProjectFactory,
)
from idat.dsa40_applications.views import (
    AccessCaseOverview,
    ProjectOverview,
)
from idat.users.tests.factories import UserFactory
from idat.vlopse.tests.factories import VlopseFactory

pytestmark = pytest.mark.django_db


def project_overview_url() -> tuple[str, object]:
    project = ResearchProjectFactory.create()
    return (
        reverse("dsa40_applications:project_overview", args=[project.pk]),
        project.owner,
    )


def case_overview_url() -> tuple[str, object]:
    case = AccessCaseFactory.create()
    return (
        reverse("dsa40_applications:case_overview", args=[case.pk]),
        case.project.owner,
    )


@pytest.mark.parametrize("make_url", [project_overview_url, case_overview_url])
class TestProjectOwnerRequired:
    """Each view builds its URL and returns (url, project owner)."""

    def test_owner_gets_the_page(self, client, make_url) -> None:
        url, owner = make_url()
        client.force_login(owner)

        assert client.get(url).status_code == HTTPStatus.OK

    def test_superuser_gets_any_page(self, client, make_url) -> None:
        url, _owner = make_url()
        client.force_login(UserFactory.create(is_superuser=True))

        assert client.get(url).status_code == HTTPStatus.OK

    def test_other_user_gets_404(self, client, make_url) -> None:
        url, _owner = make_url()
        client.force_login(UserFactory.create())

        assert client.get(url).status_code == HTTPStatus.NOT_FOUND

    def test_anonymous_is_sent_to_login(self, client, make_url) -> None:
        url, _owner = make_url()

        response = client.get(url)

        assert response.status_code == HTTPStatus.FOUND
        assert response.url.startswith(reverse("account_login"))


class TestProjectOverview:
    def test_renders_project(self, client) -> None:
        project = ResearchProjectFactory.create()
        client.force_login(project.owner)

        response = client.get(
            reverse("dsa40_applications:project_overview", args=[project.pk])
        )

        assert response.status_code == HTTPStatus.OK
        assert response.context["project"] == project
        assert response.context["case_states"] is AccessCase.State

    def test_lists_only_the_projects_cases_by_platform_name(self, client) -> None:
        project = ResearchProjectFactory.create()
        zeta = AccessCaseFactory.create(
            project=project, vlopse=VlopseFactory.create(name="Zeta test platform")
        )
        alpha = AccessCaseFactory.create(
            project=project, vlopse=VlopseFactory.create(name="Alpha test platform")
        )
        AccessCaseFactory.create()  # another project's case
        client.force_login(project.owner)

        response = client.get(
            reverse("dsa40_applications:project_overview", args=[project.pk])
        )

        assert list(response.context["cases"]) == [alpha, zeta]

    def test_unknown_project_is_404(self, client, user) -> None:
        client.force_login(user)

        response = client.get(
            reverse("dsa40_applications:project_overview", args=[999_999])
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestAccessCaseOverview:
    def test_renders_case(self, client) -> None:
        case = AccessCaseFactory.create()
        client.force_login(case.project.owner)

        response = client.get(
            reverse("dsa40_applications:case_overview", args=[case.pk])
        )

        assert response.status_code == HTTPStatus.OK
        assert response.context["case"] == case

    def test_unknown_case_is_404(self, client, user) -> None:
        client.force_login(user)

        response = client.get(
            reverse("dsa40_applications:case_overview", args=[999_999])
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


def owned_project() -> list:
    return [ResearchProjectFactory.create()]


def owned_cases() -> list:
    project = ResearchProjectFactory.create()
    return AccessCaseFactory.create_batch(2, project=project)


def owner_of(obj: object) -> object:
    if isinstance(obj, AccessCase):
        return obj.project.owner
    return obj.owner


@pytest.mark.parametrize(
    ("view_class", "make_objects"),
    [
        (ProjectOverview, owned_project),
        (AccessCaseOverview, owned_cases),
    ],
)
class TestProjectOwnerLookup:
    """get_queryset filters by the view's project_owner_lookup."""

    def get_queryset(self, view_class, user) -> list:
        request = RequestFactory().get("/")
        request.user = user
        view = view_class()
        view.setup(request)
        return list(view.get_queryset())

    def test_returns_only_the_owners_objects(self, view_class, make_objects) -> None:
        own = make_objects()
        others = make_objects()

        queryset = self.get_queryset(view_class, owner_of(own[0]))

        assert set(queryset) == set(own)
        assert not set(queryset) & set(others)

    def test_superuser_gets_all_objects(self, view_class, make_objects) -> None:
        objects = make_objects() + make_objects()

        queryset = self.get_queryset(view_class, UserFactory.create(is_superuser=True))

        assert set(queryset) == set(objects)
