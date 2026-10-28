from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pycountry import countries

if TYPE_CHECKING:
    from idat.dsa40_form_handler.schema import PlatformMapping

Inputs = str | list[str | None] | None


class OperatorExecutionError(Exception):
    """Raised when an operator cannot process its inputs.

    Wraps both ``TypeError`` (wrong input shape) and ``ValueError`` (invalid
    input value) so callers only need to handle one exception type. The
    ``inputs`` field preserves the original value(s) for error reporting.
    """

    def __init__(self, message: str, inputs: Inputs) -> None:
        list_inputs = inputs if isinstance(inputs, list) else [inputs]
        super().__init__({"message": message, "inputs": list_inputs})


class AbstractOperator(ABC):
    @abstractmethod
    def _apply(self, inputs: Inputs) -> str:
        """Transform *inputs* into a single output string.

        Raise ``TypeError`` when the input shape is wrong (e.g. a list where a
        string is expected). Raise ``ValueError`` when the value itself is
        invalid (e.g. an unrecognised country name).
        """
        ...

    def apply(self, inputs: Inputs) -> str:
        """Public entry point; delegates to ``_apply`` with uniform error handling."""
        try:
            return self._apply(inputs)
        except TypeError as e:
            message = e.args[0]
            raise OperatorExecutionError(message, inputs) from None

        except ValueError as e:
            message = e.args[0]
            raise OperatorExecutionError(message, inputs) from None


class MakeISOOperator(AbstractOperator):
    """Convert a country name string to its ISO 3166-1 alpha-3 code.

    Accepts a single string (e.g. ``"Germany"``), returns the three-letter code
    (``"DEU"``). Currently supports English names only.
    """

    def _apply(self, inputs: Inputs) -> str:
        if inputs is None:
            msg = "Cannot create ISO from None argument."
            raise TypeError(msg)
        if isinstance(inputs, list):
            msg = "Cannot create ISO from list argument."
            raise TypeError(msg)
        result = countries.get(name=inputs)
        if not result:
            msg = f"Unknown country {inputs}"
            raise ValueError(msg)
        return result.alpha_3


class JoinOperator(AbstractOperator):
    """Join a list of strings into one using a fixed delimiter.

    Accepts a ``list[str]`` (e.g. ``["Jane", "Doe"]``), returns the joined
    string (``"Jane Doe"`` for a space delimiter).
    """

    delimiter: str

    def __init__(self, delimiter: str) -> None:
        self.delimiter = delimiter

    def _apply(self, inputs: Inputs) -> str:
        if inputs is None:
            msg = "Cannot join None type"
            raise TypeError(msg)
        if isinstance(inputs, str):
            msg = "Cannot join str type"
            raise TypeError(msg)
        return self.delimiter.join(inputs)


class NoopOperator(AbstractOperator):
    """Pass a single string through unchanged.

    Used for direct field mappings that require no transformation.
    """

    def _apply(self, inputs: Inputs) -> str:
        if isinstance(inputs, list):
            msg = "Cannot transform lists"
            raise TypeError(msg)
        if inputs is None:
            msg = "Cannot transform None"
            raise TypeError(msg)
        return inputs


def hydrate_operator(operator: PlatformMapping) -> AbstractOperator:
    """Instantiate the correct operator for a VLOPSE mapping entry.

    *operator* is either a bare string (direct field mapping -> ``NoopOperator``)
    or a ``PlatformMappingComplex`` whose ``operation`` field selects the
    operator:

    - ``"make-iso"``:   ``MakeISOOperator``: country name -> ISO 3166-1 alpha-3
    - ``"join-space"``: ``JoinOperator(" ")``: list of strings joined by a space
    - ``"join-comma"``: ``JoinOperator(", ")``: list of strings joined by ``", "``

    Raises ``ValueError`` for unrecognised operation strings.
    """
    if isinstance(operator, str):
        return NoopOperator()
    match operator.operation:
        case "make-iso":
            return MakeISOOperator()
        case "join-space":
            return JoinOperator(" ")
        case "join-comma":
            return JoinOperator(", ")
        case _:
            msg = f"Invalid operator description: {operator}"
            raise ValueError(msg)
