# Frontend assets

[Tailwind CSS](https://tailwindcss.com/) is used for styles and
[Alpine.js](https://alpinejs.dev/) for interactivity. Node.js runs on the host only.

## Setup (once)

Install the Node.js version pinned in `.nvmrc` (e.g. with
[nvm](https://github.com/nvm-sh/nvm)) and the dependencies:

```bash
nvm install
npm ci
```

## Development

Run the watcher next to the Docker stack. It rebuilds the assets whenever a template or
script changes:

```bash
npm run watch
```

To run only one of them, use `npm run watch:css` or `npm run watch:js`.

## Files

- `idat/assets/css/input.css`: Tailwind entry point (sources, design tokens, custom CSS)
- `idat/assets/js/main.js`: JS entry point (Alpine.js setup, plugins, components)
- `idat/static/dist/`: generated `main.css` and `main.js`; gitignored, never edit or commit

Tailwind only generates classes it finds as complete strings in the templates and
scripts. See the [UI library](../contributing/ui-library.md) for the token and component
rules.

## Production

The production Docker image builds the assets itself (`npm run build`); no manual step
is needed before deploying. To check a production build locally:

```bash
npm run build
```
