TODO: Integrate into refactored docs once they are merged into the codebase

## Mailpit for local email testing

[Mailpit](https://mailpit.axllent.org/) is a free, open-source SMTP testing tool.
Use it to test emails sent by IDAT (incl. their HTML versions).

By default, the local Django container logs emails to the console using its
`django.core.mail.backends.console.EmailBackend`.

To enable Mailpit, edit or create `.envs/.local/.dev-local` and add:

    DJANGO_USE_MAILPIT=True

Recreate the Django container for the settings update to apply:

    just up

Then start the Mailpit container:

    just mailpit
    # just stop-mailpit

The Mailpit client is now accessible at http://localhost:8025/, its SMTP server
listens to localhost:1025. It automatically intercepts and displays all emails
sent by Django.
