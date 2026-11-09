---
name: figma-sync
description: Sync the UI library with the Figma design system. Import a new Figma component or page as django-cotton templates, update one that changed, or compare and update all. Use whenever asked to implement, import, update or sync something from Figma.
argument-hint: "import <Figma link> | update <Figma link> [component] | all"
---

# Figma sync

Request: $ARGUMENTS

Figma is the source of truth: file `DjAthBSdrd2LHopYz0tGaB`, page "Design system". All
conventions in CLAUDE.md apply. Never commit; the user reviews first.

Sync is one-way, Figma → repo. Never change anything in Figma: no use_figma,
generate_figma_design, upload_assets, add_code_connect_map / send_code_connect_mappings,
create_new_file, comments or any other write tool, even when asked mid-sync. Use only
read tools (get_design_context, get_screenshot, get_metadata, get_variable_defs,
search_design_system). If Figma looks wrong, report it under Inconsistencies; the user
fixes it in Figma.

## Modes
- **import <link>**: build the linked component (set). For a page frame, build it from
  existing components and create new ones only for parts that repeat.
- **update <link> [component]**: compare the Figma node with the existing component and
  list the differences first. Then update the component, its gallery demo and every caller
  (search for `<c-name`).
- **all**: list the components on the Figma page (get_metadata) and compare them with
  idat/templates/cotton/, and the variables (get_variable_defs) with
  idat/assets/css/input.css. Report one line per item (new in Figma, changed, missing in
  Figma, unchanged), wait for the user's go, then work through the list in order.
- No mode given: infer it from the request; ask if it is unclear.

## Renamed in code, not yet in Figma
The code name wins; match by node id. Treat these as the same component (not "new in
Figma" or "missing"), keep the code name, and drop a row once Figma uses the new name.

| Node  | Figma name now     | Code name             | Code                                             |
|-------|--------------------|-----------------------|--------------------------------------------------|
| 7:464 | Wizard Sidebar     | Wizard / Sidebar      | wizard/sidebar.html → c-wizard.sidebar           |
| 5:128 | Nav / Phase Step   | Wizard / Step Item    | wizard/step_item.html → c-wizard.step-item       |
| 5:175 | Nav / Section Item | Wizard / Section Item | wizard/section_item.html → c-wizard.section-item |
| 5:181 | Nav / Sub Item     | Wizard / Sub Item     | wizard/sub_item.html → c-wizard.sub-item         |

"Phase" in Figma (component names, props, descriptions) is "step" in code
(current-step prop, current_step context).

## Per component
1. One Figma component (set) at a time. Call get_design_context with a screenshot; if the
   result is sparse, request the child nodes individually.
2. Check idat/templates/cotton/ first; reuse or extend instead of duplicating.
3. Translate the MCP output (below) into a cotton component following CLAUDE.md. Copy the
   behaviour rules from the Figma component description ("Warning never blocks", "only
   show community numbers when n ≥ 10") into the component's comment and follow them.
4. Gallery: add or update idat/templates/dev/components/_<slug>.html with every variant and
   state, plus its nav entry and `{% include "dev/_section.html" with slug=… title=… node=…
   tag=… demo=… %}` in idat/templates/dev/components.html.
5. Run `npm run build` after CSS/JS changes (restart the django container if template
   edits don't show up). Check /dev/components/ in light and dark against the Figma
   screenshot: measure sizes and spacing, click through interactive states, and read the
   console for errors.

## Translating Figma MCP output
The MCP returns React + Tailwind: a visual reference only, never output JSX.
- Arbitrary token classes → utilities: bg-[var(--color-bg-X,…)] → bg-X ·
  text-[color:var(--color-text-X,…)] → text-X · border-[var(--color-border-X,…)] →
  border-X · var(--color-status-X) → text-X / bg-X · var(--color-icon-X) → text-icon-X ·
  [var(--spacing-X,…)] → X (gap-sm) · rounded-[var(--radius-X,…)] → rounded-X.
  No var(--…) classes or hex fallbacks may remain.
- Text styles, never font-['…']: Display/Large → type-display-lg, Headline/Large|Small →
  type-headline-lg|sm, Title/Large|Medium → type-title-lg|md, Body/Large|Medium|Small →
  type-body-lg|md|sm, Label/Large|Medium → type-label-lg|md, Label/Overline →
  type-overline. Effect styles Elevation/1–3 → shadow-1|2|3.
- Drop data-node-id, fontVariationSettings and React leftovers (content-stretch,
  relative/shrink-0 that do nothing, [word-break:break-word] unless needed).
- Raw px on the 4px grid → Tailwind numbers (gap-[4px] → gap-1, pl-[16px] → pl-4).
  Canvas widths (w-[280px]) → w-full / flex-1, unless the width is part of the design.
- Auto layout → flex/grid + gap, not margins or absolute positioning.
- Icons are Lucide: <c-icon>, never the figma.com/api/mcp/asset URLs.
- Whatever doesn't map cleanly (no token or text style, off-grid value, contradiction) is
  not hard-coded: keep the closest token and report it.

## Report
Don't write notes files to the repo or assume one exists. End the sync with a short report
in your reply, one line per item, "None" if empty:

- **Bugs**: broken behavior found in the code (say if fixed)
- **Inconsistencies**: Figma contradicts itself or has no token/text style for a value,
  off-grid values
- **Notes**: decisions and workarounds a reviewer should know

Write it to a file only when asked, then under .local_docs/ (gitignored).
