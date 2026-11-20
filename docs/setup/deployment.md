# Deployment

Production runs as a Docker Compose stack (`docker-compose.production.yml`):

| Service   | Source                          | Role                                   |
|-----------|---------------------------------|----------------------------------------|
| django    | `compose/production/django/`    | Gunicorn app server; builds the assets |
| postgres  | `compose/production/postgres/`  | Database, with backup/restore scripts  |
| traefik   | `compose/production/traefik/`   | Reverse proxy, TLS                     |
| nginx     | `compose/production/nginx/`     | Serves media files                     |

Environment variables come from `.envs/.production/`; see
[Settings & environment](../reference/settings.md).

!!! note "To do"
    Document the actual deployment procedure (host, how the stack is started and
    updated, backups). Until then, see the
    [cookiecutter-django Docker guide](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html),
    which this setup is based on.
