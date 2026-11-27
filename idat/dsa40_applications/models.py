"""A submitted DSA40 Research Project: what the wizard's draft becomes once a
logged-in user submits it."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from idat.dsa40_form_handler.models import DSAQuestion, InputType, VLOPSEQuestion
from idat.users.models import User
from idat.vlopse.models import Vlopse

if TYPE_CHECKING:
    from django.db.models import QuerySet


class ResearchProject(models.Model):
    """A research project applying for data access in multiple cases."""

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        RUNNING = "running", "Running"
        DATA_RECEIVED = "data_received", "Data Received"
        INSIGHTS_PUBLISHED = "insights_published", "Insights Published"

    title = models.TextField(blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DSA40 Research Project"

    def __str__(self) -> str:
        return f"{self.title}"

    answers: QuerySet[DSAAnswer]

    access_cases: QuerySet[AccessCase]


class AccessCase(models.Model):
    """An access case related to a specific VLOPSE. Contains one
    application object"""

    class State(models.TextChoices):
        DRAFT = "draft", _("Draft")
        OPEN = "open", _("Open")
        SUBMITTED = "submitted", _("Submitted")

    state = models.CharField(
        max_length=16,
        choices=State,
        default=State.DRAFT,
    )
    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.PROTECT,
        related_name="access_cases",
    )
    vlopse = models.ForeignKey(Vlopse, on_delete=models.PROTECT)

    class Meta:
        ordering: ClassVar = ["vlopse__name"]
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["project", "vlopse"],
                name="unique_vlopse_per_project",
            )
        ]

    def __str__(self) -> str:
        return f"Case {self.vlopse.name} ({self.project.title})"


class AccessApplication(models.Model):
    """The application to one VLOPSE within a research project."""

    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PENDING = "pending", "Pending"
        REQUIRES_RESPONSE = "requires_response", "Requires Response"
        APPEALED = "appealed", "Appealed"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        MODIFICATION_ACCEPTED = "modification_accepted", "Modification Accepted"
        MODIFICATION_REJECTED = "modification_rejected", "Modification Rejected"

    state = models.CharField(
        max_length=32,
        choices=State,
        default=State.DRAFT,
    )

    access_case = models.OneToOneField(AccessCase, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(null=True, blank=True)

    answers: QuerySet[VLOPSEAnswer]

    def __str__(self) -> str:
        return f"AccessApplication[{self.state.value}]({self.access_case.vlopse.name})"

    @property
    def project(self) -> ResearchProject:
        return self.access_case.project

    @property
    def vlopse(self) -> Vlopse:
        return self.access_case.vlopse


class Answer(models.Model):
    """Relates a question to it's reply. May have a file or _normal_ reply
    in case of file, value returns `VersionedUploadedFile`."""

    _value = models.TextField()
    files: QuerySet[VersionedUploadedFile]

    question: DSAQuestion | VLOPSEQuestion

    def __str__(self) -> str:
        return f"{self.question.text[:15]}={self.value}"

    def should_have_file_answer(self) -> bool:
        return self.question.input_type == InputType.FILE_UPLOAD

    @property
    def value(self) -> str | VersionedUploadedFile | None:
        if self.should_have_file_answer():
            return self.files.first()
        return self._value


class DSAAnswer(Answer):
    """Answers given to DSAQuestions during Wizard phase.
    _reply related_ functionality is defined in superclass `Answer`"""

    question = models.ForeignKey(
        DSAQuestion,
        on_delete=models.PROTECT,
        db_index=True,
    )

    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.CASCADE,
        related_name="dsa_answers",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "question"],
                name="unique_answer_per_project_question",
            )
        ]


class VLOPSEAnswer(Answer):
    """Answers specific to a VLOPSE application. May stem from Wizardphase
    or be created in VLOPSE specific questionaires later on.
    _reply related_ functionality is defined in superclass `Answer`"""

    question = models.ForeignKey(
        VLOPSEQuestion,
        max_length=16,
        on_delete=models.PROTECT,
        db_index=True,
    )

    application = models.ForeignKey(
        AccessApplication, on_delete=models.CASCADE, related_name="answers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "question"],
                name="unique_answer_per_application_question",
            )
        ]


class VersionedUploadedFile(models.Model):
    """Provides both access to uploaded files and their version history.
    Currently linked to a specific answer to either `DSAQuestion` or `VLOPSEQuestion`
    """

    # TODO: Autoincrement on save
    # TODO: remove link to answer and use project / case
    # TODO: Create super class UploadedFile.
    dsa_answer = models.ForeignKey(
        DSAAnswer, null=True, blank=True, on_delete=models.CASCADE, related_name="files"
    )
    vlopse_answer = models.ForeignKey(
        VLOPSEAnswer,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="files",
    )
    name = models.CharField(max_length=255, blank=True)
    creator = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name="documents"
    )
    version = models.PositiveIntegerField(editable=False)

    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    data = models.BinaryField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    question: DSAQuestion | VLOPSEQuestion

    class Meta:
        ordering: ClassVar = ["-version"]
        constraints: ClassVar = [
            models.CheckConstraint(
                condition=(
                    Q(dsa_answer__isnull=False, vlopse_answer__isnull=True)
                    | Q(dsa_answer__isnull=True, vlopse_answer__isnull=False)
                ),
                name="file_belongs_to_exactly_one_answer",
            ),
            models.UniqueConstraint(
                fields=["dsa_answer", "version"],
                name="unique_file_version_per_dsa_answer",
            ),
            models.UniqueConstraint(
                fields=["vlopse_answer", "version"],
                name="unique_file_version_per_vlopse_answer",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"

    @property
    def answer(self) -> DSAAnswer | VLOPSEAnswer:
        if self.dsa_answer is not None:
            return self.dsa_answer
        return self.vlopse_answer

    def _answer_lookup(self) -> dict[str, int]:
        if self.dsa_answer.id is not None:
            return {"dsa_answer_id": self.dsa_answer_id}
        return {"vlopse_answer_id": self.vlopse_answer_id}

    @property
    def versions(self) -> models.QuerySet[VersionedUploadedFile]:
        return VersionedUploadedFile.objects.filter(**self._answer_lookup())

    @property
    def most_recent(self) -> VersionedUploadedFile:
        return self.versions.first()

    @property
    def previous(self) -> VersionedUploadedFile | None:
        return self.versions.filter(version__lt=self.version).first()

    @property
    def next(self) -> VersionedUploadedFile | None:
        return self.versions.filter(version__gt=self.version).last()
