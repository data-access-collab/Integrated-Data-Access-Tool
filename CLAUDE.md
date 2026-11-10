## UI library rules

Apply to all template and component work. Syncing with Figma (importing or updating a
component or page) follows the figma-sync skill (.claude/skills/figma-sync/SKILL.md).
Figma is read-only, always: sync is one-way, Figma → repo. Never use a Figma write tool
(use_figma, generate_figma_design, upload_assets, Code Connect mappings, new files,
comments …), even when asked; report Figma problems instead, the user fixes them there.

### Basics
- Output Django templates (.html), never JSX/React/Vue.
- Reuse or extend existing components in idat/templates/cotton/; never duplicate one.
  Pages are built from components; markup used only once can stay inline.
- A value without a token is never hard-coded: use the closest token and mention it.

### Design tokens (idat/assets/css/input.css) — use only these
Tailwind's default palette, radii and shadows are removed: bg-gray-50, text-red-600,
shadow-md, rounded-xl … generate NO CSS.
- bg-: canvas, surface, surface-muted, nav, nav-hover, nav-active, accent, accent-hover,
  accent-subtle, brand, selected, disabled, success-subtle, danger-subtle,
  warning-subtle, info-subtle
- text-: primary, secondary, tertiary, disabled, on-accent, on-brand, on-nav,
  on-nav-muted, accent, link
- border-: default, strong, focus, accent, on-nav · focus: ring-focus, outline-focus
- Status, with any color utility: success, danger, warning, info, success-on-nav,
  danger-on-nav, warning-on-nav (text-danger, bg-success, border-warning …)
- Icons: text-icon-default, text-icon-on-nav (icons use currentColor)
- Spacing: 2xs 4 · xs 8 · sm 12 · md 16 · lg 24 · xl 32 · 2xl 48 · 3xl 64 (p-md, gap-sm …)
- Radius: rounded-sm 6 · md 10 · lg 16 · full · Shadow: shadow-1|2|3
- Type: type-display-lg, type-headline-lg|sm, type-title-lg|md, type-body-lg|md|sm,
  type-label-lg|md, type-overline. Each sets family, size, line-height, weight and
  tracking: no font-/text-[size]/leading- classes on top.
- Dark mode comes from the tokens (class="dark" on <html>): no dark: variants for them.

### Styling
- Token utilities only: no hex, no arbitrary values (bg-[#4f46e5]).
- Auto layout → flex/grid + gap, not margins or absolute positioning.
- Every class name must appear complete and literally in the source: Tailwind scans the
  text, so bg-{{ color }} or 'text-' + tone generates no CSS. Map values to full class
  strings with {% if %} (see Variants below).
- Semantic HTML: <button> for actions, <a> for navigation, <nav>/<ol> for nav and
  breadcrumbs, aria-current="step"/"page" on the current item, aria-expanded on
  accordion triggers.

### django-cotton components
- One component per file in idat/templates/cotton/; snake_case file → kebab-case tag,
  subfolders → dots: button.html → <c-button>, user_card.html → <c-user-card>,
  nav/section_item.html → <c-nav.section-item>. Folders follow the Figma prefix (Nav / …
  → nav/, Help / … → help/, Form / … → forms/), at most one level deep.
- File order: the {% comment %} block first (behaviour rules, props, usage only), a blank
  line, {% load %}, <c-vars>, then the markup. Never <c-vars> above the comment:
    {% comment %}
      Nav / Section Item
      …
    {% endcomment %}

    {% load static %}
    <c-vars state="incomplete" label="" count="" class="" />
    <a class="… {{ class }}" {{ attrs }}>
- Props and defaults go in <c-vars>; declared props are NOT part of {{ attrs }}. Put
  {{ attrs }} on the root element (id, aria-*, data-*, x-* …) and append a declared
  `class` prop to the root's classes.
- Never name a prop after an attribute that assistive technology reads (role, aria-*,
  tabindex, hidden, lang, alt): it swallows the caller's role="…" or aria-label="…" and
  accessibility breaks silently. Prefix it (person-role, affiliation-role).
- Prop names are kebab-case on the tag and underscores in the template:
  {{ person_role }}, never {{ person-role }}.
- Slots: {{ slot }} for the main content, a named slot per extra content area:
    caller:    <c-card><c-slot name="header">Title</c-slot>Body</c-card>
    component: <header>{{ header }}</header><div>{{ slot }}</div>
- Variants: Figma variant property → prop with lowercase kebab-case values
  (State=Not enough data → state="not-enough-data"), each mapped to a FULL class string:
    {% if state == "current" %}bg-nav-hover border-l-3 border-accent text-on-nav
    {% elif state == "blocking" %}text-danger-on-nav
    {% else %}text-on-nav-muted
    {% endif %}
- Keep that {% if %} inline while the values are short. Assign them to variables with
  {% define "<value>" as <name> %} instead when a branch's value no longer fits on one
  line, a prop sets several values per branch, or a value is needed in several places
  (e.g. both sides of a form/div switch). Usually classes (variant_class, then
  class="… {{ variant_class }} {{ class }}"), but any value works: a badge tone, an icon
  name. Translatable text uses {% translate "…" as label %} instead. Put the block right
  after <c-vars>, before the markup. Value first, name last: the reverse order
  ({% define name as "…" %}) silently leaves the variable empty.
- Figma boolean property → boolean attribute (<c-help.accordion expanded>, then
  {% if expanded %}). Figma text property → string prop, defaulting to the Figma text
  only if it's real UI copy, else "".
- Plain attributes are strings; pass Python values with a colon:
  <c-table :rows="orders" :striped="True" />.

### Form field components (reference: cotton/checkbox/index.html, cotton/text_field.html)
- Labelled fields (Text Field, Textarea, Select, Date Field …) wrap their control in
  <c-field-layout> (label row, asterisk, help icon, helper; errors replace the helper);
  never rebuild the label row per field.
- Take a BoundField via :field="form.x" and read name (field.html_name), id
  (field.id_for_label), label, value, required (field.field.required), help_text and
  errors from it; plain props (label, name, value, id …) are the fallback.
- Field on the LEFT of |default: {% with input_name=field.html_name|default:name %}.
  As a filter argument (name|default:field.html_name) it raises when no field is passed.
- Exception to the attrs rule: {{ attrs }} go on the <input>/<select>/<textarea> (so
  x-model, disabled, aria-* reach it); class goes on the wrapper.
- Errors: aria-invalid="true" and aria-describedby → {{ input_id }}-help / -error.
- @tailwindcss/forms styles native inputs globally. Custom-drawn controls (checkbox,
  switch) keep the native input transparent (peer … opacity-0) and draw the visual with
  peer-checked: / peer-focus-visible: siblings.
- Focus, buttons and custom controls: focus-visible:outline-2 outline-offset-2
  outline-focus.
- Text-like controls (input, textarea, select): Figma's 2px focus/error border is
  border + 1px inset ring, which also replaces the forms plugin's blue ring:
    focus:border-focus focus:ring-1 focus:ring-inset focus:ring-focus
    errors: border-danger ring-1 ring-inset ring-danger (else border-strong)

### Alpine.js inside cotton
- On <c-…> tags a leading `:` is cotton's, not Alpine's: use x-bind:class and x-on:click
  there (x-on: over @ for consistency). Shorthand (:class, @click) is fine on normal
  elements inside a component.
- Interactive Figma variants (Expanded, hover, open) → Alpine state when the user toggles
  them, cotton props when the server decides (e.g. the current nav item).
- x-data on the component's root for its own state; on a common parent in the page for
  shared state.
- x-cloak on anything Alpine hides at load ([x-cloak]{display:none} is in input.css).

### Icons and assets
- Figma icons are Lucide (24px grid, 1.75 stroke): <c-icon name="check" class="size-4
  text-success" />, never figma.com/api/mcp/asset URLs, never <img> (can't be recolored).
- c-icon inlines the shapes of idat/templates/icons/<name>.svg ({% icon_content name %})
  and sets size, stroke and aria itself, so currentColor and dark mode work.
- Icon files are complete, valid SVGs (24×24 viewBox, stroke="currentColor") with an XML
  comment above the root (<!-- Lucide "x" (ISC licence) … -->), never {# #}.
- Other images: idat/static/img/, via {% load static %} … {% static 'img/…' %}.
