from typing import TYPE_CHECKING

from idat.dsa40.models import DSAQuestion, VLOPSEQuestion

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

    def get(self, question_id: str) -> VLOPSEQuestion | None:
        return VLOPSEQuestion.objects.filter(id=question_id).first()

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

    def get_unified(self, question_id: str) -> DSAQuestion | None:
        return DSAQuestion.objects.filter(id=question_id).first()

    def get_all_unified_for(self, question_ids: list[str]) -> QuerySet[DSAQuestion]:
        return DSAQuestion.objects.filter(id__in=question_ids).all()

    def get_all_unified(self) -> QuerySet[DSAQuestion]:
        return DSAQuestion.objects.all()
