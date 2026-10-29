from collections import defaultdict
from typing import TYPE_CHECKING

from idat.dsa40_form_handler.services.questions import QuestionService
from idat.dsa40_form_handler.validation.config import get_vlopse_configuration_for

if TYPE_CHECKING:
    from collections.abc import Mapping

    from idat.dsa40_form_handler.schema import Condition


class ConditionService:
    question_service: QuestionService

    def __init__(self) -> None:
        self.question_service = QuestionService()

    def get_conditions(
        self, for_vlopses: list[str]
    ) -> Mapping[str, dict[str, list[Condition]]]:
        return {
            vlopse: get_vlopse_configuration_for(vlopse).conditions
            for vlopse in for_vlopses
        }

    def get_merged_conditions(
        self, for_vlopses: list[str]
    ) -> Mapping[str, list[Condition]]:
        merged: dict[str, list[Condition]] = defaultdict(list)
        for conditions in self.get_conditions(for_vlopses).values():
            for target_id, conds in conditions.items():
                merged[target_id].extend(conds)
        return merged
