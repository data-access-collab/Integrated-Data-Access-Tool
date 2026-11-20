# Settings & environment

## Settings modules

| Module                          | Used by                                               |
|---------------------------------|-------------------------------------------------------|
| `config/settings/base.py`       | Shared by all environments                            |
| `config/settings/local.py`      | Local development (`docker-compose.local.yml`)        |
| `config/settings/test.py`       | pytest                                                |
| `config/settings/production.py` | Production stack                                      |

Settings read environment variables with
[django-environ](https://django-environ.readthedocs.io/). Locally they come from
`.envs/.local/`, in production from `.envs/.production/`.

## Environment variables

| Variable                                                  | Purpose                                           |
|-----------------------------------------------------------|---------------------------------------------------|
| `DJANGO_SECRET_KEY`                                       | Secret key (required in production)               |
| `DJANGO_WIZARD_SECRET`                                    | Wizard state token key (required in production)   |
| `DJANGO_ALLOWED_HOSTS`                                    | Allowed host names (production)                   |
| `DJANGO_DEBUG`                                            | Debug mode                                        |
| `DJANGO_ADMIN_URL`                                        | Path of the Django admin (production)             |
| `DJANGO_ADMIN_FORCE_ALLAUTH`                              | Route admin login through allauth                 |
| `DJANGO_ACCOUNT_ALLOW_REGISTRATION`                       | Allow sign-up (default: true)                     |
| `DJANGO_EMAIL_BACKEND`                                    | E-mail backend (SMTP; console locally)            |
| `DJANGO_USE_MAILPIT`                                      | Send e-mail to Mailpit (local, DEBUG only)        |
| `DJANGO_DEFAULT_FROM_EMAIL`                               | Default sender address (production)               |
| `DJANGO_SERVER_EMAIL`                                     | Sender address for error emails                   |
| `DJANGO_EMAIL_SUBJECT_PREFIX`                             | Subject prefix of admin e-mails (production)      |
| `DJANGO_SECURE_SSL_REDIRECT`                              | Redirect HTTP to HTTPS                            |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`                   | HSTS for subdomains                               |
| `DJANGO_SECURE_HSTS_PRELOAD`                              | HSTS preload                                      |
| `DJANGO_SECURE_CONTENT_TYPE_NOSNIFF`                      | `X-Content-Type-Options: nosniff`                 |
| `DJANGO_READ_DOT_ENV_FILE`                                | Read a `.env` file                                |
| `DATABASE_URL`                                            | Database connection                               |
| `POSTGRES_HOST` / `_PORT` / `_DB` / `_USER` / `_PASSWORD` | PostgreSQL connection (Docker)                    |
| `CONN_MAX_AGE`                                            | Database connection lifetime                      |
| `REDIS_URL`                                               | Redis (cache)                                     |
| `USE_DOCKER`                                              | Running inside Docker (adjusts debug toolbar IPs) |

!!! note
    The list is collected from `env(…)` calls in `config/settings/`. When you add a
    variable there, add it here too.
