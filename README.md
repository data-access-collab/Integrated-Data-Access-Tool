# Integrated Data Access Tool

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      uv run python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    uv run mypy idat

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    uv run coverage run -m pytest
    uv run coverage html
    uv run open htmlcov/index.html

#### Running tests with pytest

    uv run pytest

### Tailwind CSS

Styles are built with [Tailwind CSS](https://tailwindcss.com/) via the Tailwind CLI. 
Node.js runs on the host only (i.e., it is not part of the local Docker setup).

#### Setup (once)

Install the Node.js version pinned in `.nvmrc` (e.g. with [nvm](https://github.com/nvm-sh/nvm)) and install the dependencies:

    nvm install
    npm ci

#### Development

Run the watcher next to the Docker stack. It rebuilds the CSS whenever a template changes:

    npm run watch:css

#### Files

- `idat/assets/css/input.css`: Tailwind entry point (sources, theme, custom CSS)
- `idat/static/dist/main.css`: generated output, gitignored; never edit or commit

Tailwind only generates classes it finds as complete strings in the source templates.

#### Production

The production Docker image builds the CSS itself in a Node build stage (`npm run build:css`), 
so no manual build step is needed before deploying. To check a production build locally:

    npm run build:css

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).
