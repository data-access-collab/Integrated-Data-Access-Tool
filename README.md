# Integrated Data Access Tool

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Helps researchers apply for data access to Very Large Online Platforms and Search
Engines (VLOPSEs) under Article 40 of the Digital Services Act.

## Documentation

Developer docs live in [`docs/`](docs/) and are built with [Zensical](https://zensical.org/):

    just docs

then open <http://localhost:9000>. Start with **Dev Setup** (`docs/setup/`).

Quick start:

    docker compose -f docker-compose.local.yml build
    docker compose -f docker-compose.local.yml up
