/*
 * DSA40 application wizard (idat/dsa40_applications)
 *
 * Served as a static ES module (imported with type="module"), only on the wizard page.
 * The server keeps no state: the encrypted wizard state travels in the
 * X-Wizard-State header and is kept in the tab-bound sessionStorage.
 * Files never leave the browser. They are encrypted with a per-draft key the
 * server sends with every step (X-Wizard-File-Key, kept in memory only) and
 * stored in IndexedDB; only their metadata is submitted.
 * IndexedDB is shared by all tabs, each of which has its own draft: stored files
 * expire like the token (X-Wizard-Max-Age, sliding), not when another tab starts.
 */

const STATE_KEY = "dsa40-wizard-state";
const DB_NAME = "dsa40-wizard";
const STORE = "files";

let wizardId = null;
let fileKey = null; // Promise<CryptoKey>
let maxAgeMs = 0;

/* IndexedDB */

function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore(mode, fn) {
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const result = fn(tx.objectStore(STORE));
      tx.oncomplete = () => resolve(result?.result);
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

const storedFileId = (question) => `${wizardId}:${question}`;

const getStoredFile = (question) => withStore("readonly", (store) => store.get(storedFileId(question)));

const deleteStoredFile = (question) => withStore("readwrite", (store) => store.delete(storedFileId(question)));

/**
 * Refresh the last-seen time of the current draft's files and delete files of
 * drafts not seen for longer than the token TTL: their token has expired, so
 * their key can't be derived anymore.
 */
function touchStoredFiles() {
  const now = Date.now();
  return withStore("readwrite", (store) => {
    store.openCursor().onsuccess = (event) => {
      const cursor = event.target.result;
      if (!cursor) return;
      const storedFile = cursor.value;
      if (storedFile.wizardId === wizardId) cursor.update({ ...storedFile, lastSeen: now });
      // negated, so stored files without lastSeen are deleted too
      else if (!(now - storedFile.lastSeen <= maxAgeMs)) cursor.delete();
      cursor.continue();
    };
  });
}

/** Delete all files of the current draft. */
function deleteDraftStoredFiles() {
  return withStore("readwrite", (store) => {
    store.openCursor().onsuccess = (event) => {
      const cursor = event.target.result;
      if (!cursor) return;
      if (cursor.value.wizardId === wizardId) cursor.delete();
      cursor.continue();
    };
  });
}

/* Crypto */

/**
 * Turn the X-Wizard-File-Key header (base64url, unpadded) into a non-extractable
 * AES-GCM CryptoKey for encrypting and decrypting this draft's stored files.
 */
function importKey(encoded) {
  const base64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
  const raw = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
}

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function storeFile(question, buffer) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await fileKey, buffer);
  await withStore("readwrite", (store) =>
    store.put({ id: storedFileId(question), wizardId, lastSeen: Date.now(), iv, ciphertext }),
  );
}

/** Decrypted files of the current draft, keyed by question (for saving the application). */
export async function getDecryptedFiles() {
  const storedFiles = await withStore("readonly", (store) => store.getAll());
  const files = {};
  for (const { id, wizardId: storedFileWizardId, iv, ciphertext } of storedFiles) {
    if (storedFileWizardId !== wizardId) continue;
    const question = id.slice(wizardId.length + 1);  // cut of wizardId + :
    files[question] = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, await fileKey, ciphertext);
  }
  return files;
}

/* Validation */

/**
 * Check a selected file against the widget's allowed types (extension) and max.
 * size, and that it isn't empty. Returns its contents and the metadata to submit;
 * throws an Error with a user-facing message otherwise.
 */
async function validateFile(file, { maxSize, types }) {
  const extension = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : "";
  if (!(extension in types)) {
    throw new Error(`Only these file types are allowed: ${Object.keys(types).join(", ")}.`);
  }
  if (file.size > maxSize) {
    throw new Error(`The file must not be larger than ${Math.round(maxSize / 1024 / 1024)} MB.`);
  }
  if (file.size === 0) throw new Error("The file is empty.");

  // the content isn't checked here; that happens on the server when it is saved
  const buffer = await file.arrayBuffer();
  return { buffer, metadata: { name: file.name, size: file.size, type: types[extension], sha256: await sha256(buffer) } };
}

/* Draft lifecycle */

async function discardDraft() {
  try {
    sessionStorage.removeItem(STATE_KEY);
  } catch {}
  if (wizardId) await deleteDraftStoredFiles();
  wizardId = null;
  fileKey = null;
}

/**
 * Listen on document.body for:
 * - htmx:configRequest: send the state token (X-Wizard-State) with every request
 * - htmx:beforeSwap: take the draft id, file key and TTL from step responses and
 *   refresh/expire stored files
 * - htmx:afterRequest: keep the re-issued state token in sessionStorage
 * - wizard-done: discard the draft (once saved; not dispatched yet)
 * - wizard-discard: discard the draft and go to event.detail.href ("Discard draft")
 */
function registerListeners() {
  document.body.addEventListener("htmx:configRequest", (e) => {
    const token = sessionStorage.getItem(STATE_KEY);
    if (token) e.detail.headers["X-Wizard-State"] = token;
  });

  // before the swap, so file widgets in the new content find the key
  document.body.addEventListener("htmx:beforeSwap", (e) => {
    const xhr = e.detail.xhr;
    const id = xhr.getResponseHeader("X-Wizard-Id");
    const key = xhr.getResponseHeader("X-Wizard-File-Key");
    if (!id || !key) return;
    if (id !== wizardId) {
      wizardId = id;
      fileKey = importKey(key);
    }
    maxAgeMs = Number(xhr.getResponseHeader("X-Wizard-Max-Age")) * 1000;
    // on every step response, as the server re-issues the token on each
    touchStoredFiles().catch(console.error);
  });

  document.body.addEventListener("htmx:afterRequest", (e) => {
    const token = e.detail.xhr.getResponseHeader("X-Wizard-State");
    if (token) sessionStorage.setItem(STATE_KEY, token);
  });

  document.body.addEventListener("wizard-done", () => discardDraft().catch(console.error));

  document.body.addEventListener("wizard-discard", async (e) => {
    await discardDraft().catch(console.error);
    window.location.assign(e.detail.href);
  });
}

/* Alpine component for ClientFileWidget */

/**
 * State and behaviour of one ClientFileWidget (x-data="clientFile"). It reads
 * the field's config from data-* attributes and keeps `metadata` in sync with the
 * submitted hidden input (x-ref="metadataInput"):
 * - metadata: {name, size, type, sha256} of the selected file, or null
 * - missing: metadata is set, but the file isn't stored in this browser
 * - busy: a selected file is being validated and encrypted
 * - error: user-facing validation error
 */
function clientFile() {
  return {
    metadata: null,
    missing: false,
    busy: false,
    error: "",

    get question() {
      return this.$root.dataset.question;
    },

    get label() {
      if (!this.metadata) return "";
      const { name, size } = this.metadata;
      if (size < 1024) return `${name} (${size} bytes)`;
      if (size < 1024 * 1024) return `${name} (${(size / 1024).toFixed(1)} KB)`;
      return `${name} (${(size / 1024 / 1024).toFixed(1)} MB)`;
    },

    async init() {
      const value = this.$refs.metadataInput.value;
      this.metadata = value ? JSON.parse(value) : null;
      if (this.metadata && wizardId) this.missing = !(await getStoredFile(this.question));
    },

    async select(event) {
      const file = event.target.files[0];
      if (!file) return;
      this.error = "";
      this.busy = true;
      try {
        const { buffer, metadata } = await validateFile(file, {
          maxSize: Number(this.$root.dataset.maxSize),
          types: JSON.parse(this.$root.dataset.types),
        });
        if (!fileKey) throw new Error("Please reload the page and try again.");
        await storeFile(this.question, buffer);
        this.metadata = metadata;
        this.missing = false;
        this.$refs.metadataInput.value = JSON.stringify(metadata);
      } catch (err) {
        this.error = err.message;
      } finally {
        this.busy = false;
        event.target.value = ""; // the file input is never submitted
      }
    },

    async remove() {
      if (wizardId) await deleteStoredFile(this.question);
      this.metadata = null;
      this.missing = false;
      this.$refs.metadataInput.value = "";
    },
  };
}

registerListeners();

// fired by Alpine.start() in main.js, which runs after this deferred module
document.addEventListener("alpine:init", () => window.Alpine.data("clientFile", clientFile));
