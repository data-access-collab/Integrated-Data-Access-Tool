import json
import re
from typing import Any

import pycountry
from django import forms
from django.core.exceptions import ValidationError

from idat.dsa40.models import DSAQuestion, InputType, Vlopse

CLIENT_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10 MB


# file types the client file field knows: extension -> content type; fields
# pick their subset. The browser only checks the extension; the file's content
# must be checked when it is saved.
CLIENT_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}
DEFAULT_CLIENT_FILE_TYPES = (".pdf", ".docx")
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class VlopseSelectionForm(forms.Form):
    vlopses = forms.ModelMultipleChoiceField(
        queryset=Vlopse.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={"required": "Please select at least one Vlopse"},
    )


class ClientFileWidget(forms.Widget):
    """File input whose file stays in the browser.

    The file input itself has no name and is never submitted. The browser
    validates and encrypts the file, stores it in IndexedDB and submits only
    its metadata ({name, size, type, sha256}) as JSON in a hidden input.
    """

    template_name = "dsa40_applications/widgets/client_file.html"

    def __init__(
        self,
        attrs: dict | None = None,
        types: tuple[str, ...] = DEFAULT_CLIENT_FILE_TYPES,
    ) -> None:
        super().__init__(attrs)
        self.types = types

    def use_required_attribute(self, initial: object) -> bool:
        # the file input is empty once a file is stored in the browser
        return False

    def format_value(self, value: object) -> str:
        if not value:
            return ""
        return value if isinstance(value, str) else json.dumps(value)

    def get_context(self, name: str, value: object, attrs: dict | None) -> dict:
        context = super().get_context(name, value, attrs)
        context["widget"].update(
            {
                "max_size": CLIENT_FILE_MAX_SIZE,
                "types": json.dumps(
                    {ext: CLIENT_FILE_TYPES[ext] for ext in self.types}
                ),
                "accept": ",".join(self.types),
            }
        )
        return context


def validate_client_file_metadata(value: object) -> None:
    """Check the shape of the metadata the browser reports for a file.

    The server never sees the file here, so it cannot verify type or size; the
    browser does that, and the file itself is validated when it is saved. This
    only keeps malformed values out of the wizard state.
    """
    if not (
        isinstance(value, dict)
        and value.keys() == {"name", "size", "type", "sha256"}
        and isinstance(value["name"], str)
        and 0 < len(value["name"]) <= 255  # noqa: PLR2004
        and isinstance(value["type"], str)
        and len(value["type"]) <= 255  # noqa: PLR2004
        and isinstance(value["size"], int)
        and value["size"] > 0
        and isinstance(value["sha256"], str)
        and SHA256_RE.fullmatch(value["sha256"])
    ):
        msg = "Please select the file again."
        raise ValidationError(msg, code="invalid")


class ClientFileField(forms.JSONField):
    """Metadata of a file kept in the browser.

    `types` are the accepted extensions (keys of CLIENT_FILE_TYPES); the browser
    checks them before storing the file.
    """

    default_validators = [validate_client_file_metadata]

    def __init__(
        self, *, types: tuple[str, ...] = DEFAULT_CLIENT_FILE_TYPES, **kwargs
    ) -> None:
        if unknown := set(types) - CLIENT_FILE_TYPES.keys():
            msg = f"Unknown client file types: {', '.join(sorted(unknown))}"
            raise ValueError(msg)
        self.types = tuple(types)
        kwargs.setdefault("widget", ClientFileWidget(types=self.types))
        super().__init__(**kwargs)

    def bound_data(self, data: object, initial: object) -> object:
        # ReviewStep binds the stored answers, which are already parsed
        return data if isinstance(data, dict) else super().bound_data(data, initial)

    def prepare_value(self, value: object) -> object:
        # keep dicts for the review; the widget serializes them
        return value


def get_question_choices(question: DSAQuestion) -> list[tuple[str, str]]:
    if not isinstance(question.config, dict):
        return []
    return [(option, option) for option in question.config.get("options", [])]


def get_question_field(question: DSAQuestion) -> forms.Field:  # noqa: PLR0911
    match question.input_type:
        case InputType.TEXT:
            return forms.CharField()
        case InputType.ISO_3166_1:
            return forms.ChoiceField(
                choices=[(c.alpha_2, c.name) for c in pycountry.countries],
            )
        case InputType.FILE_UPLOAD:
            return ClientFileField()
        case InputType.SELECTION:
            return forms.ChoiceField(choices=get_question_choices(question))
        case InputType.MULTI_SELECT:
            return forms.MultipleChoiceField(choices=get_question_choices(question))
        case InputType.DATE_SELECT:
            return forms.DateField()
        case _:
            return forms.CharField()


class QuestionsForm(forms.Form):
    def __init__(
        self,
        *args,
        question_config: list[tuple[bool, DSAQuestion]],
        answers: dict,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        for q in question_config:
            question = q[1]
            required = q[0]
            answer = answers.get(question.key)
            self.add_question_field(question, required, answer)

    def add_question_field(
        self,
        question: DSAQuestion,
        required: bool,
        initial: Any,  # noqa: ANN401
    ) -> None:
        self.fields[question.key] = get_question_field(question)
        self.fields[question.key].label = question.text
        self.fields[question.key].help_text = question.help_text
        self.fields[question.key].initial = initial
        self.fields[question.key].required = required
