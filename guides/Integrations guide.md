# Integrations Guide — Strengthen Your Django Rapido Project (Django Rapido V2.0)

> Django Rapido ships production-grade **API + Auth + Push + Admin + Docker**. This guide is the **next layer** — optional services you plug in when your product outgrows the template. Nothing here is pre-installed; each section tells you **what it does, when to add it, how to wire it into this template (`file:line`), and tradeoffs**.

## Table of Contents

1. [How to Decide](#how-to-decide)
2. [Observability — Prometheus, Grafana, Sentry, ELK](#observability)
3. [Realtime — WebSockets (Channels) vs SSE (already have Live Logs)](#realtime)
4. [API Styles — GraphQL (Strawberry/Graphene) vs REST (already have DRF)](#api-styles)
5. [Webhooks — Outbound + Inbound](#webhooks)
6. [Payments — Stripe, Paymob, PayPal, Fawry](#payments)
7. [Search — PostgreSQL vs Elasticsearch/Meilisearch/Typesense](#search)
8. [Object Storage & CDN — S3/MinIO/Cloudflare R2](#storage)
9. [Email & Transactional — SES/Mailgun/Postmark](#email)
10. [Feature Flags & Config — Unleash/Flagsmith/env](#feature-flags)
11. [Security Hardening — 2FA/WebAuthn, Rate-limit tiers, WAF](#security)
12. [Summaries — Priority Matrix + Wiring Map](#summaries)

---

## How to Decide

| Signal you need it | Add this first |
|---|---|
| `5XX` hidden until users report it | **Sentry** (5 min) → then **Prometheus+Grafana** |
| Need chat/live cursors/typing | **WebSockets (Channels)** — Live Logs SSE is one-way, not enough |
| Mobile asks `give me only `id,title.price`` or `N+1` screens | **GraphQL** |
| Partners say `notify me when order ships` | **Webhooks outbound** |
| Need to collect money | **Payments** |
| `GET /search?q=` is `icontains` and slow | **Search engine** |
| `media/` fills disk, images slow globally | **S3 + CDN** |
| `if user.is_staff:` everywhere | **Feature flags** |
| Logins abused, accounts shared | **2FA/WebAuthn + WAF** |

**Rule:** Don't add before you feel the pain. Each integration here is **one package + 5-15 lines** in this template — all wiring points are listed as `file:line`.

---

## Observability

### Prometheus + Grafana — Metrics

**What:** `django-prometheus` exposes `/metrics` (request latency, DB, cache hits, Celery queue depth). Prometheus scrapes it every `15s`; Grafana dashboards graph it.

**When:** After first prod deploy, before first incident. Basic `docker compose logs` + Live Logs `dashboard/live_logs.py:92` is for dev; metrics are for prod.

**How (Django Rapido wiring):**
```bash
pip install django-prometheus==2.3.1 prometheus-client
```
```python
# project/settings/base.py:60 INSTALLED_APPS
INSTALLED_APPS = ["django_prometheus", ...]  # must be first
# project/settings/base.py:108 MIDDLEWARE — add at top + bottom per docs
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware", # first
    ... "dashboard.live_logs.LiveLogsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware", # last
]
# project/urls.py:15
from django.urls import include
urlpatterns += [path("", include("django_prometheus.urls"))]  # /metrics
```
```yaml
# docker-compose.yml — add service (or docker-compose.prod.yml for prod-only)
prometheus:
  image: prom/prometheus
  volumes: ["./prometheus.yml:/etc/prometheus/prometheus.yml"]
  ports: ["9090:9090"]
grafana:
  image: grafana/grafana
  ports: ["3000:3000"]
  environment: [GF_SECURITY_ADMIN_PASSWORD=admin]
```
- Scrape `django:8000/metrics` + `postgres_exporter` + `redis_exporter` if needed.
- Alert on `histogram_quantile(0.95)` latency > `500ms`, `5XX rate > 1%`, `celery queue > 100`.

**Tradeoffs:** `+2` containers, `~100MB` RAM. `/metrics` is public by default → protect via `nginx.conf` `allow 10.0.0.0/8; deny all;` or add `IsAdminUser` wrapper.

### Sentry — Error Tracking

**What:** One line captures every `500` with traceback + user + release. Replaces `grep` on logs.

```bash
pip install sentry-sdk==2.19.0
# project/settings/base.py:486 LOGGING block — add
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),  # .env.example:116 already has placeholder
    traces_sample_rate=0.1,
    send_default_pii=False,
)
```
- Add `SENTRY_DSN=` to `.env.example:116` + `.env` (already present).
- Release: `release=os.getenv("GIT_COMMIT", "local")`.

**When:** Day 1 of prod. Faster ROI than Grafana.

### ELK / Loki — Log Aggregation

**What:** Ships `LOGGING` `base.py:486` JSON to Elasticsearch/Loki so you can `query 5XX last 7d by path`. Live Logs is ephemeral `300KB`; ELK is durable `90d`.

**How:** Keep `django` JSON formatter, add `python-json-logger==2.0.7` (already commented in `requirements.txt:141`), ship via `Filebeat` sidecar or `promtail` → Loki. No Django code change — just container + `LOG_LEVEL=WARNING` in prod.

---

## Realtime

### WebSockets (Django Channels) — When SSE Isn't Enough

**What you already have:** Live Logs SSE `dashboard/live_logs.py:417` is **server→client one-way**, perfect for admin observability. It is **not** for chat.

**When to add Channels:** Need **client↔server bidirectional** — chat, live orders, driver location, collaborative editing.

**How:**
```bash
pip install channels==4.1.0 daphne==4.1.2 channels-redis==4.2.0
```
```python
# project/settings/base.py:161 ROOT_URLCONF already, add ASGI
INSTALLED_APPS += ["channels"]
ASGI_APPLICATION = "project.asgi.application"  # already in base.py:521
CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer",
    "CONFIG": {"hosts": [os.getenv("REDIS_URL", "redis://:redis_password@redis:6379/0")]}}}

# project/asgi.py:12 — replace get_asgi_application() with ProtocolTypeRouter
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import myapp.routing
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(myapp.routing.websocket_urlpatterns)),
})
# myapp/routing.py — create
from django.urls import re_path
from .consumers import OrderConsumer
websocket_urlpatterns = [re_path(r"ws/orders/(?P<order_id>\w+)/$", OrderConsumer.as_asgi())]

# myapp/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
class OrderConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(f"order_{self.scope['url_route']['kwargs']['order_id']}", self.channel_name)
        await self.accept()
    async def order_update(self, event):
        await self.send_json(event["data"])
```
- **Docker:** Add `daphne` service or run `web` with `daphne -b 0.0.0.0 -p 8000 project.asgi:application` instead of `gunicorn`. Or keep `gunicorn` for HTTP + `daphne` for WS and route `location /ws/ → daphne` in `nginx.conf:60`.
- **Auth:** Reuse `JWTAuthentication` via query `?token=<access>` in `connect()` → `JWTAuthMiddleware` (custom).

**Tradeoffs:** `+1` process + Redis channel layer (already have Redis). Complexity: connection auth, reconnect, presence.

**Alternative — Stay on FCM/SSE:** If you only need `notify user after they leave` → keep `notifications/tasks.py:86` FCM; if `server→client while on page` → extend Live Logs SSE pattern `dashboard/live_logs.py:417` to a second stream `GET /api/v1/stream/orders/?last_id` — simpler than Channels.

---

## API Styles

### GraphQL (Strawberry preferred)

**What:** One endpoint `POST /graphql` where clients request `query { product(id){ name price } }`. Solves REST over-fetching.

**When:** Mobile with `5+` screens each needing different fields, or `N+1` REST calls to assemble a page. If your API is `10` endpoints and clients are happy → stay REST.

**How:**
```bash
pip install strawberry-graphql==0.245.0 strawberry-graphql-django==0.45.0
```
```python
# myapp/schema.py
import strawberry, strawberry_django
from .models import Product
@strawberry_django.type(Product)
class ProductType: id: strawberry.auto; name: strawberry.auto; price: strawberry.auto
@strawberry.type
class Query:
    @strawberry.field
    def products(self) -> list[ProductType]: return Product.objects.select_related("category").all()
schema = strawberry.Schema(query=Query)

# project/urls.py:29
from strawberry.django.views import GraphQLView
urlpatterns += [path("graphql/", GraphQLView.as_view(schema=schema))]
# Auth — reuse JWT: set request.user in context via JWTAuthentication
```
- Keep DRF `api/v1/` for existing clients; add GraphQL alongside — no rewrite.
- **N+1:** Use `strawberry_django` + `select_related/prefetch_related` same as `AGENTS.md §5`.

**Tradeoffs:** Caching harder (one URL), file uploads need `multipart`, learning curve. `django-filter` → `strawberry_django.filters`.

**Keep REST when:** You need `drf-spectacular` auto docs `project/urls.py:38` + `StandardPagination` + `FilterSet` discipline — REST is simpler for CRUD.

---

## Webhooks

### Outbound (you notify partners)

**What:** `POST https://partner.com/hook` JSON on `order.completed`. Partners retry on `5XX`.

**How:**
```python
# myapp/models.py — store subscriptions
class WebhookSubscription(TimestampedModel, UUIDModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    url = models.URLField()
    events = models.JSONField(default=list)  # ["order.completed"]
    secret = models.CharField(max_length=64, default=secrets.token_hex)  # HMAC
    is_active = models.BooleanField(default=True, db_index=True)

# myapp/tasks.py — dispatch (idempotent)
import hmac, hashlib, requests
from celery import shared_task
@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def dispatch_webhook(self, subscription_id: str, event: str, payload: dict):
    sub = WebhookSubscription.objects.get(id=subscription_id, is_active=True)
    body = json.dumps({"event": event, "data": payload}, sort_keys=True)
    sig = hmac.new(sub.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    try:
        r = requests.post(sub.url, data=body, headers={"X-Webhook-Signature": sig, "Content-Type": "application/json"}, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        raise self.retry(exc=exc)
# call from service: dispatch_webhook.delay(str(sub.id), "order.completed", {"order_id": str(order.id)})
```
- Add `project/urls.py` `POST /api/v1/webhooks/subscriptions/` CRUD via `BaseViewSet` `common/views.py:40`.
- Verify inbound: partner checks `X-Webhook-Signature == HMAC(secret, raw_body)`.

### Inbound (partners notify you)

```python
# myapp/views.py — allowlist IP + secret
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    sig = request.headers.get("Stripe-Signature", "")
    # stripe.Webhook.construct_event(request.body, sig, webhook_secret) — then handle event
```
- **Nginx:** `webhooks` need raw body — don't consume with `request.data` before `construct_event`.
- Store events idempotently by `event_id` unique constraint.

---

## Payments

### Stripe (global) / Paymob / Fawry (MENA)

**When:** Collecting money — choose one primary.

**How — Stripe example (others similar):**
```bash
pip install stripe==7.11.0 dj-stripe==2.9.1  # dj-stripe adds Webhook + models, optional
```
```python
# project/settings/base.py:225 BUSINESS_TIME_ZONE already — add
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")  # .env + .env.example
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# myapp/services/pricing.py — reuse docs/examples/pricing.md DELIVERY_FEE_TABLE, then charge
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
intent = stripe.PaymentIntent.create(amount=int(total*100), currency="usd",
    metadata={"order_id": str(order.id)}, automatic_payment_methods={"enabled": True})
# return client_secret to FE; FE confirms with Stripe.js

# myapp/views.py — webhook (see Webhooks inbound)
@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    event = stripe.Webhook.construct_event(request.body, request.headers["Stripe-Signature"], settings.STRIPE_WEBHOOK_SECRET)
    if event.type == "payment_intent.succeeded":
        Order.objects.filter(id=event.data.object.metadata.order_id).update(status="paid")
```

- **Paymob (Egypt):** `pip install requests` — `POST https://accept.paymob.com/api/auth/tokens → POST /api/ecommerce/orders → POST /api/acceptance/payment_keys → redirect user`. Webhook `POST /api/v1/webhooks/paymob/` validates `hmac`.
- **Fawry:** Similar `charge` → `fawry` ref → webhook.
- **Common:** Money `DecimalField 10,2` `AGENTS.md` never `Float`; `F()` atomic updates `docs/examples/pricing.md`; `select_for_update` inside `@transaction.atomic` for stock+payment race `project/settings/base.py` + `common/models.py`.

**Tradeoffs:** `+ PCI` scope (use hosted `PaymentIntent`/`Checkout` — never store card). Webhook idempotency required.

### Paymob quick wiring points

| Piece | Django Rapido `file:line` |
|---|---|
| Secret | `project/settings/base.py:225` `PAYMOB_API_KEY = os.getenv("PAYMOB_API_KEY")` |
| Service | `myapp/services/payments.py` — `create_paymob_intention(amount, order_id)` |
| View | `myapp/views.py` `@action pay` `BaseViewSet` |
| Webhook | `project/urls.py` `path("webhooks/paymob/", paymob_webhook)` + `AllowAny` |
| Model | `Order.status TextChoices paid` + `Payment.status` `common/constants.py` `PaymentStatus` |

---

## Search

### Stay PostgreSQL as long as you can

**What you have:** `django-filter` + `SearchableFilterSet` `common/filters.py:231` + `AGENTS.md §5` `SearchVector rank` `common/filters.py:269 AdvancedSearchFilter` `trigram` (`pg_trgm`).

```sql
-- Enable in migration
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
```
- Good for `10k-500k` rows, `name/icontains` + ordering `-created_at`.

### Upgrade when slow: Meilisearch / Typesense / Elasticsearch

| Engine | When | Django package | Note |
|---|---|---|---|
| **Meilisearch** | `500k-10M`, typo tolerance, instant | `meilisearch-python-sdk` | Easiest, `1` container, `<100ms` |
| **Typesense** | Similar, stricter | `typesense` | OSS, similar |
| **Elasticsearch** | `10M+`, analytics, aggregations | `django-elasticsearch-dsl==8.0` + `elasticsearch==8.13` | Heaviest |

**Meilisearch example:**
```bash
# docker-compose.yml — add
meilisearch:
  image: getmeili/meilisearch
  ports: ["7700:7700"]
  environment: [MEILI_MASTER_KEY=masterKey]
```
```python
# myapp/documents.py — index on save
import meilisearch
client = meilisearch.Client("http://meilisearch:7700", "masterKey")
client.index("products").add_documents([{"id": str(p.id), "name": p.name} for p in Product.objects.all()])
# search
results = client.index("products").search("iphon", {"limit": 20})  # typo tolerant
```
- Keep PG as source of truth, index via `post_save` signal (short, idempotent `AGENTS.md §3.3`) or Celery `index_product.delay`.

---

## Storage

### S3 / MinIO / Cloudflare R2

**What you have:** `MEDIA_URL /media/` via Nginx `nginx.conf:46` + `Whitenoise` `base.py:277` for `static/`. Works for dev, fills `media_volume` on prod.

**When to add S3:** `media/` > `10GB`, multi-region, or need signed URLs.

```bash
pip install django-storages==1.14.3 boto3==1.35.0
# project/settings/base.py:283
STORAGES = {
    "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {"bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
                    "region_name": os.getenv("AWS_S3_REGION_NAME", "eu-central-1")}},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
AWS_S3_CUSTOM_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN")  # or R2 domain
# .env.example — add AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_STORAGE_BUCKET_NAME
# docker-compose.yml — remove media_volume from web if using S3 entirely
```
- **MinIO** (self-host S3): add `minio` container + `mc` create bucket, same `boto3` config with `endpoint_url`.
- **CDN:** CloudFront / Cloudflare in front of `bucket`.

---

## Email

### Transactional (SES / Mailgun / Postmark)

**What you have:** SMTP `base.py:286` `EMAIL_HOST smtp.gmail.com` `.env.example:57` + `common/helpers.py:233 send_template_email`. Good for dev; SPF/DKIM fragile on prod.

**Upgrade:**
```python
# project/settings/base.py:286 — swap backend
EMAIL_BACKEND = "django_ses.SESBackend"  # pip install django-ses
AWS_SES_REGION_NAME = os.getenv("AWS_SES_REGION_NAME", "eu-west-1")
# or Mailgun
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.mailgun.org"
```
- Use `accounts/tasks.py:16 send_verification_email` already Celery `bind+retry` — no change, just env.

---

## Feature Flags

**When:** `if user.role == "seller":` spreads, you want kill-switch without deploy.

```bash
pip install django-flags==5.0.4  # or django-waffle==4.1.0 or unleash
# project/settings/base.py:60
INSTALLED_APPS += ["flags"]
FLAGS = {"NEW_CHECKOUT": [{"condition": "user", "value": "staff"}]}
# template: {% load feature_flags %}{% flag_enabled "NEW_CHECKOUT" as on %}{% if on %}...{% endif %}
# view: from flags.state import flag_enabled; if flag_enabled("NEW_CHECKOUT", request): ...
```
- **Unleash/Flagsmith:** Self-host `unleash` container, `unleash-client-python` in `requirements.txt`.

---

## Security

### 2FA / WebAuthn (passkeys)

**When:** Admin or finance actions — password alone insufficient.

```bash
pip install django-otp==1.5.6 django-two-factor-auth==1.16.0
# or WebAuthn
pip install webauthn==2.4.0
```
- Add `OTPRequiredMixin` to admin views; store `VerifiedDevice` per user. Wiring: `common/models.py CustomUser` add `totp_secret` + `is_2fa_enabled`.

### Rate tiers + WAF

**What you have:** `common/permissions.py:219 RateLimitPermission` `100/1000/10000`, `common/middleware.py:154 RateLimitMiddleware` + `throttles.py:16 AuthRateThrottle 30/m`, `SecurityHeadersMiddleware:129`.

**Add:** `django-axes==7.1.0` (lockout after `5` fails), Cloudflare WAF or Nginx `limit_req` + `fail2ban`.

---

## Summaries

### Priority Matrix (add in this order)

| Priority | Integration | Effort | Django Rapido wiring | Payoff |
|---|---|---|---|---|
| **P0 now if prod** | **Sentry** | `5 min` | `base.py:486 + .env SENTRY_DSN` | See every `500` |
| **P0 if prod** | **Prometheus+Grafana** | `30 min` | `django-prometheus + nginx /metrics allowlist` | Latency/5XX/queue graphs |
| **P1 when need chat** | **Channels WS** | `2h` | `asgi.py:12 + routing.py + consumers.py` | Bidirectional realtime |
| **P1 when need money** | **Payments** | `4h` | `base.py PAY_ env + services/payments.py + webhooks` | Revenue |
| **P1 when need search** | **pg_trgm → Meilisearch** | `1h → 4h` | `pg_trgm extension` → `meilisearch container` | Fast typo-tolerant search |
| **P1 when media grows** | **S3/MinIO + CDN** | `2h` | `STORAGES base.py:283 + AWS env` | No disk full, global CDN |
| **P2** | **GraphQL Strawberry** | `3h` | `schema.py + urls.py graphql/` | Flexible mobile |
| **P2** | **Webhooks outbound** | `3h` | `WebhookSubscription model + dispatch_webhook task` | Partner integrations |
| **P2** | **Email SES/Mailgun** | `15 min` | `base.py:286 EMAIL_BACKEND` | Deliverability |
| **P3** | **Feature flags** | `1h` | `flags + FLAGS base.py:60` | Kill-switch |
| **P3** | **2FA/WebAuthn** | `1d` | `django-otp + CustomUser totp_secret` | Account takeover defense |

### Wiring Map (where to touch)

| Integration | Files to edit `file:line` | DB/env |
|---|---|---|
| Prometheus | `base.py:60 INSTALLED_APPS, :108 MIDDLEWARE, project/urls.py:15, nginx.conf, docker-compose.yml` | none |
| Sentry | `base.py:486, .env.example:116` | `SENTRY_DSN` |
| Channels | `base.py:161+521 ASGI, project/asgi.py:12, myapp/routing.py, consumers.py, nginx.conf:60 ws/` | `REDIS_URL` reuse |
| GraphQL | `myapp/schema.py, project/urls.py:29` | none |
| Webhooks out | `myapp/models.py WebhookSubscription, tasks.py dispatch_webhook, views.py subscriptions, urls.py` | table `webhooks` |
| Webhooks in | `myapp/views.py stripe_webhook AllowAny, urls.py webhooks/` | `STRIPE_WEBHOOK_SECRET` |
| Payments | `base.py:225 STRIPE_SECRET_KEY, myapp/services/payments.py, views.py pay action, urls.py webhooks` | `Order.status` |
| Search | `common/filters.py:269, docker-compose.yml meilisearch` | `pg_trgm` or `meilisearch` |
| S3 | `base.py:283 STORAGES, .env AWS_*` | bucket |
| Email | `base.py:286 EMAIL_BACKEND` | provider keys |
| Flags | `base.py:60 FLAGS` | `flags` table or Unleash |
| 2FA | `common/models.py CustomUser + myapp/views 2fa` | `totp_secret` |

> Every integration above is **fully decoupled** — no other app imports it directly (see `AGENTS.md §3.1`). Add, keep, or delete via the `## Removal` pattern in each guide — no rewrites.

