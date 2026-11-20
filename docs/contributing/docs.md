# How-to: project documentation

The docs are built with [Zensical](https://zensical.org/). Pages are Markdown files in
`docs/`; site settings and the navigation live in `zensical.toml` at the repository root.

## Preview the docs

On the host:

```bash
just docs
```

Or in Docker:

```bash
docker compose -f docker-compose.docs.yml up
```

Both serve the site at <http://localhost:9000> and reload when a page, `zensical.toml`
or the Python source changes.

To build the static site into `site/` (fails on warnings, such as broken links):

```bash
just docs-build
```

## Structure

| Folder               | Section       | For                                                    |
|----------------------|---------------|--------------------------------------------------------|
| `docs/setup/`        | Dev Setup     | Running, testing and deploying the project             |
| `docs/contributing/` | Contributing  | Conventions and meta topics (UI library, these docs)   |
| `docs/apps/`         | Apps          | One page per Django app: what it does and why          |
| `docs/reference/`    | Reference     | API, settings, and generated code pages                |

Apps pages explain in prose and link to their code page under `reference/code/`, so the
details stay generated from the code instead of going stale.

## Add a page

1. Create a Markdown file in the matching folder, e.g. `docs/apps/new-app.md`.
2. Add it to `nav` in `zensical.toml`; pages left out of `nav` are built but not listed
   in the sidebar. A section's `index.md` is opened by clicking the section name.

Admonitions (`!!! note`), tables, tabs, Mermaid diagrams and highlighted code blocks
are enabled.
See the [Zensical authoring guide](https://zensical.org/docs/authoring/markdown/).

## Docstrings to documentation

API reference pages are generated from docstrings with
[mkdocstrings](https://mkdocstrings.github.io/python/). Put a `:::` line with the dotted
module, class or function path on a page in `../reference/code`:

Google-style docstrings are expected (`Args:`, `Returns:`, `Raises:` sections) to 
render properly. However, we currently only include models in the code reference 
with:

```markdown
::: idat.users.models
    options:
        heading: "Models"
        show_root_heading: true
        toc_label: "Models"
```

The source is read statically, so Django does not need to be set up.

For an example, see `../reference/code`, rendered as
[Users](../reference/code/users.md).
