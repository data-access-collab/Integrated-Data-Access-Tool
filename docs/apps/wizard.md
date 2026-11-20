# Application Wizard

`idat.dsa40_wizard` guides a researcher, with or without an account, through creating
DSA 40 applications for a set of selected VLOPSEs. It uses the
[form handler](form-handler.md): `QuestionMapper` merges the platforms' questions into
one questionnaire, and `AnswerTransformer` maps the answers back to each platform.

## Steps

| Step             | Slug             | View                  | Does                                                                       |
|------------------|------------------|-----------------------|----------------------------------------------------------------------------|
| Choose platforms | `choose-vlopses` | `VlopseSelectionStep` | Select VLOPSEs; drops answers no longer needed                             |
| Enter details    | `enter-details`  | `QuestionsStep`       | Answer the mapped DSA questions, one section at a time                     |
| Review           | `review`         | `ReviewStep`          | Stored answers, read-only; continuing re-validates them, submits none      |
| Generate         | `generate`       | `GenerateStep`        | One read-only preview per VLOPSE, with any mapping errors                  |
| Submit           | `submit`         | none                  | Planned; its URL returns 404                                               |

Each step subclasses `WizardFormStep` (`views.py`): a form, a template, `next_step` and
`check_prerequisites`. A step whose prerequisites fail (no valid VLOPSE selected, an
unanswered question on Review) renders the step to fix instead (`go_to`).

Enter details groups its questions by `QuestionCategory`; `sections.py` sets each
section's order, icon and description, with *Other* (general category) last. Generate
builds its previews in `services/preview.py`.

## URLs

Mounted under `/applications/` (`urls.py`):

| URL                     | Name                | Does                                                        |
|-------------------------|---------------------|-------------------------------------------------------------|
| `create/`               | `create`            | Wizard shell, starting at Choose platforms                  |
| `create/<step>/`        | `wizard_step`       | Shows a step                                                |
| `create/<step>/submit/` | `wizard_submit`     | Submits a step's form                                       |
| `create/<step>/save/`   | `wizard_save`       | Stores answers without validating them (Enter details only) |
| `draft-unavailable/`    | `draft_unavailable` | Shown when a draft can't be loaded                          |

`route_wizard_step` dispatches all step URLs to the view in `STEP_VIEWS`.

## Draft state

Until a draft is saved, nothing is stored on the server. A `WizardState` (draft ID,
selected VLOPSE IDs, answers) travels as a Fernet token (encrypted and authenticated,
key derived from `DJANGO_WIZARD_SECRET`) kept in the tab's sessionStorage (`state.py`).

**Why a token:** the wizard works without an account. Storing drafts on the server
(database or session) would keep personal answers of abandoned, anonymous drafts, and a
session cookie is shared by all tabs, so drafts in two tabs would overwrite each other.
The token gives:

1. **Server-enforced expiry**, the main reason. Only the server can tell whether a token
   is still valid, and it sends the file key only along with a valid one; once the token
   expires, the draft's files can't be decrypted, whatever the browser keeps.
2. **Integrity:** the browser can't alter the draft ID or the selected VLOPSEs unnoticed.
3. **Confidentiality**, as a side effect: answers aren't readable in browser storage.

How it works:

- `wizard.js` sends the token as the `wizard_state` POST parameter (`htmx:configRequest`);
  a header was ruled out because the token grows with the answers and servers and
  proxies limit header size.
- Every step response re-issues it in `X-Wizard-State` (stored on `htmx:afterRequest`),
  together with `X-Wizard-Id`, `X-Wizard-File-Key` and `X-Wizard-Max-Age`
  (`add_response_headers`).
- Tokens expire `MAX_STATE_AGE` (6 hours) after the last response (sliding). Rotating
  the secret invalidates all open drafts.
- Only Choose platforms starts a new draft without a token (`load_wizard_state` creates
  an empty state with a new draft ID). An expired or tampered token, or none on a later
  step (e.g. its URL opened in another tab), answers 204 with
  `X-Wizard-Draft-Unavailable`; the browser discards the draft and goes to the
  draft-unavailable page.

## File uploads

Before a draft is saved, files never reach the server:

- The browser checks, hashes (SHA-256) and encrypts a selected file, and stores it in
  IndexedDB (`clientFile` in `wizard.js`); only its metadata is submitted and kept in
  the state (`ClientFileField` in `forms.py`).
- The key is per draft, comes with every step response and is kept in memory only.
- IndexedDB is shared by all tabs, so files expire by last-seen time and the token TTL,
  not per tab: files of abandoned drafts stay, unreadable, until the wizard is used again
  in that browser.
- "Discard draft" and an unavailable draft delete the token, the key and the draft's
  files. The draft ID is kept in sessionStorage next to the token, so this also works
  after a reload.

This keeps files unreadable for other users of a shared device, though whoever uses the
tab within the TTL can continue the draft, files included.

**Saving (not implemented yet):** creating the applications will require an account.
The browser uploads the decrypted files (`getDecryptedFiles()`); the server must validate
them against their actual content (type against `CLIENT_FILE_TYPES`, size, SHA-256),
since nothing the browser reports can be trusted, before storing them. The client-side
saving logic belongs in `wizard.js`.

## htmx and Alpine

- Every wizard request is an htmx POST (`hx-post`), since it carries the token; an htmx
  GET is rejected, so never use `hx-get`, a plain `<form method="post">` or a link. The
  URL, not the method, tells showing, submitting and saving apart.
- A plain page load (reload, typed URL) or a history restore returns the shell
  (`base.html`), which then requests the step into `#application-wizard-body`.
- Steps render through `_step.html` (step template plus an out-of-band sidebar).
- On Enter details, all sections stay in one form; Alpine's `section` state shows one at
  a time. Answers are saved in the background on a section switch, a file change and
  after 30 seconds without typing; "Back to platforms" and sidebar step links save
  before switching step (`save/?next=`).
- `static/dsa40_wizard/wizard.js` is an ES module loaded on the wizard page only: it
  attaches and stores the token, handles the file key and IndexedDB, "Discard draft",
  and the `clientFile` Alpine component.
