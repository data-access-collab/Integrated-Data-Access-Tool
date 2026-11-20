# Contributing

## Branches and pull requests

### Branches

| Branch                               | Purpose                                             |
|--------------------------------------|-----------------------------------------------------|
| `main`                               | Default branch, always deployable                   | 
| `dev`                                | Integration branch; merged into `main` for releases |
| `feat/…`, `fix/…`, `refactor/…` etc. | Short-lived branches off `dev`, merged back via PR  |


### PRs

- Open a pull request against `dev`. CI must pass (see
  [Testing & quality](../setup/testing.md)).
- No direct commits to `main` - everything goes through dev → PR → dev → main:

    * One PR = one clearly scoped slice of a WP task
    * At least **one review from the other developer** before merging
    * CI must pass (lint, tests, build) before merge
    * Squash-merge to `dev` to keep a clean, readable history + delete the branch after merge
  
- Keep branches short-lived (days, not weeks) — split large WPs (like T1) into smaller PRs
  where possible rather than one giant branch.

A task/PR is "done" when:

- [ ] Code is merged to `dev` via a reviewed PR
- [ ] **Test coverage:** Automated tests cover the new behavior (unit tests minimum; integration tests for
      cross-cutting features like auth, consent, or the mapping engine)
- [ ] `python manage.py check --deploy` passes with no new warnings, where relevant
- [ ] **Accessibility requirements checked:**

    | Resource                                                                  | Purpose                                                      |
    |---------------------------------------------------------------------------|--------------------------------------------------------------|
    | [WCAG 2.1 AA](https://www.w3.org/TR/WCAG21/)                              | Accessibility standard new UI must meet                      |
    | [WCAG 2 Checklist](https://webaim.org/standards/wcag/checklist) (WebAIM)  | Practical checklist for the WCAG criteria                    |
    | [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/) (W3C)  | Accessible patterns for widgets and ARIA usage               |
    | [axe-core](https://www.npmjs.com/package/axe-core)                        | Run locally for automated accessibility checks on any new UI |

- [ ] **Security requirements checked:**

    | Resource                                                                                            | Purpose                                                                       |
    |-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
    | [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/) | Settings and hardening to check before deploying                              |
    | [Security Headers](https://securityheaders.com/) (Snyk)                                             | Check the site's HTTP security headers                                        |
    | [HTTP Observatory](https://developer.mozilla.org/en-US/observatory) (Mozilla)                       | Second check of headers and HTTP security                                     |
    | [OWASP Top 10](https://top10.owasp.org/2025/0x00_2025-Introduction/)                                | Common risks to review for anything touching auth, file uploads or user input |
    | [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/index.html)                                 | Specific guidance for auth, file uploads and user input                       |


- [ ] **Docs:** Relevant docs updated (README, install guide, or inline docstrings) if behavior or
      setup steps changed


## Commit messages

Commits are based on [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`,
for example `feat: add question categories and model admins` or
`refactor(t1): Create core app`.

Common types:
  - `feat`: new functionality
  - `fix`: bug fixes
  - `chore`: tooling, CI, dependency bumps, non-code housekeeping
  - `docs`: documentation
  - `test`: adding/fixing tests with no behavior change
  - `refactor`: Restructuring code with no functional change

Issues can be referenced in commit messages using `Refs:`.

## In this section

- [UI library](ui-library.md): design tokens, cotton components, the Figma source of truth.
- [Figma sync](figma-sync.md): importing and updating components from Figma.
- [Docs](docs.md): writing and previewing this documentation.
