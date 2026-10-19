from idat.dsa40.lib.models import (
    Answer,
    MappedAnswer,
    MappingError,
    PlatformMapping,
    PlatformMappingComplex,
)
from idat.dsa40.lib.transform import AnswerTransformer

mapping: dict[str, PlatformMapping] = {
    "T1": PlatformMappingComplex(
        src=["first-name", "last-name"], operation="join-space"
    )
}
transformer = AnswerTransformer(mapping)


def test_invalid_argument():
    mapping: dict[str, PlatformMapping] = {
        "T1": PlatformMappingComplex(src="first-name", operation="join-space")
    }
    transformer = AnswerTransformer(mapping)
    res = transformer.map(
        [
            Answer(question_id="first-name", value="Joseph"),
        ]
    )

    err = res[0]
    assert isinstance(err, MappingError)
    assert err.errors
    assert err.errors[0].loc == ["first-name", "T1"]
    # TODO: error should be more specific
    assert err.errors[0].message == "transformation failed"


def test_missing_argument():
    mapping: dict[str, PlatformMapping] = {
        "T1": PlatformMappingComplex(
            src=["first-name", "last-name"], operation="join-space"
        )
    }
    transformer = AnswerTransformer(mapping)
    res = transformer.map(
        [
            Answer(question_id="first-name", value="Joseph"),
        ]
    )

    err = res[0]
    assert isinstance(err, MappingError)
    assert err.errors
    assert err.errors[0].loc == ["T1", "last-name"]
    assert err.errors[0].message == "missing required argument"


def test_invalid_value():
    mapping: dict[str, PlatformMapping] = {
        "T1": PlatformMappingComplex(
            src=["first-name", "last-name"], operation="join-space"
        )
    }
    transformer = AnswerTransformer(mapping)
    res = transformer.map(
        [
            Answer(question_id="first-name", value="Joseph"),
            Answer(question_id="last-name", value=None),
        ]
    )

    err = res[0]
    assert isinstance(err, MappingError)
    assert err.errors
    # TODO: loc should be only last-name
    assert err.errors[0].loc == ["first-name", "last-name", "T1"]
    # TODO: error should be more specific
    assert err.errors[0].message == "transformation failed"


def test_valid_join_spaces():
    mapping: dict[str, PlatformMapping] = {
        "T1": PlatformMappingComplex(
            src=["first-name", "last-name"], operation="join-space"
        )
    }
    transformer = AnswerTransformer(mapping)
    res = transformer.map(
        [
            Answer(question_id="first-name", value="Joseph"),
            Answer(question_id="last-name", value="Weizenbaum"),
        ]
    )

    res = res[0]
    assert isinstance(res, MappedAnswer)

    assert res.value == "Joseph Weizenbaum"


def test_valid_make_iso():
    mapping: dict[str, PlatformMapping] = {
        "T1": PlatformMappingComplex(src="country", operation="make-iso")
    }
    transformer = AnswerTransformer(mapping)
    res = transformer.map(
        [
            Answer(question_id="country", value="Germany"),
        ]
    )

    res = res[0]
    assert isinstance(res, MappedAnswer)

    assert res.value == "DEU"


def test_invalid_make_iso():
    mapping: dict[str, PlatformMapping] = {
        "T1": PlatformMappingComplex(src="country", operation="make-iso")
    }
    transformer = AnswerTransformer(mapping)
    res = transformer.map(
        [
            Answer(question_id="country", value="German"),
        ]
    )

    err = res[0]
    assert isinstance(err, MappingError)
    assert err.errors
    # TODO: loc should be only last-name
    assert err.errors[0].loc == ["country", "T1"]
    # TODO: error should be more specific
    assert err.errors[0].message == "transformation failed"
