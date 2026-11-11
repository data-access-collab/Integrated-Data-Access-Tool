# Local development

## Start the stack

Build the images once, then start Django, PostgreSQL and Redis:

=== "just"

    ```bash
    just build
    just up
    just logs  # follow the container
    just down
    ```

=== "Docker Compose"

    ```bash
    docker compose -f docker-compose.local.yml build
    docker compose -f docker-compose.local.yml up
    ```

The app runs at <http://localhost:8000>.

Migrations also load the seed data: VLOPSEs and the DSA and VLOPSE questions (see
[VLOPSE](../apps/vlopse.md) and [Form handler](../apps/form-handler.md)).


=== "just"

    ```bash
    just manage migrate
    ```

=== "Docker Compose"

    ```bash
    docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
    ```

## Users

- **Normal user:** sign up through the site. The verification email is printed to the
  Django container's console; open the link in it to verify the address.
- **Superuser:**

    === "just"
    
        ```bash
        just manage createsuperuser
        ```
    
    === "Docker Compose"

        ```bash
        docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser
        ```

## Useful URLs (DEBUG only)

| URL                 | What                                                                   |
|---------------------|------------------------------------------------------------------------|
| `/dev/components/`  | Component gallery, see [UI library](../contributing/ui-library.md)     |
| `/api/docs`         | Interactive API docs (staff only), see [REST API](../reference/api.md) |
| `/400/` … `/500/`   | Error pages                                                            |
| `/__debug__/`       | Django Debug Toolbar                                                   |
