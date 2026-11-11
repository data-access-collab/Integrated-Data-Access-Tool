# Apps

IDAT helps researchers apply for data access under Article 40 of the Digital Services
Act (DSA). A researcher answers **one unified questionnaire**; IDAT maps the answers onto
the application forms of each selected Very Large Online Platform or Search Engine
(**VLOPSE**).

## Django apps

| App                             | Package                    | Responsibility                                          |
|---------------------------------|----------------------------|---------------------------------------------------------|
| [Core](core.md)                 | `idat.core`                | Shared forms, template tags, dev views                  |
| [Users](users.md)               | `idat.users`               | Custom user model, accounts (allauth)                   |
| [VLOPSE](vlopse.md)             | `idat.vlopse`              | The platforms and how to apply to them                  |
| [Form handler](form-handler.md) | `idat.dsa40_form_handler`  | Questions, mapping, validation and transformation       |
