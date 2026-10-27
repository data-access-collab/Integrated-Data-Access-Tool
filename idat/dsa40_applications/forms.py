import pycountry
from django import forms

from idat.dsa40.models import DSAQuestion, InputType, Vlopse


class VlopseSelectionForm(forms.Form):
    vlopses = forms.ModelMultipleChoiceField(
        queryset=Vlopse.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={"required": "Please select at least one Vlopse"},
    )


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
            return forms.FileField()
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

            # get question type
            self.fields[question.key] = get_question_field(question)
            self.fields[question.key].label = question.text
            self.fields[question.key].help_text = question.help_text
            self.fields[question.key].initial = answers.get(question.key)
            self.fields[question.key].required = q[0]
