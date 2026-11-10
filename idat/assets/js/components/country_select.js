/*
 * Alpine state for <c-country-select> (idat/templates/cotton/country_select.html):
 * an ARIA 1.2 select-only button that turns into a searchable combobox while open.
 *
 * Options come from a JSON script element holding [[value, label], …] (optgroups already
 * flattened by the template; nested lists are flattened here too). The blank choice
 * ("", "Select a country…") becomes the placeholder.
 */
function flatten(choices, out = []) {
  for (const [value, label] of choices) {
    if (Array.isArray(label)) flatten(label, out);
    else out.push({ value: String(value), label: String(label) });
  }
  return out;
}

const fold = (text) =>
  text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();

export default function countrySelect(dataId, initial = "") {
  return {
    open: false,
    query: "",
    active: 0,
    value: initial,
    options: [],
    placeholder: "",

    init() {
      const all = flatten(JSON.parse(document.getElementById(dataId).textContent));
      this.placeholder = all.find((o) => o.value === "")?.label ?? "";
      // De-duplicate: a country may appear both in a "top" group and in the full list.
      const seen = new Set();
      this.options = all.filter((o) => o.value !== "" && !seen.has(o.value) && seen.add(o.value));
    },

    get selectedOption() {
      return this.options.find((o) => o.value === this.value) ?? null;
    },

    // Name contains the query (accents ignored), or the alpha-2 code equals it.
    get filtered() {
      const q = fold(this.query.trim());
      if (!q) return this.options;
      return this.options.filter((o) => o.value.toLowerCase() === q || fold(o.label).includes(q));
    },

    optionId(option) {
      return `${dataId}-${option.value}`;
    },

    get activeId() {
      const option = this.filtered[this.active];
      return option ? this.optionId(option) : null;
    },

    // x-show reveals elements in an animation frame, so focus in the frame after that.
    focusLater(ref) {
      this.$nextTick(() => requestAnimationFrame(() => this.$refs[ref].focus()));
    },

    openList() {
      this.query = "";
      this.active = Math.max(0, this.options.indexOf(this.selectedOption));
      this.open = true;
      this.focusLater("search");
      this.scrollToActive();
    },

    close(refocus = false) {
      if (!this.open) return;
      this.open = false;
      this.query = "";
      if (refocus) this.focusLater("button");
    },

    move(step) {
      const count = this.filtered.length;
      if (!count) return;
      this.active = (this.active + step + count) % count;
      this.scrollToActive();
    },

    scrollToActive() {
      this.$nextTick(() =>
        requestAnimationFrame(() => document.getElementById(this.activeId)?.scrollIntoView({ block: "nearest" })),
      );
    },

    pick(option) {
      if (!option) return;
      this.value = option.value;
      this.close(true);
      this.$nextTick(() => this.$refs.value.dispatchEvent(new Event("change", { bubbles: true })));
    },
  };
}
