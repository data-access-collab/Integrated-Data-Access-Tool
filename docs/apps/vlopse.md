# VLOPSE

`idat.vlopse` stores the **Very Large Online Platforms and Search Engines** researchers
can apply to, and how an application to each is made.

## Model

`Vlopse` has a unique `name`, `platform_information`, whether an account is required,
an `application_link`, and the application `modality`: `form` or `email`.
Details: [code reference](../reference/code/vlopse.md).

## Seed data

`migrations/0002_initial_data.py` loads the platforms from
`migrations/data/0002_initial_data.json` with `update_or_create`, so re-running is safe.
Add a platform by adding it to the JSON in a new data migration.

Each platform also needs a mapping file in the form handler
(`idat/dsa40_form_handler/fixtures/vlopses/<name>.json`); see
[Form handler](form-handler.md#vlopse-mappings).
