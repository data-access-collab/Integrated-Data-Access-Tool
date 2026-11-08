"""DEBUG-only component gallery (/dev/components/), wired in config/urls.py.

Form-field components are demoed with real BoundFields: `form` is unbound (initial
values), `form_errors` is bound to empty data so every required field shows its error.
dev/_section.html passes the light or dark set to each copy of a demo.
"""

import datetime
import json
from pathlib import Path
from typing import Any

from django import forms
from django.conf import settings
from django.views.generic import TemplateView

from idat.core.forms import country_choices

DPIA_LABEL = "Data-protection impact assessment"
# File Upload demo config, in the format the DSA40 wizard's ClientFileWidget renders.
CLIENT_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DEMO_FILE = {
    "name": "data-protection-impact-assessment.pdf",
    "size": 2_516_582,
    "type": "application/pdf",
    "sha256": "0" * 64,
}


class GalleryDemoForm(forms.Form):
    accept_terms = forms.BooleanField(
        label="Data will only be used for non-commercial research",
        help_text="Required by Art. 40(8) DSA.",
    )
    newsletter = forms.BooleanField(
        label="Send me updates about my application",
        required=False,
        initial=True,
    )
    # Yes / No / unset. NullBooleanField skips the required check; clean_ enforces it.
    has_ethics_approval = forms.NullBooleanField(
        label="Has your project received ethics approval?",
    )
    is_affiliated = forms.NullBooleanField(
        label="Are you affiliated with a research organisation?",
        required=False,
        initial=False,
    )

    institutional_email = forms.EmailField(
        label="Institutional e-mail",
        help_text="Used by platforms to verify your affiliation.",
    )
    project_title = forms.CharField(
        label="Project title",
        max_length=120,
        required=False,
        initial="Recommender systems and minors",
    )

    research_question = forms.CharField(
        label="Describe your research question",
        widget=forms.Textarea,
        max_length=1500,
        help_text=(
            "Platforms use this to judge whether your request fits Art. 40(4) DSA."
        ),
    )

    organisation_type = forms.ChoiceField(
        label="Organisation type",
        choices=[
            ("", "---------"),
            ("university", "University"),
            ("research_institute", "Research institute"),
            ("ngo", "Non-profit / NGO"),
            ("other", "Other"),
        ],
        help_text="As registered with your national research authority.",
    )
    funding_source = forms.ChoiceField(
        label="Funding source",
        choices=[("public", "Public"), ("private", "Private"), ("mixed", "Mixed")],
        required=False,
        initial="public",
    )

    planned_start = forms.DateField(
        label="Planned start of data access",
        initial=datetime.date(2027, 3, 14),
    )

    risk_categories = forms.MultipleChoiceField(
        label="Further systemic-risk categories (Art. 34(1))",
        choices=[
            ("illegal_content", "Dissemination of illegal content"),
            ("fundamental_rights", "Fundamental rights"),
            ("civic_discourse", "Civic discourse & elections"),
            ("public_health", "Public health & minors' well-being"),
        ],
        initial=["fundamental_rights", "civic_discourse"],
        help_text="Pick any that apply.",
    )

    country = forms.ChoiceField(
        label="Country of your research organisation",
        choices=country_choices,
        initial="DE",
        help_text="ISO 3166-1 · platforms check EU establishment",
    )

    # File Upload: only the server-side error needs a field; the other states use
    # props (client_file in the view context).
    dpia = forms.FileField(label=DPIA_LABEL)

    # Platform Answer Group: one answer per platform (PlatformScopedGroup).
    data_request_tiktok = forms.CharField(
        label="TikTok: which data do you request?",
        widget=forms.Textarea,
        max_length=1500,
        required=False,
        help_text="TikTok asks for API endpoints and fields.",
    )
    data_request_instagram = forms.CharField(
        label="Instagram: which data do you request?",
        widget=forms.Textarea,
        max_length=1500,
        required=False,
        initial="Public posts and Reels from EU accounts with political-ad labels.",
        help_text="Meta asks for Content Library product names.",
    )
    data_request_youtube = forms.CharField(
        label="YouTube: which data do you request?",
        widget=forms.Textarea,
        max_length=1500,
        required=False,
        help_text="YouTube asks for Researcher Program data types.",
    )

    submitted_youtube = forms.BooleanField(
        label="I've submitted this application — start tracking it",
        required=False,
    )

    # Dialog / Log platform reply
    platform = forms.ChoiceField(
        label="Platform",
        choices=[
            ("tiktok", "TikTok"),
            ("instagram", "Instagram"),
            ("youtube", "YouTube"),
        ],
        initial="tiktok",
    )
    response_type = forms.ChoiceField(
        label="Type of response",
        choices=[
            ("clarification", "Clarification requested"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("other", "Other"),
        ],
        initial="clarification",
    )
    response_date = forms.DateField(
        label="Date of the response", initial=datetime.date(2026, 10, 31)
    )
    reply = forms.CharField(
        label="Paste the platform's reply",
        widget=forms.Textarea,
        initial=(
            "Dear Dr. Doe, thank you for your application. Please describe where "
            "the data will be stored and who has access …"
        ),
    )
    # Plain upload (FileField), not the encrypted ClientFile flow.
    reply_file = forms.FileField(
        label="…or upload the e-mail (.eml, .msg) or a PDF",
        required=False,
    )
    deadline = forms.DateField(
        label="Reply deadline (if any)",
        required=False,
        initial=datetime.date(2026, 11, 10),
    )
    remind = forms.BooleanField(
        label="Remind me 2 days before the deadline", required=False, initial=True
    )

    # Dialog / Withdraw application
    reason = forms.ChoiceField(
        label="Reason (optional)",
        choices=[
            ("", "Select a reason"),
            ("scope", "Project scope changed"),
            ("funding", "Funding ended"),
            ("other_source", "Got the data elsewhere"),
            ("other", "Other"),
        ],
        required=False,
        initial="scope",
    )
    share_reason = forms.BooleanField(
        label="Share the reason anonymously with the community", required=False
    )

    @property
    def data_request_platforms(self) -> list[dict[str, Any]]:
        return [
            {"name": "TikTok", "field": self["data_request_tiktok"]},
            {"name": "Instagram", "field": self["data_request_instagram"]},
            {"name": "YouTube", "field": self["data_request_youtube"]},
        ]

    def clean_has_ethics_approval(self) -> bool:
        value = self.cleaned_data["has_ethics_approval"]
        if value is None:
            msg = "Please answer yes or no."
            raise forms.ValidationError(msg)
        return value


class ComponentGalleryView(TemplateView):
    template_name = "dev/components.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # One set per theme copy, so ids are unique on the page.
        context["forms"] = {theme: self._forms(theme) for theme in ("light", "dark")}
        context["submission"] = self._submission_demo()
        context["client_file"] = {
            "label": DPIA_LABEL,
            "types": json.dumps(CLIENT_FILE_TYPES),
            "accept": ",".join(CLIENT_FILE_TYPES),
            "max_size": 10 * 1024 * 1024,
            "hint": "PDF or DOCX · max. 10 MB",
            "stored": json.dumps(DEMO_FILE),
        }
        # Every <c-icon> name: the files in templates/icons/.
        icon_dir = Path(settings.APPS_DIR) / "templates" / "icons"
        context["icon_names"] = sorted(path.stem for path in icon_dir.glob("*.svg"))
        context["wizard_hrefs"] = dict.fromkeys(
            ("choose_platforms", "enter_details", "review", "generate"),
            "#wizard-sidebar",
        )
        return context

    @staticmethod
    def _submission_demo() -> dict[str, Any]:
        return {
            "email_body": "Research question:\nHow do recommender systems …",
            "attachments": [
                "application-snapchat.pdf",
                "data-protection-impact-assessment.pdf",
            ],
        }

    @staticmethod
    def _forms(theme: str) -> dict[str, GalleryDemoForm]:
        form_errors = GalleryDemoForm(data={}, prefix=f"{theme}-err")
        form_errors.is_valid()
        return {
            "form": GalleryDemoForm(prefix=theme),
            "form_errors": form_errors,
            # Dialogs: second copy opened as a real modal next to the in-place preview.
            "modal_form": GalleryDemoForm(prefix=f"{theme}-modal"),
        }
