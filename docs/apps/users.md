# Users

IDAT uses a custom user model, `idat.users.models.User`. Users sign in with their
institutional e-mail (no username) and can add an optional, unique ORCID iD
(`validators.py` checks its format and check digit).

## Routes

| URL                        | What                                                                               |
|----------------------------|------------------------------------------------------------------------------------|
| `/accounts/`               | [django-allauth](https://docs.allauth.org/): sign-up, login, password, e-mail, MFA |
| `/accounts/confirm-email/` | Replaces allauth's views: "Check your inbox" and the confirm link                  |
| `/users/my-account/`       | My account (profile, `affiliations/`, `account/` tabs); login required             |

Sign-up and login are allauth's flows, customised in `adapters.py` (`AccountAdapter`)
and `forms.py`:

- **Registration** asks for first and last name, e-mail, password, optional ORCID iD and
  accepting the terms. `DJANGO_ACCOUNT_ALLOW_REGISTRATION` opens or closes it.
- **E-mail verification** is mandatory: an unverified account can't sign in. Links
  expire after 1 day, password-reset links after 1 hour.
- **Changing the e-mail** replaces the address once the new one is verified. The link
  only works signed in to the same account with a recent password or 2FA confirmation
  (`ConfirmEmailChangeView`); the old address is notified.
- **Passwords** need at least 15 characters and pass Django's other validators.
- **MFA** supports TOTP, security keys/passkeys and recovery codes; passkey login is
  enabled.

## User groups

| Group      | Requirements                                                             |
|------------|--------------------------------------------------------------------------|
| Anonymous  | None: can use the [application wizard](wizard.md) up to the preview      |
| Researcher | Verified e-mail; MFA optional                                            |
| Staff      | A second factor (TOTP or security key; recovery codes alone don't count) |

For staff, `AccountAdapter.post_login` and `StaffSecurityMiddleware` send them to the
MFA page until a second factor is set up, and keep them out of the admin until then.
Staff are logged out after `STAFF_SESSION_IDLE_TIMEOUT` (8 hours) without a request.
The admin login goes through allauth (`DJANGO_ADMIN_FORCE_ALLAUTH`).
