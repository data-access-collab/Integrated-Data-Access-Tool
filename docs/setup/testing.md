# Testing & quality

## Tests

```bash
just pytest            # in the Django container
uv run pytest          # on the host
```

## Coverage

```bash
uv run coverage run -m pytest
uv run coverage html
open htmlcov/index.html
```

## Type checks

```bash
uv run mypy idat
```

## Linters and formatters

[pre-commit](https://pre-commit.com/) runs Ruff, djLint, djangofmt and the other hooks
in `.pre-commit-config.yaml` on every commit. Install the hooks once, or run them on
everything:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## CI

`.github/workflows/ci.yml` builds the Docker images, checks for missing migrations, runs
the migrations and the test suite.
