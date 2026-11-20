# Form handler

`idat.dsa40_form_handler` connects the unified DSA questionnaire to each VLOPSE's
application form.

## Questions

There are two kinds of questions: VLOPSEQuestions and DSAQuestions.
VLOPSEQuestions model the application forms by VLOPSEs, while the DSAQuestions are the
abstracted questions provided by the admin team.

- **`DSAQuestion`**s are identified by its unique `key`. The keys SHOULD be descriptive.
  it's fields are:
  - `input_type`: The type of the input.
  - `category`: Used to group different DSAQuestions, e.g. all questions related to
  one's affiliation.
  - `config`: custom configuration for a question, e.g. in case of selections holds
    the options given or Text Questions have a maximum length

- **`VLOPSEQuestion`**s are identified by its unique `key` as well. These keys
  MAY be prefixed by a shorthand for its VLOPSE to ease editing.
  - `vlopse`: links the question to its VLOPSE
  - `input_type`: The type of the input.
  - `required`: Whether the question is ALWAYS required in a VLOPSE questionnaire.
    For conditional requirement, see the mapping description below.
  - `category`: Used to group different VLOPSEQuestions, e.g. all questions related to
  one's affiliation.

Both are seeded by migrations `0002` and `0003` from `migrations/data/`.

## Input types

`form_field_types.py` defines how each input type validates an answer: ISO 3166-1
country, selection, boolean, text, file upload, date range and date select.

## VLOPSE mappings

Each platform has a mapping file, `fixtures/vlopses/<vlopse>.json`, loaded by
`validation/config.py`:

```json
{
  "mappings": {
    "X1": { "src": ["first-name", "last-name"], "operation": "join-space" },
    "X2": "email-inst",
    "X3": { "src": "org-addr-country", "operation": "make-iso" }
  },
  "conditions": {
    "data-acc-end": [
      { "question_id": "data-acc-start", "operator": "eq", "value": "01-07-1992" }
    ]
  }
}
```

- **`mappings`**: platform field → DSA question key(s). A plain string copies the answer;
  an object combines one or more answers with an operator.
- **`conditions`**: when a DSA question applies, depending on other answers
  (`services/condition_service.py`). Use this to express conditional requirement.

`QuestionMapper` (`validation/mapping.py`) checks that every mapping points to existing
questions; the `/api/v1/health` endpoint reports the result as `mapping_status`.

## Operators

Operators transform DSA answers into VLOPSE field values (`validation/operator.py`).
Each takes one or more raw answer strings and produces a single string for a platform
field. They are created at runtime by `hydrate_operator`, based on the `operation` key
in the mapping.

| Operator          | Does                                              |
|-------------------|---------------------------------------------------|
| `MakeISOOperator` | Country name → ISO 3166-1 alpha-3 code            |
| `JoinOperator`    | Joins several answers with a fixed delimiter      |
| `NoopOperator`    | Passes a single answer through unchanged          |

To add an operator:

1. Subclass `AbstractOperator` and implement `_apply`.
2. Add a `case "<your-operation-name>"` to `hydrate_operator`.
3. Use `"operation": "<your-operation-name>"` in the relevant VLOPSE JSON file.

## Validation and transformation

`services/form_engine.py` (`FormService`) ties it together: it selects the questions for
a set of platforms, validates answers against their input types, and uses
`AnswerTransformer` (`validation/transform.py`) to produce each platform's field values.
Provides both question specific and general validation guidance.
Validation may fail for multiple reasons:
- A DSAQuestion is required but not filled out. Note that _requiredness_ is computed by
  checking its dependent VLOPSEQuestions
- An input to a DSAQuestion is invalid in its type (only checks iterable/single value currently)
- An input to a DSAQuestion violates a specific validation in the `config` attribute (e.g. max_length for free-text)
- A Mapping is misconfigured (e.g. a target question doesnt exist)
- a VLOPSE data type is violated by the transformed answer.

Details: [code reference](../reference/code/form-handler.md).
