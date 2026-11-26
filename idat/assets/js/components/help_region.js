/*
 * Alpine state for <c-help.region> (idat/templates/cotton/help/region.html): whether the
 * help panel is open, and what open means at the current width.
 *
 * - Wide (Tailwind xl, 1280px and up): the panel sits in the flow and starts open unless
 *   the viewer minimised it before (remembered in localStorage; storage may be blocked).
 * - Narrower: the panel starts closed and, when open, overlays the main area. Opening
 *   moves focus into it; closing while focus is inside returns it to the rail.
 *
 * The rail and panel buttons dispatch "help-panel" { open }; a field's help icon
 * dispatches "help-tip" { tip }, which opens the panel too.
 *
 * `question`: the active question (a help-tip id, e.g. a field name), whose tips the
 * panel shows instead of the general ones; "" for the general tips. Set by "help-tip"
 * (help icon) and "help-question" { question } (e.g. a focused field; doesn't open the
 * panel), both on window.
 */
const WIDE = "(min-width: 80rem)";
const STORAGE_KEY = "idat.helpOpen";

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStored(open) {
  try {
    localStorage.setItem(STORAGE_KEY, String(open));
  } catch {
    // blocked storage: the choice just isn't remembered
  }
}

export default function helpRegion() {
  return {
    open: false,
    question: "",

    isWide() {
      return window.matchMedia(WIDE).matches;
    },

    init() {
      this.open = this.isWide() && readStored() !== "false";
      this.$watch("open", (open) => {
        if (this.isWide()) {
          writeStored(open);
        } else if (open) {
          this.$nextTick(() => this.$refs.panel.querySelector("button")?.focus());
        } else if (this.$refs.panel.contains(document.activeElement)) {
          this.$refs.rail.querySelector("button")?.focus();
        }
      });
    },

    /* Esc and clicks next to the panel close it only where it overlays the page. */
    dismiss() {
      if (this.open && !this.isWide()) this.open = false;
    },
  };
}
