from typing import TYPE_CHECKING

from idat.dsa40_form_handler.models import DSAQuestion, VLOPSEQuestion

if TYPE_CHECKING:
    from django.db.models import QuerySet


class QuestionService:
    def __init__(self) -> None:
        # TODO: self, app=.. then app.async session lala
        pass

    def add(self, *args, **kwargs) -> None:
        question = VLOPSEQuestion(*args, **kwargs)
        question.save()

    def get_all_for_vlopse(self, vlopse: str) -> QuerySet[VLOPSEQuestion]:
        return VLOPSEQuestion.objects.filter(vlopse=vlopse).all()

    def get(self, key: str) -> VLOPSEQuestion | None:
        return VLOPSEQuestion.objects.filter(key=key).first()

    def add_unified(
        self,
        id: str | None,  # noqa: A002
        text: str,
        input_type: str,
        help_text: str | None,
        config: dict[str, str] | None = None,
    ) -> None:
        DSAQuestion(
            id=id, text=text, input_type=input_type, help_text=help_text, config=config
        ).save()

    def get_unified(self, key: str) -> DSAQuestion | None:
        return DSAQuestion.objects.filter(key=key).first()

    def get_all_unified_for(self, keys: list[str]) -> QuerySet[DSAQuestion]:
        return DSAQuestion.objects.filter(key__in=keys).all()

    def get_all_unified(self) -> QuerySet[DSAQuestion]:
        return DSAQuestion.objects.all()
