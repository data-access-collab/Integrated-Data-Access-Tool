export COMPOSE_FILE := "docker-compose.local.yml"

## Just does not yet manage signals for subprocesses reliably, which can lead to unexpected behavior.
## Exercise caution before expanding its usage in production environments.
## For more information, see https://github.com/casey/just/issues/2473 .


# Default command to list all available commands.
default:
    @just --list

# build: Build python image.
build *args:
    @echo "Building python image..."
    @docker compose --profile default build {{args}}

# up: Start up containers.
up:
    @echo "Starting up containers..."
    @docker compose --profile default up -d --remove-orphans

# down: Stop containers.
down:
    @echo "Stopping containers..."
    @docker compose --profile default --profile dev-tools down

# restart: Restart a service (default: django).
restart service="django":
    @docker compose restart {{service}}

# prune: Remove containers and their volumes.
prune *args:
    @echo "Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: View container logs
logs *args:
    @docker compose logs -f {{args}}

# manage: Executes `manage.py` command.
manage +args:
    @docker compose run --rm django python ./manage.py {{args}}

# pytest: Run tests with pytest.
pytest *args:
    @docker compose run --rm django pytest {{args}}

# docs: Serve the docs with live reload at http://localhost:9000.
docs:
    @uv run --group docs zensical serve --dev-addr localhost:9000

# docs-build: Build the docs into site/, failing on warnings.
docs-build:
    @uv run --group docs zensical build --strict

# mailpit: Start only the mailpit service.
mailpit:
    @echo "Starting Mailpit..."
    @docker compose --profile dev-tools up -d

# stop-mailpit: Stop only the mailpit service.
stop-mailpit:
    @echo "Stopping Mailpit..."
    @docker compose --profile dev-tools stop
