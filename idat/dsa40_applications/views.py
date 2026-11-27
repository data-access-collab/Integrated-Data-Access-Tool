from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.detail import DetailView

from idat.dsa40_applications.models import AccessCase, ResearchProject

if TYPE_CHECKING:
    from django.db.models import QuerySet


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
