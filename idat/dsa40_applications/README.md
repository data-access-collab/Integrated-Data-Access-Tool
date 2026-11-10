# DSA40 Applications

This Django App manages DSA40 applications.

Core features:

- **Application Model**: Provides a DB model to store an application (not implemented)
- **Form Wizard**: Provides both anonymous and logged-in users a form wizard to create an application
- **Application Overview**: Provides logged-in users with an overview of their created applications - both drafts and submitted (not implemented)
- **Edit applications**: Provides logged-in users with a form to edit their draft applications (not implemented)

## Form Wizard for Application Creation

The form wizard gathers and renders all necessary questions for a set of
chosen VLOPSEs. For this, it uses the `dsa40_form_handler` app: `QuestionMapper`
merges the selected VLOPSEs' questions into one set of DSA questions, and
`AnswerTransformer` maps the answers back to each VLOPSE's own questions.

It consists of these steps (URL slug in brackets):

1. *Choose platforms* (`choose-vlopses`): select the VLOPSEs for which a DSA40
   application should be created.
2. *Enter details* (`enter-details`): answer the DSA questions the selected VLOPSEs
   need, one section (question category, see `sections.py`) at a time.
3. *Review* (`review`): the answers, read-only. Continuing re-validates the stored
   answers; the page itself submits none.
4. *Generate* (`generate`): one read-only application per VLOPSE, i.e. the answers
   mapped to that platform's questions (`services/applications.py`), with any mapping
   errors. Saving the applications (requires an account) is not implemented yet.
5. *Submit* (`submit`): planned, not implemented yet.

### How the steps work

- Each step is a `WizardFormStep` view in `views.py` (form, template, prerequisites,
  `next_step`). All steps share one URL pattern, `create/<step>/`, routed by
  `STEP_VIEWS`.
- Steps are htmx partials swapped into `#application-wizard-body`. A plain page load
  (reload, typed URL, history restore) returns the shell (`base.html`), which then
  requests the step with the state token (see below).
- A step whose prerequisites aren't met (e.g. no VLOPSE selected, or on Review a
  question the details step hasn't stored an answer for) renders the step to fix instead (`go_to`).
- Review and Generate render the provided answers read-only.

### How answers are stored

Before a draft is saved, answers aren’t stored on the server.
Instead, a `WizardState` (draft ID, selected VLOPSEs, answers) travels as an encrypted
token (Fernet, key derived from `DJANGO_WIZARD_SECRET`) in the `X-Wizard-State`
header.
The token expires 6 hours after the last step (sliding); changing the secret
invalidates all open drafts.

**Why a token:** the wizard works without an account, so the draft lives in the
browser, per tab. Server-side storage (database or Django session) would keep
personal answers of abandoned, anonymous drafts on the server, and a session cookie
is shared by all tabs, so drafts in two tabs would overwrite each other. Keeping the
draft in the browser as an encrypted, authenticated token instead gives:

1. **Server-enforced expiry (the main reason).** Only the server can tell whether a
   token is still valid (Fernet TTL), and it hands out the file key
   (`X-Wizard-File-Key`) only along with a valid token. So once the token expires,
   the draft's files in IndexedDB can no longer be decrypted, whatever the browser
   keeps. With plain state in sessionStorage, anyone at the device could read the
   draft ID and get the key at any time; expiry would be up to the browser.
2. **Integrity.** The browser can't alter the state (e.g. the draft ID or the
   selected VLOPSEs) without the server noticing; a tampered token resets the draft.
3. **Confidentiality, as a side effect.** The answers aren't readable in browser
   storage. As sessionStorage is per tab and short-lived, this matters least, but
   browsers do restore it when a closed tab is reopened.

*On the server side*, the information stored in the token is used to validate/render
the form and persist answers between steps.

*On the client side*, the token is stored in the tab-bound sessionStorage, so
that the token survives tab reloads but a separate tab will get its own WizardState.

**How the token is attached to requests:** The forms hold only
the CSRF token and the fields; `wizard.js` adds the state to every htmx request:

- `htmx:configRequest` reads the token from sessionStorage and sends it as the
  `X-Wizard-State` request header (form posts and `hx-get` links alike).
- Every step response carries a re-issued token (`add_response_headers`, also on
  GET, which makes the expiry sliding); `htmx:afterRequest` stores it in
  sessionStorage.
- The first step request has no token yet: the server starts an empty state with a
  new draft ID (`load_wizard_state`), whose token comes back with that response.

So only htmx requests carry the state: a step must use `hx-post` / `hx-get`, never a
plain `<form method="post">` or link. A plain page
load returns the shell (`base.html`), which then requests the step through htmx.

This logic lives in `state.py` (server) and `static/dsa40_applications/wizard.js`
(client).

### How file uploads are handled

Before a draft is saved, selected files never reach the server. The browser stores
them encrypted in IndexedDB, and they can only be decrypted while the tab's state
token is valid (see above). This keeps them unreadable for other users of a shared
device; although whoever can use the tab within the token's TTL can continue the draft,
including its files.

Implementation details:

- `ClientFileWidget` (`ui_component = "file"`) is rendered by `<c-file-upload>`: an
  unnamed file input (never submitted) and a hidden input. The `clientFile` Alpine
  component in `wizard.js` drives it, so it only works on wizard pages. On selection,
  the browser checks the file (allowed extension, max. 10 MB,
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
