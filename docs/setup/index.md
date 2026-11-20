# Dev Setup

Everything you need to run, test and deploy IDAT locally.

## Prerequisites

| Tool                                            | Used for                                             |
|-------------------------------------------------|------------------------------------------------------|
| [Docker](https://docs.docker.com/get-docker/)   | Django, PostgreSQL and Redis containers              |
| [uv](https://docs.astral.sh/uv/)                | Python dependencies, running tools on the host       |
| [Node.js](https://nodejs.org/) (see `.nvmrc`)   | Building the Tailwind and Alpine assets, host only   |
| [just](https://just.systems/) (optional)        | Shortcuts for common commands (`just --list`)        |

## Next steps

1. [Local development](local.md): start the stack and create users.
2. [Frontend assets](frontend-assets.md): build CSS and JS.
3. [Testing & quality](testing.md): tests, coverage, type checks, linters.
4. [Deployment](deployment.md): the production Docker stack.
