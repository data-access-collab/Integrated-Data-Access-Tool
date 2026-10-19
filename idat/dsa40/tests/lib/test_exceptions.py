import pytest

from idat.dsa40.lib.mapping import Mapping
from idat.dsa40.lib.models import (
    Answer,
)
from idat.dsa40.lib.operator import JoinOperator, MakeISOOperator
from idat.dsa40.lib.schemas import Selection
from idat.dsa40.lib.transform import (
    Transformation,
    TransformationError,
    ValidationErrors,
)
from idat.dsa40.models import DSAQuestion


@pytest.mark.skip(reason="Not implemented yet")
def test_invalid_selection():
    answer = Answer(question_id="prev-experience", value="hehe")
    q = DSAQuestion(
        id="X1",
        type="selection",
        required=True,
        text_en="Previous experience?",
        config=Selection.model_validate(
            {"type": "selection", "options": ["Yes", "No"]}
        ),
    )
    q.config.validate_answer(answer.value)


### TRANSFORMATION BASED EXCEPTIONS ###
def test_validating_missing_argument():
    mapper = Mapping("V1", ["first-name", "last-name"])
    op = JoinOperator(" ")
    transformation = Transformation(mapper, op)
    with pytest.raises(ValidationErrors) as exc_info:
        transformation.validate_args([Answer(question_id="first-name", value="Joseph")])
    args = exc_info.value.exceptions[0].args[0]

    assert args["message"] == "missing required argument"
    assert args["loc"] == ("last-name",)


def test_transforming_missing_argument():
    mapper = Mapping("V1", ["first-name", "last-name"])
    op = JoinOperator(" ")
    transformation = Transformation(mapper, op)
    with pytest.raises(TransformationError) as exc_info:
        _ = transformation.transform([Answer(question_id="first-name", value=None)])
    exc = exc_info.value
    args = exc.args[0]
    assert args["message"] == "transformation failed"
    assert args["loc"] == ("first-name",)
    assert args["cause"] == "Cannot join None type"


def test_transforming_invalid_argument_type():
    mapper = Mapping("V1", ["first-name", "last-name"])
    op = MakeISOOperator()
    transformation = Transformation(mapper, op)
    with pytest.raises(TransformationError) as exc_info:
        _ = transformation.transform(
            [
                Answer(question_id="first-name", value="Joseph"),
                Answer(question_id="last-name", value="Weizenbaum"),
            ]
        )
    exc = exc_info.value
    args = exc.args[0]
    assert args["message"] == "transformation failed"
    assert args["loc"] == ("first-name", "last-name")
    assert args["cause"] == "Cannot create ISO from list argument."
