# Development Guide

## Operators

Operators for transforming DSA answers into VLOPSE platform field values.

Each operator takes one or more raw answer strings and produces a single output
string suitable for a target platform field. Operators are instantiated at
runtime by `hydrate_operator` based on the `operation` key in a VLOPSE
mapping configuration (e.g. `backend/app/data/vlopses/mastodon.json`).

To add a new operator:
1. Subclass `AbstractOperator` and implement `_apply`.
2. Add a `case "<your-operation-name>"` to `hydrate_operator`.
3. Use `"operation": "<your-operation-name>"` in the relevant VLOPSE JSON file.
