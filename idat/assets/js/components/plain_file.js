/*
 * Alpine state for <c-file-upload plain> (idat/templates/cotton/file_upload.html).
 *
 * A normal file input submitted with the form (multipart/form-data), no browser
 * encryption. It exposes the same state names as clientFile (wizard.js), so the
 * template's Empty / Stored / Error markup is shared:
 * - metadata: {name, size} of the selected file, or null
 * - error: user-facing validation error (accepted types, max. size, not empty)
 * - busy, missing, pending: always idle here
 * Config comes from data-accept (".pdf,.eml") and data-max-size (bytes) on the root.
 */
function sizeLabel(size) {
  if (size < 1024) return `${size} bytes`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function check(file, { accept, maxSize }) {
  const extension = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : "";
  const allowed = accept ? accept.split(",").map((type) => type.trim().toLowerCase()) : [];
  if (allowed.length && !allowed.includes(extension)) {
    return `Only these file types are allowed: ${allowed.join(", ")}.`;
  }
  if (maxSize && file.size > maxSize) {
    return `The file must not be larger than ${Math.round(maxSize / 1024 / 1024)} MB.`;
  }
  if (file.size === 0) return "The file is empty.";
  return "";
}

export default function plainFile() {
  return {
    metadata: null,
    missing: false,
    busy: false,
    pending: "",
    error: "",

    get sizeLabel() {
      return this.metadata ? sizeLabel(this.metadata.size) : "";
    },

    select(event) {
      const file = event.target.files[0];
      this.metadata = null;
      this.error = "";
      if (!file) return;
      this.error = check(file, {
        accept: this.$root.dataset.accept,
        maxSize: Number(this.$root.dataset.maxSize),
      });
      if (this.error) {
        event.target.value = ""; // don't submit a file that was rejected
        return;
      }
      this.metadata = { name: file.name, size: file.size };
    },

    async remove() {
      this.$refs.input.value = "";
      this.metadata = null;
      this.error = "";
    },
  };
}
