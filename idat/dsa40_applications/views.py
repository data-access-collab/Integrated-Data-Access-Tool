from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import TYPE_CHECKING, Any, ClassVar

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
from django.views import View
from django.views.generic.detail import DetailView, SingleObjectMixin

from idat.dsa40_applications.models import (
    AccessCase,
    ResearchProject,
    VersionedUploadedFile,
)
from idat.dsa40_applications.ui import status_timeline

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


class ProjectOwnerRequiredMixin(LoginRequiredMixin):
    """Limits a model view (DetailView, UpdateView, ListView …) to objects of projects
    the signed-in user owns; superusers see everything.

    Anonymous users are sent to the login page. Objects of other users' projects are
    filtered out of the queryset. If no objects are found, renders 404.

    Set ``project_owner_lookup`` to the ORM path from the view's model to the
    project owner, e.g. ``"owner"`` on ResearchProject, ``"project__owner"`` on
    AccessCase, ``"access_case__project__owner"`` on AccessApplication.
    """

    project_owner_lookup: ClassVar[str] = "project__owner"

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(**{self.project_owner_lookup: self.request.user})


class ProjectOverview(ProjectOwnerRequiredMixin, DetailView):
    model = ResearchProject
    project_owner_lookup = "owner"
    template_name = "dsa40_applications/project/overview.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "cases": self.object.access_cases.all(),
                "case_states": AccessCase.State,
                "shared_answers": [],  # TODO: Add as soon as clarified
                "shared_documents": [],  # TODO: Add as soon as clarified
            }
        )

        return context


class AccessCaseOverview(ProjectOwnerRequiredMixin, DetailView):
    model = AccessCase
    project_owner_lookup = "project__owner"
    template_name = "dsa40_applications/access_case/overview.html"
    context_object_name = "case"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "cases": self.object.project.access_cases.all(),
                "status_events": status_timeline(self.object),
                "case_documents": self.get_case_documents(),
            }
        )
        return context

    def get_case_documents(self) -> list[VersionedUploadedFile]:
        """The newest version of each file uploaded to the case's applications, by
        name; ``document.history`` holds all its versions, newest first."""
        files = (
            VersionedUploadedFile.objects.filter(
                vlopse_answer__application__access_case=self.object
            )
            .select_related("creator")
            .order_by("-version")
        )
        history: defaultdict[int, list[VersionedUploadedFile]] = defaultdict(list)
        for file in files:
            history[file.vlopse_answer_id].append(file)
        documents = []
        for versions in history.values():
            newest = versions[0]
            newest.history = versions
            documents.append(newest)
        return sorted(documents, key=lambda document: document.name)


class DocumentDownload(ProjectOwnerRequiredMixin, SingleObjectMixin, View):
    """Sends one stored file version as an attachment."""

    model = VersionedUploadedFile
    project_owner_lookup = "project__owner"

    def get(self, request: HttpRequest, *args, **kwargs) -> FileResponse:
        document = self.get_object()
        return FileResponse(
            BytesIO(bytes(document.data)),
            as_attachment=True,
            filename=document.name,
        )
