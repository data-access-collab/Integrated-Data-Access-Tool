# Users

IDAT uses a custom user model, `idat.users.models.User`. It replaces Django's
`first_name` and `last_name` with a single `name` field, since first and last names don't
cover naming patterns around the globe. Keeping a custom model from the start also lets
the model be extended later without a painful migration.

## Accounts

Sign-up, login and email verification are handled by
[django-allauth](https://docs.allauth.org/) (`/accounts/`), with MFA enabled. The
adapters in `adapters.py` control whether registration is open
(`DJANGO_ACCOUNT_ALLOW_REGISTRATION`).

## API

`/api/users/`: list users, read and update the current user (`/me/`) or a user by
username. Requires a session login.
