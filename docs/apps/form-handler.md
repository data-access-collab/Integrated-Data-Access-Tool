# Form handler

`idat.dsa40_form_handler` connects the unified DSA questionnaire to each VLOPSE's
application form.

## Questions

- **`DSAQuestion`**: a question of the unified questionnaire, identified by `key`, with
  an `input_type`, optional `config` and a `category`.
- **`VLOPSEQuestion`**: a field of one platform's form (`key` like `X1`), linked to its
  `Vlopse`, with its own `input_type`, `required` flag and `category`. Categories are
  free text, since they come from the platforms.

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
  (`services/condition_service.py`).

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

Details: [code reference](../reference/code/form-handler.md).
