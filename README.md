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

### Frontend Assets (Tailwind & Alpine)

[Tailwind CSS](https://tailwindcss.com/) is used for styles and 
[Alpine.js](https://alpinejs.dev/) is used as Javascript/interactivity framework.
Node.js runs on the host only.

#### Setup (once)

Install the Node.js version pinned in `.nvmrc` (e.g. with [nvm](https://github.com/nvm-sh/nvm)) and the dependencies:

    nvm install
    npm ci

#### Development

Run the watcher next to the Docker stack. It rebuilds the assets 
whenever a template or script changes:

    npm run watch

To run only one of them, use `npm run watch:css` or `npm run watch:js`.

#### Files

- `idat/assets/css/input.css`: Tailwind entry point (sources, theme, custom CSS)
- `idat/assets/js/main.js`: JS entry point (Alpine.js setup, plugins, components)
- `idat/static/dist/`: generated `main.css` and `main.js`, gitignored; never edit or commit

Tailwind only generates classes it finds as complete strings in the source templates and scripts.

#### Production

The production Docker image builds the assets itself (`npm run build`); no manual step is needed before deploying.
To check a production build locally:

    npm run build

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).
