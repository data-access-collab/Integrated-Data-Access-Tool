# Settings & environment

## Settings modules

| Module                         | Used by                                               |
|--------------------------------|-------------------------------------------------------|
| `config/settings/base.py`      | Shared by all environments                            |
| `config/settings/local.py`     | Local development (`docker-compose.local.yml`)        |
| `config/settings/test.py`      | pytest                                                |
| `config/settings/production.py`| Production stack                                      |

Settings read environment variables with
[django-environ](https://django-environ.readthedocs.io/). Locally they come from
`.envs/.local/`, in production from `.envs/.production/`.

## Environment variables

| Variable                              | Purpose                                                        |
|---------------------------------------|----------------------------------------------------------------|
| `DJANGO_SECRET_KEY`                   | Secret key (production)                                        |
| `DJANGO_DEBUG`                        | Debug mode                                                     |
| `DJANGO_ADMIN_URL`                    | Path of the Django admin                                       |
| `DJANGO_ADMIN_FORCE_ALLAUTH`          | Route admin login through allauth                              |
| `DJANGO_ACCOUNT_ALLOW_REGISTRATION`   | Allow sign-up (default: true)                                  |
| `DJANGO_SERVER_EMAIL`                 | Sender address for error emails                                |
| `DJANGO_SECURE_SSL_REDIRECT`          | Redirect HTTP to HTTPS                                         |
| `DJANGO_SECURE_HSTS_PRELOAD`          | HSTS preload                                                   |
| `DJANGO_READ_DOT_ENV_FILE`            | Read a `.env` file                                             |
| `DATABASE_URL`                        | Database connection                                            |
| `POSTGRES_HOST` / `_PORT` / `_DB` / `_USER` / `_PASSWORD` | PostgreSQL connection (Docker)              |
| `CONN_MAX_AGE`                        | Database connection lifetime                                   |
| `REDIS_URL`                           | Redis (cache)                                                  |
| `USE_DOCKER`                          | Running inside Docker (adjusts debug toolbar IPs)              |

!!! note
    The list is collected from `env(…)` calls in `config/settings/`. When you add a
    variable there, add it here too.
