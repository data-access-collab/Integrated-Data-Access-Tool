/*
 * Alpine state for <c-date-field> (idat/templates/cotton/date_field.html).
 *
 * The visible input takes "DD / MM / YYYY" (any separator); the hidden input submits
 * ISO "YYYY-MM-DD", which Django's DateField always accepts. Text that doesn't parse is
 * submitted as typed, so Django's own "Enter a valid date." error still applies.
 */
const pad = (n) => String(n).padStart(2, "0");
const toIso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const toDisplay = (d) => `${pad(d.getDate())} / ${pad(d.getMonth() + 1)} / ${d.getFullYear()}`;

function makeDate(year, month, day) {
  const d = new Date(year, month - 1, day);
  // Rejects 31 / 02 and similar roll-overs.
  return d.getFullYear() === year && d.getMonth() === month - 1 && d.getDate() === day ? d : null;
}

function parse(text) {
  const iso = /^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$/.exec(text);
  if (iso) return makeDate(+iso[1], +iso[2], +iso[3]);
  const dmy = /^\s*(\d{1,2})\D+(\d{1,2})\D+(\d{4})\s*$/.exec(text);
  if (dmy) return makeDate(+dmy[3], +dmy[2], +dmy[1]);
  return null;
}

export default function dateField(initial = "") {
  return {
    open: false,
    text: "",
    selected: null,
    month: null, // first day of the month shown in the calendar

    init() {
      this.selected = parse(initial);
      this.text = this.selected ? toDisplay(this.selected) : initial;
      this.month = this.firstOfMonth(this.selected || new Date());
    },

    get submitted() {
      return this.selected ? toIso(this.selected) : this.text.trim();
    },

    get locale() {
      return document.documentElement.lang || undefined;
    },

    get monthLabel() {
      return new Intl.DateTimeFormat(this.locale, { month: "long", year: "numeric" }).format(this.month);
    },

    get weekdays() {
      // 2024-01-01 is a Monday; the week starts on Monday.
      const fmt = new Intl.DateTimeFormat(this.locale, { weekday: "short" });
      return Array.from({ length: 7 }, (_, i) => fmt.format(new Date(2024, 0, 1 + i)).slice(0, 2));
    },

    // Leading nulls pad the first week so day 1 falls on its weekday.
    get days() {
      const y = this.month.getFullYear();
      const m = this.month.getMonth();
      const lead = (this.month.getDay() + 6) % 7;
      const count = new Date(y, m + 1, 0).getDate();
      const fmt = new Intl.DateTimeFormat(this.locale, { dateStyle: "full" });
      const cells = Array.from({ length: lead }, () => null);
      for (let day = 1; day <= count; day++) {
        const date = new Date(y, m, day);
        cells.push({ day, date, label: fmt.format(date) });
      }
      return cells;
    },

    firstOfMonth(d) {
      return new Date(d.getFullYear(), d.getMonth(), 1);
    },

    isSelected(cell) {
      return cell && this.selected && toIso(cell.date) === toIso(this.selected);
    },

    shiftMonth(step) {
      this.month = new Date(this.month.getFullYear(), this.month.getMonth() + step, 1);
    },

    toggle() {
      if (this.open) return this.close();
      this.month = this.firstOfMonth(this.selected || new Date());
      this.open = true;
      // Focus the selected day (or day 1) so the calendar is keyboard-usable straight away.
      // x-show reveals the calendar in an animation frame, so focus in the frame after that.
      this.$nextTick(() =>
        requestAnimationFrame(() => {
          const cal = this.$refs.calendar;
          (cal.querySelector("[aria-pressed=true]") || cal.querySelector("[data-day]"))?.focus();
        }),
      );
    },

    typed() {
      this.selected = parse(this.text);
      if (this.selected) this.month = this.firstOfMonth(this.selected);
    },

    choose(cell) {
      this.selected = cell.date;
      this.text = toDisplay(cell.date);
      this.open = false;
      this.$nextTick(() => {
        this.$refs.input.focus();
        this.$refs.input.dispatchEvent(new Event("change", { bubbles: true }));
      });
    },

    close(refocus = false) {
      if (!this.open) return;
      this.open = false;
      if (refocus) this.$refs.toggle.focus();
    },
  };
}
