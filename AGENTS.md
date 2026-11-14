# AGENTS.md — Django Rapido

Authoritative instructions for AI agents working in this repository. These rules are
mandatory unless a rule explicitly says otherwise.

Read this file before changing code. `guides/` is the source of truth for how each
module works — read the guide for the app you are touching, keep it accurate, and
update it whenever your change alters documented behavior.

This file is the repo's single source of truth for conventions; when a decision is
missing, add it here — don't invent one ad-hoc.

## 1. Working principles

1. **Preserve behavior.** Make focused changes, preserve existing functionality, and avoid
   unrelated refactoring.
2. **Follow the architecture.** Keep HTTP handling, business logic,
   serialization, data retrieval and asynchronous work in their established layers.
3. **Treat API contracts as intentional.** Explicitly define fields, validation,
   permissions, nullability, and response structure.
4. **Test every meaningful change.** Add or update tests and run them; never weaken
   or delete tests to make a suite pass.
5. **Optimize by evidence.** Prevent N+1 queries, bound collections, and measure
   before introducing optimizations.
6. **Keep the consumer contract intact.** The API exists to serve clients (web, mobile,
   third parties). Backend changes must not guess what the client wants; the contract
   is the contract. Enforce authentication, ownership, and permissions on the backend.
7. **Do not invent behavior.** If documentation and implementation conflict, investigate.
   If intended behavior remains unclear, ask for clarification.
8. **Keep the template generic.** No product-domain constants, users, data or flows.
   `accounts` ships the multi-account auth engine; your app ships your domain. Do not
   hard-code roles, client IDs or business rules into reusable modules.

## 2. Documentation map

| Need | Source |
|------|--------|
| Documentation for every module (i18n, auth, Docker, Celery, notifications, …) | `guides/*.md` |
| Common/ reference (models, views, permissions, middleware, …) | `guides/common/*.md` |
| Conventions & architecture for this repo | this file |
| Environment variables and their meanings | `.env.example` (REUSE comments) |
| Scripts available | `Makefile` (`make quality` runs the full gate) |

When a change alters documented behavior, update the guide in the same change — or state
explicitly why the guide stays as it is.

## 3. Backend standards

### 3.1 Translatable model fields are mandatory

Any model field a user reads as text — names, titles, descriptions, labels, bodies, FAQ
copy, category names — **must** be registered for translation with `django-modeltranslation`.
Never ship an English-only text field, and never store Arabic in an untranslated field.

- Register fields in `<app>/translation.py`, following the reusable `TranslationOptions`
  pattern in `compliance/translation.py`.
- `guides/i18n guide.md` is the full guide.
- `fields` lists only genuinely translatable text — not provenance or index fields.
  Enumerations, codes, slugs and units stay untranslated.
- Serializers read translated attributes. Do not build bilingual pairs by hand.
- Write both locales (`_en`, `_ar`). `MODELTRANSLATION_FALLBACK_LANGUAGES` is a fallback, not a substitute.
- Keep `modeltranslation` before `django.contrib.admin` in `INSTALLED_APPS`.
- After registering, run `makemigrations` — modeltranslation adds `<field>_en` / `<field>_ar`
  columns to the same table.

### 3.2 NULL means "no data" — never fake zero

A missing value is `NULL` and renders as "no data". A `0` must only ever mean a measured
zero. Never coerce missing values to `0` during import, serialization, or display.
Preserve nullability across the API boundary: allow `null` explicitly where the answer
is genuinely absent.

### 3.3 Bulk import commands must be idempotent and self-verifying

Management commands that import datasets must:

- Upsert using a natural key; re-running the command produces identical counts.
- Print a final report: rows in, rows out, skipped, anomalies.
- Run the verification script before and after import, wherever one exists.

### 3.4 Tests use pytest

- Plain `test_*` functions with `pytest-django` marks; do not use `unittest.TestCase`.
- Run from the repo root: `python -m pytest`. `manage.py test` is not the test runner
  here and collects nothing.
- `python -m pytest -q` currently collects 15 tests. Keep the count honest.

### 3.5 Reads go through the layer's public surface

`models.py` holds models; querysets with non-trivial filtering live in the app's
manager or in a service, not inline in views. Plain `Model.objects.filter(...)` may
silently leak inactive or wrong-tenant rows — use the queryset the module exposes.
Admin, importer and reconciliation code may use the unfiltered manager.

### 3.6 Indexes for query patterns, not for luck

Filter, join, ordering and FK fields need reviewed indexes; composite indexes beat
several single-column ones for frequent two-column predicates. Inspect query plans
(`EXPLAIN`, `EXPLAIN ANALYZE`) for expensive queries before adding or removing indexes.
Never index blindly — every index taxes writes.

## 4. API and serializer standards

Serializers define the contract between the backend and its consumers. Their fields,
validation, representation and write behavior must be deliberate.

### 4.1 Explicit fields and protected data

- Explicitly declare every field. Never use `fields = "__all__"` in API serializers.
- Review every exposed field for suitability.
- Set `read_only_fields` for server-set fields (ids, timestamps, computed/protected data).
- Protect ownership, internal status and timestamps; clients cannot write them unless required.
- Use appropriate serializer field types with intentional `required`, `allow_null`,
  `allow_blank` and `default`.
- Keep names and types consistent with existing API conventions.

### 4.2 Validation

- `validate_<field>()` for field-specific validation; `validate()` for cross-field rules.
- Clear messages suitable for API consumers.
- Business constraints validate before operations.
- Use model validation and database constraints as backstops, never as the only layer.
- Never rely exclusively on frontend validation.

### 4.3 Read/write representations

- Separate read/write serializers only when responsibilities genuinely differ.
- Prefer explicit IDs for writable relations. Keep nested writes rare and justified.
- Nested reads must be fed by an optimized queryset (see §6.1). Do not re-serialize what
  the queryset can annotate.
- Return only the data the consumer needs.

### 4.4 Computed and dynamic fields

- Avoid unnecessary `SerializerMethodField`; prefer model fields / annotations.
- Never query from serializer methods; pass context explicitly via `serializer context`.
- Memoize repeated per-object computation on the serializer instance or in context.

### 4.5 Responsibility boundaries and reuse

- Serializers validate and shape — business logic lives in `services/`.
- Do not put external API calls or complex workflows in `create()`/`update()`.
- Reuse existing serializers before writing new ones. **Never create one unnecessarily.**

### 4.6 Consistency and compatibility

- Keep related response structures consistent; standard error envelope everywhere.
- Do not leak internal details. Preserve backward compatibility unless a change is
  explicitly required. Document non-obvious fields.

Before completing a serializer, verify: explicit fields, read-only protected data,
intentional nullability, correctly placed validation, consistent relationship shapes,
nested queries optimized, computed fields justified, contract preserved.

## 5. Architecture and code organization

### 5.1 Layers

| Layer | Responsibility |
|-------|----------------|
| Models | Database structure, relationships, constraints, closely related model behavior |
| Serializers | Input validation and API representation |
| Views / ViewSets | HTTP handling, orchestration, permissions, responses — thin |
| Services | Business workflows spanning models or systems |
| Selectors / Managers | Reusable, complex data retrieval |
| Tasks | Asynchronous and scheduled operations |
| Permissions | Reusable access-control rules |

Business logic belongs in `services/`, not views or serializers. Views parse, delegate,
return. Cross-app imports use the other app's public surface (models, serializers) —
never another app's `services/`.

### 5.2 Shared and reusable code (`common/`)

`common/` is the shared library for cross-cutting concerns; apps import from `common/`,
never the reverse, and never domain apps.

- **Reuse before reinventing.** Most needs already exist below.
- **Consolidate duplicates into `common/`.** When the same logic exists in app and
  `common/`, keep the better one, update callers, delete the duplicate.
- **`common/` is additive.** Unused helpers stay — it is a library; delete only what is
  demonstrably dead repo-wide.
- **Extend, don't fork.** Subclass or compose `common/` primitives instead of copying them.

| If you need… | Use… |
|---|---|
| A viewset | `BaseViewSet` from `common.views` |
| Model bases | `TimestampedModel`, `UUIDModel`, `SoftDeleteModel` from `common.models` (order matters: `TimestampedModel` first) |
| Error handling | `BaseViewSetMixin` from `common.mixins` (envelope, `SENSITIVE_LOG_KEYS` scrubbing, `perform_*` hooks) |
| Pagination | `StandardPagination` from `common.pagination` |
| Role permissions | `create_role_permission()` from `common.permissions` |
| File/image validation | helpers from `common.serializers` |
| ModelAdmin bases | `BaseAdmin` / `TranslationBaseAdmin` / `ReadOnlyAdmin` from `common.unfold_admin_bases` — **mandatory**, never raw `admin.ModelAdmin` |
| OTP throttling | `OTPThrottle`, `AccountLinkThrottle`, `AuthRateThrottle` from `common.throttles` |

### 5.3 Default app layout

```text
<app>/
├── models.py              # Models only (+ closely tied manager/queryset)
├── serializers.py         # Or serializers/ package when it grows
├── views.py               # Thin viewsets; services for logic
├── services/              # Business logic, one module per concern
├── urls.py
├── admin.py               # Inherit common admin bases
├── apps.py
├── translation.py         # If translatable fields exist
├── filters.py             # FilterSets — every query param belongs here
├── tasks.py               # Celery tasks (bind=True, retries)
└── tests/                 # pytest, one file per feature
```

Split into packages only for discoverability — a `serializers.py` and `views.py` stay
the default until they are genuinely unwieldy.

### 5.4 Code quality bar

- Readable in two minutes by a teammate new to the module.
- Meaningful names; predicates for booleans, plural collections.
- Guard clauses over nesting; ≤ 3 indentation levels; functions ≤ 40 lines (60 hard limit).
- Modules have one concern; ~300 lines is the split point.
- Type hints on every function, `X | None` over `Optional[X]`.
- No mutable default arguments; no wildcard imports; no `except Exception: pass`.
- Validate at system boundaries, raise typed exceptions, fail fast — don't swallow errors.
- Self-documenting code over implementation comments; section headers and public-API
  docstrings are fine.
- Remove dead code, unused imports, and commented-out blocks — leave none behind.

### 5.5 Signals and cross-app communication

Signals only for cross-app notifications (e.g. `post_save` → Celery task). Signals are
short and idempotent; no business logic in signals. Prefer direct calls over signals.

## 6. Database and performance

### 6.1 Query budgets — every read endpoint

- Bounded query count independent of row count. `select_related()` for FK/O2O,
  `prefetch_related()` for reverse/M2M.
- `Prefetch()` with a limited queryset when nested serializers need a subset; name every
  field the nested serializer reads.
- Never filter or re-order on a related manager after a Prefetch — bypasses the cache;
  use `.all()` (reuses the prefetched cache).
- No queries inside serializer methods or property accessors.
- `Count(..., filter=Q(...))`, `F()`, `Q()`, `.annotate()`, `.values()`/`.values_list()`,
  `.only()`/`.defer()` where justified — never list every column on a wide table for a
  narrow response.
- `.iterator()` for large scans (imports, audits). Eager for small bounded lists.
- Cap unbounded collections before serialization (recents ≤ 20, inbox ≤ 50, files per
  response bounded); every list endpoint paginates.
- Budget every read endpoint with `django_assert_max_num_queries` tests.

### 6.2 Indexes

Pattern-driven (see §3.6). `EXPLAIN ANALYZE` when executing is safe; add indexes for hot
predicates before shipping the search/filter endpoint. `pg_trgm` GIN for large-text
search in production.

### 6.3 Writes and transactions

- `transaction.atomic()` around multi-row writes; `select_for_update()` inside it for
  check-then-write; re-read at point of mutation. Keep transactions short.
- `bulk_create`/`bulk_update`/`QuerySet.update()` for batch writes; accept that
  signals and `save()` hooks do not fire — only use them when those are not needed.
- `F()` for atomic arithmetic — never read-modify-write.

### 6.4 Caching

Use Django's cache framework (Redis in production) and `cache.get_or_set`. Define TTL and
a write-side invalidation path; user-specific keys must include ownership; never cache
what cannot be reliably invalidated. Caching is not an excuse for bad queries.

### 6.5 Request-path discipline

- >100 ms of work (email, push, image processing, exports) runs in Celery — never blocks
  a request. No synchronous external HTTP in the request path; use Celery or an
  async client with a timeout.
- Reuse HTTP sessions; paginate everything; responses stay small (≤ 1 MB without
  justification). Profile before optimizing; verify behavior is preserved.

## 7. Testing standards

Mandatory and part of implementation — a feature isn't done because it returns 200.

### 7.1 Rules

- Every new app/feature ships meaningful tests; every bug fix ships a regression test.
- Tests isolated, deterministic, readable; reuse fixtures; never weaken/delete to pass.
- Do not mock the implementation when the test should verify its actual behavior.

### 7.2 What to cover

- **Models**: defaults, nullability, constraints, relations, status transitions.
- **Services**: success/side effects, invalid input, boundary conditions, exceptions,
  transactions, external-failure handling.
- **APIs**: auth, permissions, ownership and user isolation, read-only fields, status
  codes, response shape, filters/ordering/pagination, 4xx paths.
- **Security**: cross-user access attempts, read-only field injection, role gates.
- **Performance**: query budgets, N+1 regression, pagination behavior.

### 7.3 Execution

1. Focused run for the changed app (`python -m pytest tests/<file>.py -q`).
2. Full `python -m pytest -q` before finishing substantial work.
3. Investigate failures rather than assuming they are unrelated.
4. Report exactly what was run and what was skipped.

## 8. Consumer contract consistency

The API is consumed by web/mobile clients against a public contract. Before changing an
endpoint, read how the consumer calls it.

- **Match contract, not habit.** Field names, envelopes, status codes, error shapes and
  headers (`Accept-Language`, `X-Timezone`) are part of the contract.
- **No silent API changes.** A contract change ships with the client (web repository
  gets the matching change) or with a compatibility plan — not as a surprise.
- **Enforce on the backend.** Authentication, ownership and permissions live server-side;
  hidden/disabled UI is never a control.
- **Idempotency on state changes.** Duplicate submissions to state-changing actions are
  safe by design (natural-key upserts, unique constraints, idempotent tasks).
- **Guides stay accurate.** `guides/*.md` document each module; when your change alters
  documented behavior, update the guide in the same change (see §2).
- **Never document behavior the code does not support;** never invent requirements where
  none exist. Ask first.

## 9. Definition of Done

**Before implementation** — understand the current implementation; read the relevant
`guides/*.md`; check `common/` for reusable pieces; confirm no duplication.

**During implementation** — architecture and layer boundaries respected; contracts
preserved or explicitly versioned; validation, permissions and ownership handled; query
efficiency considered; expected errors and edge cases handled; `common/` reused.

**Testing** — meaningful tests added/updated; failure, authz and edge cases covered;
query budgets checked; `python -m pytest` green; `python manage.py check` clean.

**Final review** — complete diff reviewed; dead code gone; no unrelated files modified;
migrations checked where models changed; documentation matches implementation; existing
flows (accounts, notifications, compliance, admin) still work.

## 10. Completion report

Report concisely:

1. **Changes** — what was implemented or modified.
2. **Architecture and API** — important contract or layering decisions.
3. **Tests** — what was added/updated and its coverage.
4. **Checks executed** — actual commands and results, including failures.
5. **Remaining work** — limitations, skipped checks, follow-ups.

Never claim tests passed unless you ran them. Never claim a feature is fully verified
when important checks were skipped.

## 11. Quality gate and git workflow

- `make quality` = `check-format` (black, line-length 100) + `lint` (flake8
  `--extend-ignore=E203,W503`) + `type-check` (mypy) + `test` (pytest) + `check`
  (`manage.py check`). Run it before committing.
- Conventional commits, scoped (`accounts:`, `notifications:`, `docs:`, `chore:`), no
  force-pushes, review the diff for secrets before committing.
- `python manage.py check` is the baseline sanity gate; `pytest` is the behavior gate;
  both before push.

## Appendix: repository facts

Apps: `accounts` (multi-account auth: `Account`, `EmailOTP`, `SocialAccountLink` +
`AccountJWTAuthentication`, RLS context — JWT per Account), `common` (shared library),
`compliance` (FAQ + `PolicyDocument`/`PolicyAcceptance`), `contacts`,
`notifications` (`Device`, `Notification`, `CustomReminder`), `dashboard` (Live Logs SSE),
`guides/` (module documentation), `tests/` (pytest). Docker: PostgreSQL 17, Celery 5.4,
`python:3.13-slim` image (local venv may differ — trust the image Dockerfile). Auth is
mounted at `/api/v1/auth/`.
