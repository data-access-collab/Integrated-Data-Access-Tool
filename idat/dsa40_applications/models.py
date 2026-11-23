"""A submitted DSA40 Research Project: what the wizard's draft becomes once a
logged-in user submits it."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from idat.vlopse.models import Vlopse

if TYPE_CHECKING:
    from django.db.models import QuerySet


class ResearchProject(models.Model):
    """A research project applying for data access in multiple cases.
    platforms (PlatformApplication). DSA Question answers are stored here."""

    title = models.TextField(blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    class Meta:
        verbose_name = "DSA40 Research Project"

    def __str__(self) -> str:
        return f"{self.title}"

    answers: QuerySet[ProjectAnswer]
    access_cases: QuerySet[AccessCase]


class ApplicationState(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready"
    SUBMITTED = "submitted", "Submitted"


class AccessCase(models.Model):
    """The access case of a research project with one or more platforms
    targeted"""

    state = models.CharField(
        max_length=16,
        choices=ApplicationState,
        default=ApplicationState.DRAFT,
    )
    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.PROTECT,
        related_name="access_cases",
    )
    vlopse = models.ForeignKey(Vlopse, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("AccessCase")
        ordering: ClassVar = ["vlopse__name"]
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["project", "vlopse"],
                name="unique_platform_per_project",
            )
        ]

    def __str__(self) -> str:
        return f"Case: {self.project.title}"


class AccessApplication(models.Model):
    """The application to one platform (VLOPSE) within a project."""

    copied_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="copies"
    )
    access_case = models.OneToOneField(AccessCase, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(null=True, blank=True)

    answers: QuerySet[PlatformSpecificAnswer]

    def __str__(self) -> str:
        return f"{self.vlopse} ({self.project.title})"

    @property
    def state(self) -> ApplicationState:
        return self.access_case.state

    @property
    def project(self) -> ResearchProject:
        return self.access_case.project

    @property
    def vlopse(self) -> Vlopse:
        return self.access_case.vlopse

    @property
    def is_editable_in_place(self) -> bool:
        return self.state != ApplicationState.SUBMITTED

    def copy_as_draft(self) -> AccessApplication:
        # TODO: COPY from Application
        new = AccessApplication.objects.create(
            application=self.project,
            state=ApplicationState.DRAFT,
            copied_from=self,
        )
        PlatformSpecificAnswer.objects.bulk_create(
            PlatformSpecificAnswer(application=new, key=a.key, value=a.value)
            for a in self.answers.all()
        )
        return new


class BaseAnswer(models.Model):
    key = models.CharField(max_length=16, db_index=True)
    value = models.JSONField(null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.key}={self.value}"


class ProjectAnswer(BaseAnswer):
    project = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="answers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "key"],
                name="unique_answer_per_project_question",
            )
        ]


class PlatformSpecificAnswer(BaseAnswer):
    application = models.ForeignKey(
        AccessApplication, on_delete=models.CASCADE, related_name="answers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "key"],
                name="unique_answer_per_application_question",
            )
        ]
