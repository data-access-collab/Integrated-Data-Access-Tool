# Figma sync

The [UI library](ui-library.md) follows the Figma design system. Syncing is one-way,
**Figma → repo**: design changes are made in Figma first, then imported.

Imports are done with Claude Code's `figma-sync` skill
(`.claude/skills/figma-sync/SKILL.md`). It can:

- import a new Figma component or page as django-cotton templates,
- update a component that changed in Figma,
- compare all components and update the ones that drifted.

The rules the generated templates follow (tokens only, one component per file, props,
slots, variants, icons) are in `CLAUDE.md` under "UI library rules"; review a sync's
output in the [component gallery](../setup/local.md#useful-urls-debug-only).

!!! warning
    Never change Figma from the repo side. Report problems in the Figma file and 
    the Figma maintainer will fix it.
