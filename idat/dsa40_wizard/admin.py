from __future__ import annotations

from typing import TYPE_CHECKING

from django import forms
from django.contrib import admin
from django.db.models import Count, Q

from idat.dsa40_form_handler.models import QuestionCategory
from idat.dsa40_wizard.models import WizardInfo
from idat.dsa40_wizard.steps import WizardStep

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


class WizardInfoForm(forms.ModelForm):
    # Checkbox lists instead of the ArrayField's comma-separated text input.
    steps = forms.MultipleChoiceField(
        choices=WizardStep.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    sections = forms.MultipleChoiceField(
        choices=QuestionCategory.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = WizardInfo
        fields = [
            "title",
            "body",
            "presentation",
            "tone",
            "order",
            "steps",
            "sections",
            "dsa_questions",
            "vlopse_questions",
        ]


class TargetsFilter(admin.SimpleListFilter):
    """Tips without any target (no step, section or question) are shown nowhere."""

    title = "targets"
    parameter_name = "targets"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list:
        return [("none", "None"), ("any", "At least one")]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[WizardInfo]
    ) -> QuerySet[WizardInfo]:
        # dsa_question_count / vlopse_question_count: WizardInfoAdmin.get_queryset
        no_targets = Q(
            steps=[], sections=[], dsa_question_count=0, vlopse_question_count=0
        )
        if self.value() == "none":
            return queryset.filter(no_targets)
        if self.value() == "any":
            return queryset.exclude(no_targets)
        return queryset


class ArrayChoiceFilter(admin.SimpleListFilter):
    """Tips whose array field (`parameter_name`) contains the chosen value."""

    # not "choices": SimpleListFilter.choices() is the method that draws the links
    options: list[tuple[str, str]]

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list:
        return self.options

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[WizardInfo]
    ) -> QuerySet[WizardInfo]:
        if self.value():
            return queryset.filter(
                **{f"{self.parameter_name}__contains": [self.value()]}
            )
        return queryset


class StepFilter(ArrayChoiceFilter):
    title = "step"
    parameter_name = "steps"
    options = WizardStep.choices


class SectionFilter(ArrayChoiceFilter):
    title = "section"
    parameter_name = "sections"
    options = QuestionCategory.choices


@admin.register(WizardInfo)
class WizardInfoAdmin(admin.ModelAdmin):
    form = WizardInfoForm
    list_display = ["title", "presentation", "tone", "order", "targets"]
    list_filter = ["tone", StepFilter, SectionFilter, TargetsFilter]
    search_fields = ["title", "body"]
    filter_horizontal = ["dsa_questions", "vlopse_questions"]
    fieldsets = [
        (None, {"fields": ["title", "body"]}),
        ("Presentation", {"fields": ["presentation", "tone", "order"]}),
        (
            "Targets",
            {
                "description": "Shown wherever one of these is shown.",
                "fields": ["steps", "sections", "dsa_questions", "vlopse_questions"],
            },
        ),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[WizardInfo]:
        return (
            super()
            .get_queryset(request)
            .annotate(
                dsa_question_count=Count("dsa_questions", distinct=True),
                vlopse_question_count=Count("vlopse_questions", distinct=True),
            )
        )

    @admin.display(description="Targets")
    def targets(self, obj: WizardInfo) -> str:
        counts = [
            (len(obj.steps), "step(s)"),
            (len(obj.sections), "section(s)"),
            (obj.dsa_question_count, "DSA question(s)"),
            (obj.vlopse_question_count, "VLOPSE question(s)"),
        ]
        return " · ".join(f"{n} {noun}" for n, noun in counts if n) or "none"
