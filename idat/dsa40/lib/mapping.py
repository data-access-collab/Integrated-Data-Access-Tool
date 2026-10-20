from collections import defaultdict
from typing import TYPE_CHECKING

from idat.dsa40.lib.config import get_vlopse_configuration_for

if TYPE_CHECKING:
    from idat.dsa40.lib.models import PlatformMapping
    from idat.dsa40.models import DSAQuestion
    from idat.dsa40.services.questions import QuestionService


class Mapping:
    vlopse_id: str
    dsa_ids: list[str]

    def __init__(self, vlopse_id: str, dsa_ids: list[str]) -> None:
        self.vlopse_id = vlopse_id
        self.dsa_ids = dsa_ids

    def __repr__(self) -> str:
        return f"DSA([{', '.join(self.dsa_ids)}]) -> VLOPSE({self.vlopse_id})"


def hydrate_mapping(
    vlopse_question: str, mapping_definition: PlatformMapping
) -> Mapping:
    if isinstance(mapping_definition, str):
        return Mapping(vlopse_question, [mapping_definition])
    if isinstance(mapping_definition.src, list):
        return Mapping(vlopse_question, mapping_definition.src)
    if isinstance(mapping_definition.src, str):
        return Mapping(vlopse_question, [mapping_definition.src])
    return None


class MappingValidationError(Exception):
    pass


class QuestionMapper:
    _mapping: dict[str, list[Mapping]]
    questions: QuestionService

    @classmethod
    def from_vlopse_names(
        cls, vlopses: list[str], questions: QuestionService
    ) -> QuestionMapper:
        mapping = {
            vlopse: get_vlopse_configuration_for(vlopse).mappings for vlopse in vlopses
        }
        return cls(mapping, questions)

    def _validate(self) -> None:
        question_ids = [q.id for q in self.questions.get_all_unified()]
        invalid: set[Mapping] = set()
        # TODO: Check if a mapping refers to a question not defined by the vlopse
        for vlopse, mappings in self._mapping.items():
            print(f"Validating {vlopse}..")  # noqa: T201
            for mapping in mappings:
                for u_id in mapping.dsa_ids:
                    if u_id not in question_ids:
                        invalid.add(mapping)
                        msg = f"[WARN] {mapping} for {vlopse} refers to {u_id}, which is undefined!"  # noqa: E501
                        print(msg)  # noqa: T201

        if invalid:
            msg = f"[ERROR] {len(invalid)} invalid mappings found.: {invalid}"
            raise MappingValidationError(msg)

    def __init__(
        self, mapping: dict[str, dict[str, PlatformMapping]], questions: QuestionService
    ) -> None:
        self._mapping = {
            vlopse: [
                hydrate_mapping(vlopse_question, operator)
                for vlopse_question, operator in mapping_definitions.items()
            ]
            for vlopse, mapping_definitions in mapping.items()
        }
        self.questions = questions

    def _map(self) -> defaultdict[str, list[str]]:
        result: dict[str, list[str]] = defaultdict(list)
        for mappings in self._mapping.values():
            for mapping in mappings:
                for dsa_id in mapping.dsa_ids:
                    result[dsa_id].append(mapping.vlopse_id)

        return result

    def map_vlopse_to_unified(self) -> list[tuple[bool, DSAQuestion]]:
        map_traces = self._map()
        # FIXME: this should ask the db
        result: list[tuple[bool, DSAQuestion]] = []
        for dsa_id, vlopse_ids in map_traces.items():
            dsa = self.questions.get_unified(dsa_id)
            if dsa is None:
                print(f"WARNING {dsa_id} MAPPED TO UNKNOWN DSA QUESTION")  # noqa: T201
                continue
            required = False
            for vlopse_id in vlopse_ids:
                vlopse = self.questions.get(vlopse_id)
                if vlopse is None:
                    print(f"WARNING {vlopse_id} MAPPED TO UNKNOWN VLOPSE QUESTION")  # noqa: T201
                    continue
                # FIXME: Typing err
                if vlopse.required:
                    required = True
            result.append((required, dsa))

        return result
