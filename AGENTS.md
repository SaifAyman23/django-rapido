# AGENTS.md — Universal Django + DRF Reference

> **Purpose:** This file is the single source of truth for this codebase and a universal reference for anyone
> (AI or human) building Django REST Framework projects. All sections are framework-level best practices
> that apply to ANY Django/DRF project.
>
> **Mandatory:** Every contributor MUST read this file before writing any code. If a decision, convention,
> or pattern is missing, add it here — don't assume, guess, or invent ad-hoc solutions.

---

## 1. Project Identity

```
Name:        [Project Name]
Stack:       Django 5 + DRF, Celery + Redis, PostgreSQL 16, JWT Auth
Auth:        JWT (simplejwt), email+password
No WebSockets — all real-time updates via push notifications (if applicable)
```

---

## 2. Directory Layout

```
project/                     # Django project config (settings, urls, celery, wsgi)
  settings/
    base.py                  # Shared settings (DB, cache, celery, DRF, JWT)
    local.py                 # Dev overrides (DEBUG=True, eager celery)
    production.py            # Production overrides (HTTPS, strict CORS)
    unfold_config.py         # Admin theme (sidebar nav, colors, branding)
  urls.py                    # Root URL routing
  celery.py                  # Celery app instance

accounts/                    # Authentication only — login, register, logout, token refresh
  filters.py                #   FilterSets for query param filtering
  serializers.py             #   All serializers for this app
  views.py                  #   All viewsets for this app
  urls.py                   #   URL routing
  admin.py                  #   Django admin configuration
  helpers.py                #   Pure helper functions

common/                      # Reusable infrastructure (shared by ALL apps)
  models.py                 #   Base models (UUIDModel, TimestampedModel, SoftDeleteModel, AuditLog)
  mixins.py                 #   BaseViewSetMixin — central error handling, perform_* hooks
  views.py                  #   BaseViewSet, CurrentUserOwnerMixin, BulkOperationViewSet
  serializers.py            #   AuditableSerializer, file/image validation helpers
  pagination.py             #   StandardPagination, LargePagination, cursor pagination
  permissions.py            #   Permission classes (add your project-specific ones here)
  unfold_admin_bases.py     #   BaseAdmin, BaseUserAdmin, ReadOnlyAdmin, SoftDeleteAdmin

# Add your project-specific apps here, each following this structure:
# app/
#   __init__.py
#   models.py          # Data models
#   filters.py         # django-filter FilterSets
#   serializers.py     # DRF serializers
#   views.py           # DRF viewsets
#   urls.py            # URL routing via DefaultRouter
#   admin.py           # Django admin registration
#   services/          # Business logic (optional)
#   tasks.py           # Celery tasks (optional)
#   tests/
#     __init__.py
#     test_models.py
#     test_views.py
#     test_services.py
```

---

## 3. Architecture & Decoupling

### 3.1 App Boundaries
- **One responsibility per app.** If you can't describe an app's purpose in one sentence, it's too broad.
- Apps own their data. No app directly imports another app's models. Cross-app access goes through service functions or the importing app's public API (views, service layer).
- An app's `models.py` is its private schema — other apps should never import from it directly. If `ratings` needs to know about orders, it uses `order_id` (a UUID string), not the `Order` model.

### 3.2 Service Layer Pattern
- Put business logic in `app/services/`, never in views or serializers.
- Views call services. Services call models and other services.
- A service function receives primitive types (strings, ints, UUIDs) or model instances, never requests.
- Service functions are pure — they return results or raise exceptions, they don't return Responses.

### 3.3 Signal Rules
- Signals are for **cross-app notifications only** (e.g., `post_save` on Order → fire Celery task).
- Signals must be short and idempotent. Never put business logic in signals.
- If you can call a function directly instead of using a signal, do that instead.

### 3.4 Common App — Shared Infrastructure
Before writing ANYTHING, check `common/` — it exists precisely to eliminate duplication:

| If you need... | Use... |
|---|---|
| A viewset | `BaseViewSet` from `common.views` — never write `ModelViewSet` from scratch |
| A model base | `UUIDModel` + `TimestampedModel` from `common.models` |
| Error handling | `BaseViewSetMixin` from `common.mixins` — envelope: `{"error": {"code": "...", "message": "...", "details": ...}}` |
| Success response in custom action | `self.success_response(data, message)` from `BaseViewSetMixin` |
| Pagination | `StandardPagination` from `common.pagination` |
| Audit log creation | `AuditLog.objects.log_action(...)` from `common.models` |
| Role-based permissions | Permission classes from `common.permissions` |
| File/image validation | Helpers from `common.serializers` |
| Admin base classes | `BaseAdmin`, `BaseUserAdmin` from `common.unfold_admin_bases` |

If the tool you need doesn't exist in `common/`, **add it there first, then use it**. Never duplicate.

---

## 4. Models — Design & Conventions

### 4.1 Base Classes
Every model inherits from `UUIDModel` + `TimestampedModel` in this order (MRO matters):
```python
from common.models import UUIDModel, TimestampedModel

class MyModel(TimestampedModel, UUIDModel):  # TimestampedModel first = its fields survive MRO
```
This gives you: UUID PK, `created_at`, `updated_at`.

If you need soft-delete, add `SoftDeleteModel`:
```python
from common.models import UUIDModel, TimestampedModel, SoftDeleteModel

class MyModel(TimestampedModel, UUIDModel, SoftDeleteModel):
    ...
```

### 4.2 Field Rules
- **Money**: `DecimalField(max_digits=10, decimal_places=2)` — never `FloatField`.
- **Timestamps**: always `DateTimeField` (with `auto_now_add` / `auto_now`), never `DateField` or `TimeField` for audit timestamps.
- **Text choices**: use `models.TextChoices` (not Django 3.x integer choices) for type/status fields.
- **JSON**: use `JSONField` (native PostgreSQL JSONB) — never serialize JSON manually.
- **Nullable vs blank**: `null=True` for DB-level null, `blank=True` for form/DRF validation. `CharField`/`TextField` with `blank=True, default=""` is better than `null=True` for text.
- **ImageField/FileField**: always `null=True, blank=True` — files are optional.

### 4.3 Meta Options
```python
class Meta:
    verbose_name = _("My Model")
    verbose_name_plural = _("My Models")
    ordering = ["-created_at"]           # default unless domain requires otherwise
    constraints = [                      # DB-level constraints > Python validation
        models.UniqueConstraint(fields=["user", "product"], name="unique_user_product"),
    ]
    indexes = [
        models.Index(fields=["foreign_key"]),           # FK indexes (Django adds these automatically for FK fields, but explicit is clearer)
        models.Index(fields=["-created_at"]),           # common sort pattern
        models.Index(fields=["field_a", "field_b"]),   # composite index for filtered queries
    ]
```

### 4.4 Index Strategy
- Every FK gets an index (Django does this automatically, but verify).
- Every field used in `filter()`, `exclude()`, `order_by()`, or `distinct()` should be indexed or have a composite index.
- Composite indexes matter: if you filter by `(category, is_active)`, create one index, not two separate ones.
- Use `Index(condition=...)` for partial indexes on soft-delete or archived scopes.
- Avoid over-indexing — each index slows writes.

### 4.5 Enum / TextChoices Pattern
```python
from django.db import models
from django.utils.translation import gettext_lazy as _

class OrderStatus(models.TextChoices):
    SUBMITTED = "submitted", _("Submitted")
    PREPARED = "prepared", _("Prepared")
    COMPLETE = "complete", _("Complete")

class Order(TimestampedModel, UUIDModel):
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.SUBMITTED,
        db_index=True,
    )
```
Use `choices` everywhere — never store freeform strings for status/type fields.

### 4.6 `__str__` Always
```python
def __str__(self):
    return self.name  # or f"{self.user.email} - {self.product.name}"
```

### 4.7 Model Methods vs Properties
- `@property` for computed fields that are cheap (no DB query).
- Regular methods for anything that touches the DB or does work.
- Avoid putting query logic in model methods — that belongs in managers/querysets or service functions.

---

## 5. Queries — Optimization & Performance (Senior)

### 5.1 The N+1 Enemy
Every loop over a queryset that accesses a FK triggers a separate query unless you `select_related()` or `prefetch_related()`.

**select_related** (for FK and OneToOne — SQL JOIN):
```python
# BAD — N+1 queries:
for product in Product.objects.all():
    print(product.category.name)

# GOOD — 1 query with JOIN:
for product in Product.objects.select_related("category").all():
    print(product.category.name)

# CHAINED:
Product.objects.select_related("category__parent_category").all()
```

**prefetch_related** (for reverse FK and ManyToMany — separate query + merge in Python):
```python
# BAD:
for category in Category.objects.all():
    for product in category.products.all():  # 1 query per category
        ...

# GOOD — 2 queries total:
for category in Category.objects.prefetch_related("products").all():
    for product in category.products.all():
        ...
```

**Prefetch objects** for filtered/ordered prefetches:
```python
from django.db.models import Prefetch

Product.objects.prefetch_related(
    Prefetch(
        "favorited_by",
        queryset=ProductFavorite.objects.filter(user=request.user),
        to_attr="user_favorites",
    )
)
```

### 5.2 Column Selection — `.only()` and `.defer()`

Only fetch columns you actually need. This matters on models with many fields, large text/JSON fields, or high-traffic endpoints.

```python
# Fetch only specific columns:
Product.objects.only("id", "name", "price")

# Defer expensive/rarely-needed columns:
Product.objects.defer("description", "image")  # fetches everything except these

# Never do this on list endpoints:
Product.objects.all()  # when you only need name + price, use .only("name", "price")
```

**Senior rule**: Use `.only()` on list endpoints, `.defer()` on detail endpoints where you usually need most fields but want to skip heavy ones. Profile with `len(connection.queries)` and `django-debug-toolbar`.

### 5.3 Lightweight Queries — `.values()` and `.values_list()`

When you only need raw values (not model instances), use `values()`:
```python
# Returns dicts instead of model instances — 10x faster for large datasets:
Product.objects.filter(is_active=True).values("id", "name", "price")

# Returns flat tuples or single values:
Product.objects.filter(is_active=True).values_list("id", flat=True)

# Use with dict comprehension for fast lookups:
product_prices = {
    p["id"]: p["price"]
    for p in Product.objects.values("id", "price")
}
```

**When to use**: aggregations, reports, dropdown options, batch operations, any read-only data that doesn't need model methods.

### 5.4 F() Expressions — Atomic Field Updates

Never do read-modify-write in concurrent scenarios:
```python
# RACE CONDITION — two requests can read the same value:
product = Product.objects.get(id=1)
product.times_ordered += 1
product.save()

# ATOMIC — DB handles the increment:
from django.db.models import F
Product.objects.filter(id=1).update(times_ordered=F("times_ordered") + 1)
```

`F()` expressions work on all field types and can be combined:
```python
# Multiple fields:
Order.objects.filter(id=order.id).update(
    products_total=F("products_total") + adjustment,
    updated_at=timezone.now(),
)
```

### 5.5 Subqueries and Exists

For filtering based on related model conditions without triggering N+1:
```python
from django.db.models import Exists, OuterRef, Subquery

# Find categories that have at least one active product:
categories = Category.objects.filter(
    Exists(Product.objects.filter(category=OuterRef("pk"), is_active=True))
)

# Annotate with related data:
latest_order_per_user = Order.objects.filter(
    user=OuterRef("pk")
).order_by("-created_at").values("id")[:1]

User.objects.annotate(
    last_order_id=Subquery(latest_order_per_user)
)
```

### 5.6 Annotate and Aggregate

Use annotations to compute derived fields in the DB:
```python
from django.db.models import Count, Sum, Avg, Q, Case, When, IntegerField, Value

# Count related objects:
Category.objects.annotate(product_count=Count("products"))

# Conditional counts:
Category.objects.annotate(
    active_products=Count("products", filter=Q(products__is_active=True))
)

# Computed boolean field:
User.objects.annotate(
    has_active_orders=Exists(
        Order.objects.filter(user=OuterRef("pk"), status="submitted")
    )
)
```

### 5.7 Batch Operations

```python
# BAD — N queries for N objects:
for product in products:
    product.is_active = False
    product.save()

# GOOD — 1 query:
Product.objects.filter(id__in=[p.id for p in products]).update(is_active=False)

# Bulk create (no signals, no auto_now):
Product.objects.bulk_create([
    Product(name="A", price=10, category_id=cat_id),
    Product(name="B", price=20, category_id=cat_id),
])

# Bulk update:
Product.objects.bulk_update(products, ["price", "is_active"])
```

### 5.8 Query Checklist (Before Committing)
- [ ] `select_related()` applied for every FK accessed in the response?
- [ ] `prefetch_related()` applied for every reverse relation or M2M?
- [ ] `.only()` or `.defer()` used to avoid fetching unnecessary columns?
- [ ] No queries inside loops?
- [ ] `F()` expressions used for atomic increments instead of read-modify-write?
- [ ] FilterSet handles all query params (no inline `get_queryset` conditions)?
- [ ] Considered whether `.values()` is sufficient instead of full model instances?

---

## 6. Database Transactions & Locking (Senior)

### 6.1 Transaction Boundaries

Use `@transaction.atomic` on viewset actions, not on model methods:
```python
from django.db import transaction

class OrderViewSet(BaseViewSet):
    @action(detail=True, methods=["post"])
    @transaction.atomic  # <--- here
    def confirm(self, request, pk=None):
        order = self.get_object()
        order.status = "complete"
        order.save()
        Product.objects.filter(order=order).update(
            times_ordered=F("times_ordered") + 1
        )
```

**Rules:**
- Put `@transaction.atomic` at the **viewset action level**, not in service functions.
- Service functions are called inside the transaction — they raise exceptions, the view catches and rolls back.
- Keep transactions short. Long transactions hold DB connections and block concurrent access.
- Read-only operations do NOT need transactions.

### 6.2 `select_for_update()` — Row-Level Locking

Use when you need to read a value, compute something, and write it back — without races:
```python
@transaction.atomic
def allocate_inventory(order_id: str, product_id: str, quantity: int):
    order = Order.objects.select_for_update().get(id=order_id)
    product = Product.objects.select_for_update().get(id=product_id)

    # Both rows are locked — no other request can read them until this transaction commits:
    if product.stock < quantity:
        raise ValueError("Insufficient stock")

    product.stock = F("stock") - quantity
    product.save()
    update_order_total.delay(order_id)
```

**When to use:**
- Payment processing (check balance → debit → confirm)
- Inventory/stock management
- Resource allocation (inventory, seat booking)
- Coupon/code consumption (check available → use → decrement)

**When NOT to use:**
- You can use `F()` expressions instead (they're atomic without locking)
- Pure reads
- High-throughput endpoints where occasional races are acceptable (like like/favorite toggles)

**Always use `select_for_update()` inside `@transaction.atomic`** — it has no effect outside a transaction.

### 6.3 Deadlock Prevention

Order your locks consistently to prevent deadlocks:
```python
# BAD — two code paths locking in different orders:
# Path A: lock Order, lock Product
# Path B: lock Product, lock Order

# GOOD — always lock in the same order (e.g., alphabetically by model name):
def transfer():
    # Always lock Order before Product (O before P)
    order = Order.objects.select_for_update().get(id=order_id)
    product = Product.objects.select_for_update().get(id=product_id)
```

### 6.4 Nested Transactions (Savepoints)
```python
@transaction.atomic  # outer
def process_order(order_id):
    order = Order.objects.get(id=order_id)
    with transaction.atomic():  # savepoint — can rollback this inner block
        try:
            charge_payment(order)
        except PaymentError:
            # Rollback only the payment, not the entire order:
            # (the savepoint undoes charge_payment)
            order.status = "payment_failed"
            order.save()
```

---

## 7. Serializers — Patterns & Performance (Senior)

### 7.1 Action-Specific Serializers

Never use one serializer for all actions — list, detail, create, and update often need different fields:
```python
class ProductViewSet(BaseViewSet):
    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer  # includes store, full description
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer  # write-only fields, validation
        return ProductListSerializer  # lightweight, no heavy relations
```

### 7.2 Nested Serializer Performance

Nested serializers with `source="..."` annotations add DB work. Pre-annotate or use `SerializerMethodField` with cached queries:
```python
# BAD — triggers a query per object in the loop:
class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name")

# GOOD — same, but ensure the viewset has select_related("category"):
# (the serializer itself is fine, just make sure the viewset optimizes the query)

# For computed fields, annotate in the viewset:
class ProductViewSet(BaseViewSet):
    def get_queryset(self):
        return Product.objects.annotate(
            is_favorited=Exists(
                ProductFavorite.objects.filter(
                    user=self.request.user,
                    product=OuterRef("pk"),
                )
            )
        )

class ProductListSerializer(serializers.ModelSerializer):
    is_favorited = serializers.BooleanField(read_only=True)  # comes from annotation, no extra query
```

### 7.3 Validation Patterns

```python
class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["name", "price", "category", "image"]

    # Field-level validation:
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be positive")
        return value

    # Object-level validation (multiple fields):
    def validate(self, attrs):
        category = attrs.get("category")
        if category and not category.is_active:
            raise serializers.ValidationError(
                {"category": "Category is not active"}
            )
        return attrs
```

### 7.4 Context Passing
```python
# View passes context:
serializer = self.get_serializer(data=request.data)
# or explicitly:
serializer = ProductSerializer(data=request.data, context={"request": request})

# Serializer reads context:
class ProductSerializer(serializers.ModelSerializer):
    def get_user(self):
        return self.context["request"].user
```

### 7.5 Dynamic Fields (Hide from certain users)
```python
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context["request"].user
        if not user.is_authenticated or not user.is_staff:
            data.pop("internal_notes", None)
        return data
```

**Senior rule**: Use `to_representation` sparingly — it runs on every serialization. Prefer separate serializer classes first.

### 7.6 Serializer Checklist
- [ ] Different serializers for list, detail, create, update?
- [ ] `read_only_fields` set for all server-set fields (id, created_at, timestamps)?
- [ ] `write_only_fields` for password, tokens?
- [ ] No N+1 from nested serializers (check with `django-debug-toolbar`)?
- [ ] File validation (size, type) on ImageField/FileField inputs?
- [ ] Validation logic in serializer, not in view?

---

## 8. Views & ViewSets

### 8.1 Standard Viewset Structure
```python
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from common.views import BaseViewSet
from .filters import MyModelFilter
from .serializers import (
    MyModelListSerializer,
    MyModelDetailSerializer,
    MyModelWriteSerializer,
)

class MyModelViewSet(BaseViewSet):
    queryset = MyModel.objects.select_related("relation").all()
    serializer_class = MyModelListSerializer  # default
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_class = MyModelFilter
    search_fields = ["name", "email"]
    ordering_fields = ["created_at", "name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MyModelDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return MyModelWriteSerializer
        return self.serializer_class
```

### 8.2 Pagination Rules
- Pagination is configured globally in settings (DEFAULT_PAGINATION_CLASS). Every list endpoint is paginated by default.
- Never set `pagination_class = None` unless the endpoint returns a fixed small set (like dashboard stats).
- Never redeclare pagination per-viewset — it's global. Only override if you need different behavior.
- Custom pagination class? Extend `StandardPagination` from `common.pagination`.

### 8.3 Permission Rules
- Read endpoints (GET): `IsAuthenticatedOrReadOnly` (public can read, must be auth to mutate)
- Write endpoints (POST/PATCH/DELETE): `IsAuthenticated` minimum
- Admin-only actions: `IsAdminUser` or custom role class
- Custom actions (like `/enable/`, `/cancel/`): explicit `permission_classes` on the action

```python
@action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
def enable(self, request, pk=None):
    ...

@action(detail=True, methods=["post"])
@transaction.atomic
def cancel(self, request, pk=None):
    # Uses viewset's default permissions
    ...
```

### 8.4 FilterSet — Every Query Param Belongs Here
```python
# filters.py — never scatter filter logic in get_queryset:
import django_filters

class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    include_inactive = django_filters.BooleanFilter(method="filter_include_inactive")

    class Meta:
        model = Product
        fields = ["category", "is_active"]

    def filter_include_inactive(self, queryset, name, value):
        if value and self.request.user.is_staff:
            return queryset  # bypass active filter for staff
        return queryset.filter(is_active=True, category__is_active=True)
```

Filters have access to `self.request` — use it for user-aware filtering.

### 8.5 Custom Action Pattern
```python
@action(detail=True, methods=["post"], url_path="favorite", url_name="favorite")
@transaction.atomic
def favorite(self, request, pk=None):
    product = self.get_object()
    if request.method == "DELETE":
        deleted, _ = ProductFavorite.objects.filter(
            user=request.user, product=product,
        ).delete()
        if not deleted:
            return Response({"error": "Not found"}, status=404)
        return Response(status=204)

    fav, created = ProductFavorite.objects.get_or_create(
        user=request.user, product=product,
    )
    if not created:
        fav.delete()
        return self.success_response({"favorited": False}, "Removed from favorites")
    return self.success_response({"favorited": True}, "Added to favorites", status=201)
```

### 8.6 ViewSet Checklist
- [ ] `select_related` / `prefetch_related` on the base queryset?
- [ ] `filterset_class` defined in `app/filters.py` (not `filterset_fields`)?
- [ ] `search_fields` and `ordering_fields` set?
- [ ] Action-specific serializers used?
- [ ] Permissions correct per action?
- [ ] Mutating actions wrapped in `@transaction.atomic`?

---

## 9. Security (Universal)

### 9.1 Mass Assignment Protection
- Never pass user input directly to `serializer.save()` without validation.
- Use `read_only_fields` for server-controlled fields (id, timestamps, computed fields).
- Use `write_only_fields` for sensitive inputs (passwords, tokens).
- Never expose `is_staff`, `is_superuser`, or role-based fields to client write access.

### 9.2 SQL Injection
- Django's ORM + parameterized queries prevent SQL injection by default.
- Never use `raw()` or `extra()` with string interpolation.
- If you must write raw SQL, always use `cursor.execute(sql, params)` with params as a list/tuple.

### 9.3 Authentication & Authorization
- Every endpoint has explicit permission classes — no endpoint is accidentally public.
- Role checks happen at the viewset level, not scattered in `get_queryset`.
- `get_queryset` can filter by user, but never grant access to other users' data.

### 9.4 Environment & Secrets
- No secrets in code. All secrets in environment variables (or `.env` for local).
- Never log secrets, tokens, passwords, or personal data.
- No API keys, DB passwords, or secret keys in git history.

### 9.5 Settings Safety
```python
# production.py — enforce HTTPS:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

### 9.6 CORS
```python
# Be specific, never use ['*'] in production:
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
```

---

## 10. Performance (Universal)

### 10.1 Caching Strategy
- **Low-traffic, user-specific data** (cart, favorites): no cache (DB is fast enough).
- **Medium-traffic, shared data** (product catalog, categories): cache for 5-15 minutes.
- **High-traffic, rarely-changing data** (static content, config): cache indefinitely with invalidation on write.
- **Never cache user-specific data in a shared key** — use per-user keys.

```python
from django.core.cache import cache

def get_active_categories():
    cache_key = "catalog:active_categories"
    data = cache.get(cache_key)
    if data is not None:
        return data
    data = list(Category.objects.filter(is_active=True))
    cache.set(cache_key, data, 300)  # 5 minutes
    return data
```

### 10.2 Database Connection Pooling
- PostgreSQL has a limited number of connections (`max_connections`).
- Every Celery worker process holds one connection. Too many workers = connection starvation.
- Set `CONN_MAX_AGE` to a reasonable value (like 300 seconds) in settings for persistent connections.

### 10.3 Migration Performance
- Large tables: use `--name` with `--no-header` and batch operations.
- Avoid `RunPython` on millions of rows — use batch updates with `pagination`.
- Add indexes concurrently in production (PostgreSQL: `CREATE INDEX CONCURRENTLY`).

### 10.4 Static & Media Files
- Use WhiteNoise for static files (already configured).
- Media files (uploaded images) served via the production web server (Nginx/Caddy), not Django.
- CDN for production media delivery.

### 10.5 Connection Count Monitoring
- Database connections per process: Django sync worker = 1, Celery worker = 1.
- `max_connections` must be > (number of Django processes + number of Celery workers).
- Set a reasonable `CONN_MAX_AGE` to reuse connections.

---

## 11. Celery & Async Tasks

### 11.1 Task Structure
```python
from celery import shared_task
from django.db import transaction

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_order_status(self, user_id: str, order_id: str, status: str):
    """Send push notification when order status changes."""
    from notifications.services import should_notify
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.get(id=user_id)

    if not should_notify(user):
        return {"status": "skipped", "reason": "notifications_disabled"}

    try:
        send_fcm_notification(user, f"Order {status}", order_id)
    except Exception as exc:
        raise self.retry(exc=exc)

    return {"status": "sent"}
```

### 11.2 Task Rules
- Tasks are **idempotent** — running them twice produces the same result.
- Tasks are **small** — if a task does more than one thing, split it.
- Tasks import models directly (they run in the Django context), no need for service functions to stay decoupled.
- Every `notify_*` task calls `should_notify()` before sending.
- Use `bind=True` to access `self.retry()` for error recovery.

### 11.3 Avoiding Duplicate Tasks
```python
# Check before enqueuing:
if not should_notify(user):
    return

# Or use a dedup key:
from django_celery_beat.models import PeriodicTask

# For periodic tasks, use Django Celery Beat's one-off=True
```

---

## 12. Testing
