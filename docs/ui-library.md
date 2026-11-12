# UI library

## Source of truth

The [Figma file](https://www.figma.com/design/DjAthBSdrd2LHopYz0tGaB), page "Design system",
defines tokens, components and their behaviour. Code follows Figma;
design changes are made in Figma first and then synced.

If the Figma file or page changes, update its key (`DjAthBSdrd2LHopYz0tGaB`) and page name
in all three places: this file, the figma-sync skill (`.claude/skills/figma-sync/SKILL.md`)
and the gallery header (`idat/templates/dev/components.html`). The skill reads only from
the file named there.

## Setup

| Part                                                    | Where                                                                |
|---------------------------------------------------------|----------------------------------------------------------------------|
| Components ([django-cotton](https://django-cotton.com)) | `idat/templates/cotton/`                                             |
| Design tokens (Tailwind v4 theme)                       | `idat/assets/css/input.css`                                          |
| Alpine components                                       | `idat/assets/js/components/`, registered in `idat/assets/js/main.js` |
| Icons (Lucide SVGs)                                     | `idat/templates/icons/`, rendered by `<c-icon>`                      |
| Component gallery (DEBUG only)                          | `/dev/components/` · `idat/core/views/dev_gallery.py`                |

- `django_cotton` is in `INSTALLED_APPS`; `idat_base_tags` (`define`, `icon_content`) is a
  template builtin.
- A file's path sets its tag: `wizard/section_item.html` → `<c-wizard.section-item>`.
- Tokens only: Tailwind's default colours, radii and shadows are removed.
- Build assets on the host: `npm run build` (or `npm run watch`). The output in
  `idat/static/dist/` is loaded by `base.html`.

### Using a component

```django
<c-button variant="secondary" label="Save draft" leading-icon="save" />
<c-text-field :field="form.project_title" help-tip="title" />
```

Props, slots and usage are documented in the comment at the top of each component file.
Form fields accept a Django `BoundField` via `:field`.

## Syncing with Figma

Let a coding agent do the sync; it needs the Figma MCP connected and a browser. Keep the
dev server running so the agent can check the gallery. Copy Figma links with **Copy link
to selection**; they contain the `node-id`.

The workflow lives in the project skill `.claude/skills/figma-sync/SKILL.md`; the
conventions in `CLAUDE.md`. In Claude Code:

```text
/figma-sync import <Figma link>              new component (set) or page
/figma-sync update <Figma link> [component]  one component or page changed
/figma-sync all                              compare everything, report, then update
```

Other agents (Codex, Cursor, Copilot …) don't load these files on their own. Start with:

```text
Read CLAUDE.md and .claude/skills/figma-sync/SKILL.md and follow them for this sync:
import | update | all <Figma link>
```

Every sync ends with a short report in the agent's reply: **Bugs**, **Inconsistencies**
(Figma contradicts itself, values without a token, off-grid values) and **Notes**. It isn't
written to the repo; ask the agent to save it under `.local_docs/` (gitignored) if you
want to keep it. Nothing is committed; review the diff and the gallery (light and dark),
and raise inconsistencies with design so Figma gets fixed.
