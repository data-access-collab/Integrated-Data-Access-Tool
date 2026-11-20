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
    """Container object for access cases for one or more
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
    applications: QuerySet[PlatformApplication]


class PlatformApplication(models.Model):
    """The application to one platform (VLOPSE) within a project."""

    # The application wording is more from the user side while case seems
    # to be the Weizenbaums perspective but they mean the same object?
    # Each duplicate created by copied_from builds an application but they
    # all refer to the same case. Unsure if it warrents a seaprate object in between

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        SUBMITTED = "submitted", "Submitted"

    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)

    vlopse = models.ForeignKey(
        Vlopse, on_delete=models.PROTECT, related_name="platform_applications"
    )
    copied_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="copies"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    answers: QuerySet[PlatformSpecificAnswer]

    class Meta:
        verbose_name = _("Application")
        ordering: ClassVar = ["project", "vlopse__name"]
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["project", "vlopse"],
                name="unique_platform_per_project",
            )
        ]

    def __str__(self) -> str:
        return f"{self.vlopse} ({self.project.title})"

    @property
    def is_editable_in_place(self) -> bool:
        return self.state != self.State.SUBMITTED

    def copy_as_draft(self) -> PlatformApplication:
        # TODO: COPY from Application
        new = PlatformApplication.objects.create(
            application=self.project,
            state=self.State.DRAFT,
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
        PlatformApplication, on_delete=models.CASCADE, related_name="answers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "key"],
                name="unique_answer_per_application_question",
            )
        ]
