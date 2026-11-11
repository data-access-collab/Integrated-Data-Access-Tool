# Core

`idat.core` holds code shared by the other apps.

| Module                              | What                                                                   |
|-------------------------------------|------------------------------------------------------------------------|
| `templatetags/idat_base_tags.py`    | `define` and `icon_content` tags; registered as template builtins      |
| `forms.py`                          | Shared form helpers, e.g. `country_choices()` for `<c-country-select>` |
| `views/dev_gallery.py`              | Component gallery at `/dev/components/` (DEBUG only)                   |
| `api/schema.py`                     | Shared API schemas, e.g. `ActionOut`                                   |

Templates, cotton components and icons live in `idat/templates/`; see the
[UI library](../contributing/ui-library.md).
