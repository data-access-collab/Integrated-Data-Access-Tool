# define an alias for the specific python version used in this file.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS python

ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR ${APP_HOME}

# Only the docs dependency group (Zensical + mkdocstrings): the Python source is read
# statically, so the app's own dependencies are not needed.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --only-group docs

COPY ./compose/local/docs/start /start-docs
RUN sed -i 's/\r$//g' /start-docs
RUN chmod +x /start-docs

ENV PATH="/opt/venv/bin:$PATH"
