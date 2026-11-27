from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus

import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from idat.dsa40_applications.models import (
    AccessApplication,
    AccessCase,
    CaseStatusEvent,
    VersionedUploadedFile,
    VLOPSEAnswer,
)
from idat.dsa40_applications.tests.factories import (
    AccessCaseFactory,
    ResearchProjectFactory,
)
from idat.dsa40_applications.views import (
    AccessCaseOverview,
    ProjectOverview,
)
from idat.dsa40_form_handler.models import InputType
from idat.dsa40_form_handler.tests.factories import VlopseQuestionFactory
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


# TODO: Maybe refactor to a factory (onces the File model has settled)
def upload_case_file(
    case: AccessCase, key: str, name: str, versions: int = 1
) -> list[VersionedUploadedFile]:
    """Uploads ``versions`` versions of a file to a file question of the case."""
    answer = VLOPSEAnswer.objects.create(
        application=AccessApplication.objects.get_or_create(access_case=case)[0],
        question=VlopseQuestionFactory.create(
            key=key, vlopse=case.vlopse, input_type=InputType.FILE_UPLOAD
        ),
    )
    return [
        VersionedUploadedFile.objects.create(
            vlopse_answer=answer,
            name=name,
            creator=case.project.owner,
            version=version,
            project=case.project,
            data=f"%PDF-1.4 v{version}".encode(),
        )
        for version in range(1, versions + 1)
    ]


def document_download_url() -> tuple[str, object]:
    case = AccessCaseFactory.create()
    (document,) = upload_case_file(case, "TEST-DOWNLOAD", "Ethics approval.pdf")
    return (
        reverse("dsa40_applications:document_download", args=[document.pk]),
        case.project.owner,
    )


@pytest.mark.parametrize(
    "make_url", [project_overview_url, case_overview_url, document_download_url]
)
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

    def test_lists_only_the_cases_status_events_oldest_first(self, client) -> None:
        case = AccessCaseFactory.create()  # registers its own draft event
        AccessCaseFactory.create()  # another case's draft event
        now = timezone.now()
        later = CaseStatusEvent.objects.create(
            access_case=case,
            status=CaseStatusEvent.State.GRANTED,
            registered_at=now + timedelta(days=2),
        )
        earlier = CaseStatusEvent.objects.create(
            access_case=case,
            status=CaseStatusEvent.State.SUBMITTED,
            registered_at=now + timedelta(days=1),
        )
        client.force_login(case.project.owner)

        response = client.get(
            reverse("dsa40_applications:case_overview", args=[case.pk])
        )

        assert response.context["status_events"] == [
            case.case_states.get(status=CaseStatusEvent.State.DRAFT),
            earlier,
            later,
        ]

    def test_lists_the_application_versions_newest_first(self, client) -> None:
        case = AccessCaseFactory.create()
        first = AccessApplication.objects.create(access_case=case)
        second = AccessApplication.objects.create(access_case=case)
        AccessApplication.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )
        client.force_login(case.project.owner)

        response = client.get(
            reverse("dsa40_applications:case_overview", args=[case.pk])
        )

        assert list(response.context["case_applications"]) == [second, first]

    def test_lists_the_newest_version_of_each_case_document(self, client) -> None:
        case = AccessCaseFactory.create()
        other_case = AccessCaseFactory.create(project=case.project)
        ethics_v1, ethics_v2 = upload_case_file(
            case, "TEST-DOC-1", "Ethics approval.pdf", versions=2
        )
        (agreement,) = upload_case_file(case, "TEST-DOC-2", "Data use agreement.pdf")
        upload_case_file(other_case, "TEST-DOC-3", "Other platform.pdf")
        client.force_login(case.project.owner)

        response = client.get(
            reverse("dsa40_applications:case_overview", args=[case.pk])
        )

        documents = response.context["case_files"]
        assert documents == [agreement, ethics_v2]
        assert [d.history for d in documents] == [[agreement], [ethics_v2, ethics_v1]]


class TestDocumentDownload:
    def test_sends_the_version_as_attachment(self, client) -> None:
        case = AccessCaseFactory.create()
        v1, _v2 = upload_case_file(
            case, "TEST-DOWNLOAD", "Ethics approval.pdf", versions=2
        )
        client.force_login(case.project.owner)

        response = client.get(
            reverse("dsa40_applications:document_download", args=[v1.pk])
        )

        assert response.status_code == HTTPStatus.OK
        assert b"".join(response.streaming_content) == b"%PDF-1.4 v1"
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"].startswith("attachment;")


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
