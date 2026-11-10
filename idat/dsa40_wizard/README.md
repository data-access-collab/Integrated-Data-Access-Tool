# DSA40 Wizard

This Django App provides both anonymous and logged-in users a form wizard to
create DSA40 data access applications for a set of selected VLOPSE.

## Form Wizard for Application Creation

The form wizard gathers and renders all necessary DSAQuestions for a set of
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
4. *Generate* (`generate`): one read-only application preview per VLOPSE, i.e. the answers
   mapped to that platform's questions (`services/preview.py`), with any mapping
   errors. Saving the applications (requires an account) is not implemented yet.
5. *Submit* (`submit`): planned, not implemented yet.

### How the steps work

- Each step is a `WizardFormStep` view in `views.py` (form, template, prerequisites,
  `next_step`). All steps share two URL patterns, routed by `STEP_VIEWS`:
  `create/<step>/` shows a step, `create/<step>/submit/` (the step forms) submits it.
- Steps are htmx partials swapped into `#application-wizard-body`. A plain page load
  (reload, typed URL, history restore) returns the shell (`base.html`), which then
  requests the step with the state token (see below).
- A step whose prerequisites aren't met (e.g. no VLOPSE selected, or on Review a
  question the details step hasn't stored an answer for) renders the step to fix instead (`go_to`).

### How answers are stored

Before a draft is saved, answers aren’t stored on the server.
Instead, a `WizardState` (draft ID, selected VLOPSEs, answers) travels as an encrypted
token (Fernet, key derived from `DJANGO_WIZARD_SECRET`) between browser and server.
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
   storage.

**How the token is attached to requests:** The forms hold only the CSRF token and the
fields; `wizard.js` adds the state to every htmx request:

- `htmx:configRequest` reads the token from sessionStorage and sends it as the
  `wizard_state` POST parameter (decided against sending it as a request header because
  the token grows with the answers, and servers and proxies limit header size).
- Every step response carries a re-issued token in the `X-Wizard-State` response
  header (`add_response_headers`, which makes the expiry sliding);
  `htmx:afterRequest` stores it in sessionStorage.
- The first step request has no token yet: the server starts an empty state with a
  new draft ID (`load_wizard_state`), whose token comes back with that response.

So every wizard request is an htmx **POST** (`hx-post`, never `hx-get`, a plain
`<form method="post">` or a link); an htmx GET is rejected. As the method no longer
tells them apart, the URL does: step forms post to `wizard_submit`, everything else
(shell load, Back) to `wizard_step`, which only shows the step.

This logic lives in `state.py` (server) and `static/dsa40_wizard`
(client).

### How file uploads are handled

Before a draft is saved, selected files never reach the server. The browser stores
them encrypted in IndexedDB, and they can only be decrypted while the tab's state
token is valid (see above). This keeps them unreadable for other users of a shared
device; although whoever can use the tab within the token's TTL can continue the draft,
including its files.

How the parts work together:

- The browser checks, hashes and encrypts a selected file and stores it in
  IndexedDB (`clientFile` in `wizard.js`); only its metadata is submitted and kept
  in the state (`ClientFileField` in `forms.py`).
- The key is per draft and comes with every step response (`X-Wizard-File-Key`),
  i.e. only alongside a valid token; the browser keeps it in memory only.
- IndexedDB is shared by all tabs, so files expire by last-seen time and the token
  TTL rather than per tab: files of abandoned drafts stay, unreadable, until the
  wizard is used again in that browser.
- "Discard draft" deletes the token, the key and the draft's files.

**Saving (not implemented yet):** the browser uploads the decrypted files
(`getDecryptedFiles()`). The server must validate them against their actual content
(type against `CLIENT_FILE_TYPES`, size, SHA-256), as nothing the browser reports
can be trusted, before storing them.

The client-side logic lives in `static/dsa40_wizard`, a static ES
module loaded on the wizard page only; the saving logic should live in this
file too.
