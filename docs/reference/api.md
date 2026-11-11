# REST API

The API is built with [django-ninja](https://django-ninja.dev/) in `config/api.py` and
mounted at `/api/`. Interactive OpenAPI docs are at **`/api/docs`** (staff users only).

Authentication defaults to the Django session; endpoints marked *public* need none.
