# DSA40 Applications

This Django App manages DSA40 applications.

Core features:

- **Application Model**: Provides a DB model to store an application (not implemented)
- **Form Wizard**: Provides both anonymous and logged-in users a form wizard to create an application
- **Application Overview**: Provides logged-in users with an overview of their created applications - both drafts and submitted (not implemented)
- **Edit applications**: Provides logged-in users with a form to edit their draft applications (not implemented)

## Form Wizard for Application Creation

The form wizard gathers and renders all necessary questions for a set of
chosen VLOPSEs. For this, it uses the form handler included in the `dsa40`
app.

It consists of three steps:

1. *VLOPSE selection*: select the VLOPSEs for which a DSA40 application should be created.
2. *Questions*: fill out the questions for the selected VLOPSEs.
3. *Review*: display a summary of the answers to the user. Optionally, users can
save the application in IDAT (requires an account).

### How answers are stored

Before a draft is saved, answers aren’t stored on the server.
Instead, a `WizardState` (draft ID, selected VLOPSEs, answers) travels as an encrypted
token (Fernet, key derived from `DJANGO_WIZARD_SECRET`) in the `X-Wizard-State`
header, so it can’t be read from browser storage.
The token expires 6 hours after the last step (sliding); changing the secret
invalidates all open drafts.

*On the server side*, the information stored in the token is used to validate/render
the form and persist answers between steps.

*On the client side*, the token is stored in the tab-bound sessionStorage, so
that the token survives tab reloads but a separate tab will get its own WizardState.

This logic lives in `state.py`.

### How file uploads are handled

Before a draft is saved, selected files never reach the server. The browser stores
them encrypted in IndexedDB, and they can only be decrypted while the tab's state
token is valid (see above). This keeps them unreadable for other users of a shared
device; although whoever can use the tab within the token's TTL can continue the draft,
including its files.

Implementation details:

- `ClientFileWidget` renders an unnamed file input (never submitted) and a hidden
  input. On selection, the browser checks the file (allowed extension, max. 10 MB,
  not empty), computes its SHA-256 (for an integrity check on saving), encrypts it
  (AES-GCM) and stores it in IndexedDB. Only the metadata (`name`, `size`, `type`,
  `sha256`) is submitted via the hidden input.
- Accepted types are set per field (`ClientFileField(types=(".pdf", ...))`)
  from the catalog `CLIENT_FILE_TYPES` in `forms.py` (extension →
  content type); adding a type only needs a new entry.
- `ClientFileField` only checks the shape of the metadata and stores it in
  `WizardState.answers`.
- The encryption key is derived per draft from `DJANGO_WIZARD_SECRET` and the draft
  ID, sent with every step response (`X-Wizard-File-Key`) and kept in memory only.
- Stored files expire like the token: each step response refreshes the current
  draft's last-seen time and deletes files of drafts not seen for longer than the
  TTL (`X-Wizard-Max-Age`). Drafts in other tabs are thus kept; files of abandoned
  drafts stay (unreadable) until the wizard is used again in that browser.
- "Discard draft" deletes the state token, the file key and the current draft's
  stored files. The `wizard-done` event does the same (meant for after saving; not
  used yet).

**Saving (not implemented yet):** the browser uploads the decrypted files
(`getDecryptedFiles()`). The server must validate them against their actual content
(type against `CLIENT_FILE_TYPES`, size, SHA-256), as nothing the browser reports
can be trusted, before storing them.

The client-side logic lives in `static/dsa40_applications/wizard.js`, a static ES
module loaded on the wizard page only. In production, it has a hashed file name, so
other scripts can't easily import from it; the saving logic should live in this
file too.
