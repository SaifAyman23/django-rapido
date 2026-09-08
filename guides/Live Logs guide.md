# Live Logs Guide — SSE In-Memory Admin Terminal (Django Rapido V2.0)

> In-memory SSE admin terminal — `dashboard/live_logs.py` (Redis list + fallback deque). No DB, no files, no WebSockets. Staff-only, zero-refresh.

## Table of Contents

1. [Goal](#goal)
2. [What It Offers / When to Skip](#what-it-offers--when-to-skip)
3. [File Map (code locations)](#file-map-code-locations)
4. [Architecture & How It Works](#architecture--how-it-works)
5. [Setup From Scratch (step-by-step)](#setup-from-scratch-step-by-step)
6. [How to Adjust / Enhance](#how-to-adjust--enhance)
7. [Logic — Buffer & Middleware Deep Dive](#logic--dashboardlive_logspy)
8. [Pages — Templates (Tailwind, component-based)](#pages--templates-tailwind-component-based)
9. [Styling](#styling)
10. [SSE Implementation](#sse-implementation)
11. [Nginx & Docker — Production Wiring](#nginx--docker--production-wiring)
12. [Changelog — Latest Updates Since Initial Replica](#changelog--latest-updates-since-initial-replica-exact-changes--why)
13. [Tradeoffs](#tradeoffs)
14. [How to Use (already wired)](#how-to-use-already-wired)
15. [Verification](#verification)
16. [REUSE Notes](#reuse-notes)
17. [Removal — How to Remove This Feature](#removal--how-to-remove-this-feature)

---

## Goal

Live, zero-refresh request stream inside Django admin. Watch every `2XX/3XX/4XX/5XX` with cause diagnostics for JWT/OAuth, without disk or DB load.

```
Request → LiveLogsMiddleware → deque(maxlen=1000) / Redis list ──→ SSE (StreamingHttpResponse) ──→ EventSource → terminal + stats + insights
                      1000 lines ~300KB              text/event-stream  retry:3000  heartbeat :\n\n every 0.5s
```

Stack: Django 5.2 + DRF 3.16 + Gunicorn + Redis 7 + `gevent` + Nginx — all realtime via FCM push for business logic, SSE for observability. No WebSockets, no `channels`.

---

## What It Offers / When to Skip

### What It Offers

| Capability | Detail |
|---|---|
| **Live request stream** | Every HTTP request logged with `ts, method, path, status, level, user, role, duration_ms, msg, cause` |
| **Status-family tabs** | `All / 2XX / 3XX / 4XX / 5XX` with live counts (`data-count`) |
| **KPI stats** | 5 cards: `TOTAL / 2XX / 3XX / 4XX / 5XX` with percentages (`data-stat-*`) |
| **Insights** | 4 cards: `ERROR RATE (4XX+5XX/Total) / TOP ERROR PATH / BUSIEST METHOD + avg+p95 / SUCCESS RATE (2XX/Total)` + burst detection (`BURST N/min` if ≥5 errors in 60s) |
| **Role filter** | `All Roles / Customer / Deliveryman / Ops / Guest` — generic `user.role` lowercased, fallback `guest` |
| **Cause diagnostics (≥400)** | Full JWT/OAuth forensics without token leakage — scheme, base64, `eyJ` prefix, `alg`, payload metadata, `detail/code/messages`, `token_not_valid`, `expired`, `Origin`/`XHR` hints, exception traceback tail, body snippet |
| **Search + highlight** | Live filter on `method/path/cause/msg/status/role` with `<mark>` highlight + debounce 150ms |
| **Controls** | `Pause/Resume`, `Clear`, `Download` (visible lines → `live-logs-YYYY-MM-DDTHH:MM:SS.txt`), `Auto-scroll` checkbox |
| **Terminal** | `JetBrains Mono` monospace, `oklch 9.5%` dark terminal, 560px, role-colored left border, cause amber line, separator |
| **Zero I/O** | Redis `LPUSH+LTRIM` shared across all containers; fallback `deque(maxlen=1000)` for tests/local without Redis; `~300KB` max |
| **Auto-reconnect** | `retry: 3000` + `EventSource` + gap-fill via `?last_id` / `Last-Event-ID` |
| **Staff-only** | `@staff_member_required` on both page and stream — Django session auth, not JWT |

### When to Skip (Is My Need Already Covered?)

| Your need | Skip live logs — use this instead |
|---|---|
| **Persistent audit trail** | Use `common.models.AuditLog` + `AuditLog.objects.log_action()` — survives restart, queryable, indexed. Live logs is ephemeral (~300KB ring). |
| **Structured JSON logging / ELK** | Use `project/settings/base.py:485-510` `LOGGING` (console verbose) → ship to Loki/ELK/Datadog. Live logs is for *human eyeballs* in admin, not for alerting. |
| **Celery task observability** | Use Flower (`:5555` in dev, internal in prod) + `django_celery_results`. Live logs only sees HTTP. |
| **Django debug toolbar queries** | Use `django-debug-toolbar` (`/__debug__/` when `DEBUG=True`) — live logs shows HTTP meta, not SQL. |
| **Security / IP rate-limit forensics** | Use `common.middleware.RateLimitMiddleware` + Nginx access log. Live logs shows cause but not IP throttling. |
| **Multi-process log aggregation** | If you already ship to Sentry/Papertrail, live logs is redundant — but keep it for instant local feedback without leaving admin. |
| **You have no Redis** | Works with `deque` fallback, but you lose cross-worker sharing (`web` vs `web-sse`). Either add Redis or accept single-worker visibility. |

**Rule of thumb:** Need live `4XX/5XX` diagnosis while developing/testing OAuth/JWT? Use live logs. Need durable history, alerting, or post-mortem? Use DB/file logger.

---

## File Map (code locations)

> Exact replica — every file with line count and anchor.

```
dashboard/live_logs.py                           # 444 lines — buffer + middleware + 2 views
  :21  MAX_LINES = 1000          # REUSE: easy global to tune
  :22  REDIS_KEY = "live_logs:buffer"
  :23  REDIS_SEQ = "live_logs:seq"
  :26  _buffer: deque(maxlen=MAX_LINES)  # fallback
  :27  _lock = Lock()
  :28  _seq = 0
  :31  def _next_id() -> int            # Redis INCR else Lock+_seq
  :45  def _redis_available() -> bool   # ping probe
  :56  def append_log(entry: dict)      # lpush+ltrim else deque.append
  :71  def get_snapshot(last_id=0)      # lrange+reverse else deque
  :92  class LiveLogsMiddleware         # __call__ logs every request
  :408 def live_logs_page               # @staff_member_required → admin/live_logs.html
  :417 def live_logs_stream             # @staff_member_required → SSE StreamingHttpResponse

project/settings/base.py
  :108-127  MIDDLEWARE list
  :121  "dashboard.live_logs.LiveLogsMiddleware"  # must be AFTER AccountMiddleware
  :239  TEMPLATES DIRS includes BASE_DIR / "dashboard/templates"

project/urls.py
  :15  from dashboard.live_logs import live_logs_page, live_logs_stream
  :53-58  i18n_patterns: admin/live-logs/ + stream/ + admin/
  :66-69  fallback nolang: admin/live-logs/ + stream/ (outside i18n)

project/settings/unfold_config.py
  :61-127  COLORS oklch palette (base/primary/blue/red/amber/green/purple/sky/indigo/lime)
  :256-275  SIDEBAR navigation — "Navigation" group: Dashboard + Live Logs (icon terminal → reverse_lazy("admin-live-logs"))
  :270-272  Live Logs item: title _("Live Logs"), icon "terminal", link reverse_lazy("admin-live-logs")

dashboard/templates/admin/live_logs.html         # 73 lines — shell: header + tabs + roles + stats + insights + controls + terminal
  :14  <link live_logs.css>
  :31  {% include "_tabs.html" %}
  :36-41  role filters (REUSE: Replace customer/deliveryman/ops with your Role)
  :46  {% include "_stats.html" %}
  :51  {% include "_insights.html" %}
  :56  {% include "_controls.html" %}
  :65  {% include "_terminal.html" %}
  :70  window.__LIVE_LOGS_STREAM_URL__ = "{% url 'admin-live-logs-stream' %}"
  :72  <script live_logs.js>

dashboard/templates/admin/live_logs/_tabs.html   # 7 lines — pills All/2XX/3XX/4XX/5XX data-count
dashboard/templates/admin/live_logs/_stats.html  # 27 lines — grid 5 cards TOTAL/2XX/3XX/4XX/5XX data-stat-*
dashboard/templates/admin/live_logs/_insights.html # 22 lines — grid 4 cards Error Rate/Top Path/Busiest Method/Success Rate
dashboard/templates/admin/live_logs/_controls.html # 9 lines — Pause/Clear/Download + search + status
dashboard/templates/admin/live_logs/_terminal.html # 3 lines — #live-logs-terminal oklch 9.5% 560px scroll
dashboard/templates/admin/live_logs/_line.html   # 10 lines — reference partial (JS renders lines at runtime)

static/dashboard/live_logs.js                    # 241 lines — EventSource + tab/role/search/filter + stats + render
  :2-31   els map (tabs, stat Els, insight Els, term, pauseBtn, clearBtn, downloadBtn, search, auto, status)
  :33-38  state: activeTab='all', activeRole='all', paused, lastId, buffer, searchQuery
  :40-46  family(status) → 5xx/4xx/3xx/2xx
  :48-96  renderStats() → counts, pct, paths, methods, durSum, p95, burstCount, topPath/method, err/success rate
  :98-104 highlight(text, query) → <mark>
  :106-114 visible(e) → tabOk && roleOk && searchQuery haystack
  :115-122 roleColor(role) → border-blue-500 / purple / lime / white
  :124-129 color(status) → red-400/amber-300/blue-400/green-400
  :131-174 render() → DocumentFragment, flex gap-3 + cause amber + separator, empty state, auto-scroll
  :176-180 scheduleRender() → debounce 150ms
  :182-193 tab + role click handlers
  :194-200 search input debounce 150ms
  :201-211 downloadBtn → Blob visible lines
  :212-216 pause/clear
  :218-241 connect() → EventSource baseUrl?last_id, onopen/onmessage/onerror reconnect 3s

static/dashboard/live_logs.css                   # 109 lines — @font-face JetBrains Mono + terminal + oklch utilities
  :1-8   @font-face JetBrains Mono woff2 + #live-logs-terminal font-family
  :9-10  .live-tab.active + .live-line.cause-open
  :12-73 explicit oklch utilities (bg-* / border-* / text-*) so purge never strips them
  :75-109 .dark variants (.dark .dark\:bg-*)

static/fonts/JetBrainsMono-Regular.woff2         # 92380 bytes self-hosted (no CDN)

nginx.conf                                        # 116 lines — dev
  :60-80  location ~ ^/(en|ar)?/?admin/live-logs/stream/ → proxy_pass http://django (proxy_buffering off, proxy_read_timeout 3600s, …)

nginx.prod.conf                                   # 200 lines — prod
  :28-30  upstream django_sse { server web-sse:8001 }
  :147-169 location ~ ^/(en|ar)?/?admin/live-logs/stream/ → proxy_pass http://django_sse (proxy_buffering off, proxy_cache off, 3600s, gzip off, keep-alive)

docker-compose.prod.yml
  :57-98  web-sse service — gunicorn gevent :8001 workers 2 worker-connections 1000 timeout 0 keep-alive 75 expose 8001 depends_on db/redis
  :183-185 nginx depends_on web + web-sse

docker-compose.yml
  :196-209  nginx dev (port 80, mounts nginx.conf)

requirements.txt:9  gevent==24.11.1  # only consumer is web-sse
```

---

## Architecture & How It Works

### End-to-End Flow

```
Browser /api/v1/users/me/  (Authorization: Bearer eyJ…)
  │
  ▼
Nginx ( :80 dev / :443 prod ) ── /static,/media bypass ──► Django
  │
  ▼  (project/settings/base.py:121  LiveLogsMiddleware wraps every request)
LiveLogsMiddleware.__call__  (dashboard/live_logs.py:96)
  │  start = monotonic()
  │  response = get_response(request)   # or exc_info on exception
  │  finally:
  │    duration_ms, status, level (INFO<400 WARN<500 ERROR)
  │    cause = "" ; if status>=400 → build diagnostics
  │    user = request.user.id/email[:24] if authenticated else ""
  │    role = request.user.role.lower() or "guest"
  │    append_log({ts, method, path, status, level, user, role, duration, msg, cause})
  │
  ▼
append_log  (dashboard/live_logs.py:56)
  │  entry["id"] = _next_id()  # Redis INCR live_logs:seq else Lock _seq
  │  try: Redis LPUSH live_logs:buffer + LTRIM 0:999
  │  except: fallback deque.append (O(1), maxlen=1000)
  │
  ▼
Buffer  (dashboard/live_logs.py:21-27)
  Redis list (shared)  OR  deque (per-process fallback)
  ~300 bytes/entry * 1000 ≈ 300KB max

Admin opens /admin/live-logs/  (project/urls.py:55  i18n /en/admin/live-logs/)
  │  live_logs_page (dashboard/live_logs.py:408)  @staff_member_required
  │  admin.site.each_context(request) + render admin/live_logs.html
  │  html injects window.__LIVE_LOGS_STREAM_URL__ (dashboard/templates/admin/live_logs.html:70)
  │
  ▼
Browser JS  (static/dashboard/live_logs.js:218  connect())
  │  baseUrl = window.__LIVE_LOGS_STREAM_URL__ || '/admin/live-logs/stream/'
  │  EventSource(`${baseUrl}?last_id=${lastId}`)
  │
  ▼
live_logs_stream  (dashboard/live_logs.py:417)  @staff_member_required
  │  last_id = int(GET last_id or 0)
  │  event_stream() generator:
  │    yield "retry: 3000\n\n"
  │    snapshot = get_snapshot(last_id) → gap-fill
  │    for entry in snapshot: yield "id: {id}\ndata: {json}\n\n"
  │    while True:
  │      sleep(0.5)
  │      new = get_snapshot(last_id)
  │      if new: yield each as id+data
  │      else:   yield ":\n\n"   # heartbeat comment — keeps proxy/Nginx from killing idle
  │  StreamingHttpResponse(event_stream(), content_type="text/event-stream")
  │  headers: Cache-Control no-cache, X-Accel-Buffering no, Content-Encoding identity
  │
  ▼  (nginx.conf:60 / nginx.prod.conf:147  hardened SSE location)
Nginx  proxy_buffering off, proxy_cache off, proxy_http_version 1.1, Connection "", gzip off,
       proxy_read_timeout 3600s, send_timeout 3600s, chunked_transfer_encoding on
  │
  ▼
Browser EventSource  (static/dashboard/live_logs.js:224)
  onopen → status "live"
  onmessage → JSON.parse, lastId = ev.lastEventId||data.id, buffer.push, shift>1000, scheduleRender 150ms
  onerror → status "reconnecting…", close, setTimeout(connect, 3000)

Frontend render  (static/dashboard/live_logs.js:131-174)
  renderStats() → counts, pct, paths/methods freq, durSum, p95, burst, errRate/successRate
  visible(e) → family==activeTab && role==activeRole && search haystack includes query
  DocumentFragment batch → flex row + cause amber + separator → single append (1 reflow for 1000 lines)
  auto-scroll if checkbox checked (requestAnimationFrame)
```

### Middleware Flow — Step by Step (`dashboard/live_logs.py:92-405`)

1. **Instrument** — `__call__` records `time.monotonic()` before `get_response`; captures both `response` and `exc_info` (unhandled exception) so nothing escapes (code at `dashboard/live_logs.py:96-105`).
2. **Derive status/level** — `status = response.status_code if response else 500`; overridden to `500` if `exc_info`; `level` = `INFO` (<400) / `WARN` (<500) / `ERROR` (≥500) (`dashboard/live_logs.py:108-112`).
3. **Build `cause` only if `status >=400`** (`dashboard/live_logs.py:114-373`):
   - If `exc_info`: `traceback.format_exception(...)[-5:]` → `"{ExcType}: {msg} | {tail}"` capped later.
   - Else `response.reason_phrase`.
   - Then JWT/OAuth enrichment (see next section) — appended as `" | ".join(details)` to `cause`.
4. **User + role** — `request.user.id or email` truncated `[:24]`; `role = str(getattr(user,"role","")).lower()` else `"guest"` — used for left-border color + role filter (`dashboard/live_logs.py:375-389`).
5. **Append** — `append_log({ts: isoformat, method, path: get_full_path(), status, level, user, role, duration, msg: "METHOD path", cause[:1000 implicit via json]})` (`dashboard/live_logs.py:390-403`). Whole block wrapped in `try: ... except: pass` so logging never breaks the request.

### Cause Diagnostics — JWT/OAuth Forensics (`dashboard/live_logs.py:126-373`)

Triggered when `is_jwt_path or is_oauth_path or status in (401,403)`:

- **Path detection** — `path_lc = request.get_full_path().lower()`; `is_jwt_path` if `/users/,/token,/jwt,/auth/social,/accounts/` ; `is_oauth_path` if `/social/,/oauth,/google,/facebook,/firebase` (`dashboard/live_logs.py:127-141`).
- **Header diagnostics (no token leakage)** (`dashboard/live_logs.py:144-226`):
  - `Missing Authorization header (expected 'Bearer <access>')` if empty
  - `leading/trailing whitespace`, `Multiple values (comma)`, `Wrong scheme 'X' (must be 'Bearer')`, `Bearer with no token`, `Double-space after Bearer`, `Empty token`, `Malformed JWT: N parts`, per-part empty / `^[A-Za-z0-9_-]+={0,2}$`, `not startswith eyJ`, header `base64.urlsafe_b64decode` → `alg HS256/RS256` or `header not decodable`
- **CORS/XHR** (`dashboard/live_logs.py:227-250`): `Missing Origin on OAuth POST`, `XHR without Authorization — ensure Flutter/Dio attaches Bearer`
- **Received JWT metadata for `/users/me`** (`dashboard/live_logs.py:251-325`): decodes payload without verify, compares `AccessToken(token)` validation, logs `recv JWT validated OK/FAILED type= user_id= alg= hash= err=` + `recv payload type= iss= aud= exp= iat=` + `quotes`, `Multiple Bearer` warnings. Safe — truncated ids, `hash=sha256(SIGNING_KEY)[:8]` not key.
- **DRF payload** (`dashboard/live_logs.py:327-362`): `detail/code/messages/error.message/error.details`, `token_not_valid → check ACCESS_TOKEN_LIFETIME/SECRET_KEY`, `expired → refresh via /users/token/refresh/`, `OAuth path failed`
- **Fallback** (`dashboard/live_logs.py:363-370`): `body=response.content[:2000]` if no details extracted; final `cause = " | ".join(details)` truncated to display.

### Buffer — Redis-Shared with Deque Fallback (`dashboard/live_logs.py:21-89`)

| Function | Redis path | Fallback | Lines |
|---|---|---|---|
| `_next_id()` | `get_redis_connection("default").incr(REDIS_SEQ)` atomic | `Lock + _seq +=1` | `dashboard/live_logs.py:31-42` |
| `append_log(entry)` | `lpush REDIS_KEY json.dumps(entry) + ltrim 0:MAX_LINES-1` | `_buffer.append(entry)` | `dashboard/live_logs.py:56-68` |
| `get_snapshot(last_id)` | `lrange 0:MAX_LINES-1 → json.loads → reverse → filter id>last_id` | `list(_buffer) filter id>last_id` | `dashboard/live_logs.py:71-89` |
| `_redis_available()` | `ping()` probe | `False` | `dashboard/live_logs.py:45-53` |

Memory: `MAX_LINES=1000` * `~300 bytes` (JSON with cause) ≈ `300KB` (`dashboard/live_logs.py:21` comment). `O(1)` append, auto-evicts oldest via `LTRIM`/`maxlen`. Ephemeral — cleared on Redis flush / deploy. Single-process fallback means `TESTING` (SQLite, no Redis) still works.

### SSE — Backend (`dashboard/live_logs.py:417-444`)

```python
# dashboard/live_logs.py:417
@staff_member_required
def live_logs_stream(request):
    last_id = int(request.GET.get("last_id", "0") or 0)
    def event_stream():
        nonlocal last_id
        yield "retry: 3000\n\n"                          # EventSource auto-reconnect 3s
        for entry in get_snapshot(last_id):               # gap-fill snapshot
            last_id = entry["id"]
            yield f"id: {entry['id']}\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"
        while True:
            time.sleep(0.5)
            new_entries = get_snapshot(last_id)
            if new_entries:
                for entry in new_entries:
                    last_id = entry["id"]
                    yield f"id: {entry['id']}\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"
            else:
                yield ":\n\n"                             # heartbeat comment

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"                # dashboard/live_logs.py:441
    response["X-Accel-Buffering"] = "no"                  # dashboard/live_logs.py:442
    response["Content-Encoding"] = "identity"             # dashboard/live_logs.py:443
    return response
```

- Respects `Last-Event-ID` via `?last_id` query (client sends `lastId` on reconnect).
- `StreamingHttpResponse` — Django streams generator without buffering full response.
- Headers prevent Nginx/proxy buffering (`X-Accel-Buffering no`, `Cache-Control no-cache`, `Content-Encoding identity`).
- Heartbeat `:\n\n` every `0.5s` keeps `proxy_read_timeout 3600s` satisfied through proxies that kill idle.

### Frontend — JS (`static/dashboard/live_logs.js:1-241`)

| Block | What | Lines |
|---|---|---|
| `els` map | `querySelectorAll('[data-stat-*]','[data-count]','[data-insight-*]')` + terminal/controls | `static/dashboard/live_logs.js:2-31` |
| State | `activeTab, activeRole, paused, lastId, buffer, searchQuery` | `static/dashboard/live_logs.js:33-38` |
| `family()` | `>=500 5xx / >=400 4xx / >=300 3xx / else 2xx` | `static/dashboard/live_logs.js:40-46` |
| `renderStats()` | Counts, `pct`, `paths` freq for top error path, `methods` freq, `durSum/p95`, `burstCount` (errors in last 60s), `errRate/successRate`, `BURST` badge on `els.status` if ≥5 | `static/dashboard/live_logs.js:48-96` |
| `highlight()` | Escape regex, wrap matches in `<mark class="bg-yellow-300">` | `static/dashboard/live_logs.js:98-104` |
| `visible()` | `family==activeTab && role==activeRole && haystack.includes(searchQuery)` | `static/dashboard/live_logs.js:106-114` |
| `roleColor()` / `color()` | Left-border per role; status text per family | `static/dashboard/live_logs.js:115-129` |
| `render()` | `DocumentFragment` batch, `flex gap-3 px-2 py-0.5 rounded border-l-2 {roleColor}`, `cause` amber line, `---` separator, empty state `No results for "q"`, single `els.lines.appendChild(frag)`, `requestAnimationFrame` auto-scroll | `static/dashboard/live_logs.js:131-174` |
| `scheduleRender()` | Debounce `150ms` | `static/dashboard/live_logs.js:176-180` |
| Handlers | Tabs `.live-tab`, roles `.live-role`, search `input` 150ms, download `Blob`, pause/clear | `static/dashboard/live_logs.js:182-216` |
| `connect()` | `baseUrl = window.__LIVE_LOGS_STREAM_URL__ || '/admin/live-logs/stream/'` (fix `4aab2ae`), `EventSource(?last_id)`, `onopen live`, `onmessage JSON.parse, lastId=ev.lastEventId||data.id, buffer push shift>1000, scheduleRender`, `onerror reconnecting… close setTimeout 3000` | `static/dashboard/live_logs.js:218-241` |

---

## Setup From Scratch (step-by-step)

> As if not implemented. Copy-paste each block. All paths are relative to repo root.

### Step 0 — Prerequisites

```bash
# Redis is required for shared buffer (already required for Celery)
# Verify CACHE_URL / CELERY_BROKER_URL point to redis:6379
python -m pip install gevent==24.11.1  # requirements.txt:9 — web-sse worker
```

### Step 1 — Create `dashboard/live_logs.py` (444 lines)

```python
# dashboard/live_logs.py — paste verbatim (REUSE header)
"""
REUSE: Generic live logs — Redis-shared (fallback deque), SSE, JWT diagnostics.

- MAX_LINES 1000 easy global to tune, ~300KB RAM, no env needed
- Roles: generic — reads user.role lowercased, fallback "guest" (change role filters in templates to match your Role)
- JWT diagnostics: generic, no token leakage, safe metadata only
- Django Rapido — decoupled, reusable live logs.
"""

import json
import time
import traceback
from collections import deque
from threading import Lock

from django.contrib.admin.views.decorators import staff_member_required
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.utils import timezone

MAX_LINES = 1000  # REUSE: easy global to tune, ~300KB RAM max for 1000 lines
REDIS_KEY = "live_logs:buffer"
REDIS_SEQ = "live_logs:seq"

_buffer: deque = deque(maxlen=MAX_LINES)
_lock = Lock()
_seq = 0

def _next_id() -> int:
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        return int(conn.incr(REDIS_SEQ))
    except Exception:
        global _seq
        with _lock:
            _seq += 1
            return _seq

def _redis_available() -> bool:
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        conn.ping()
        return True
    except Exception:
        return False

def append_log(entry: dict) -> None:
    entry = {**entry, "id": _next_id()}
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        conn.lpush(REDIS_KEY, json.dumps(entry, ensure_ascii=False))
        conn.ltrim(REDIS_KEY, 0, MAX_LINES - 1)
        return
    except Exception:
        pass
    with _lock:
        _buffer.append(entry)

def get_snapshot(last_id: int = 0) -> list[dict]:
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        raw = conn.lrange(REDIS_KEY, 0, MAX_LINES - 1)
        if raw:
            entries = [json.loads(x) for x in raw]
            entries.reverse()
            if last_id == 0:
                return entries
            return [e for e in entries if e["id"] > last_id]
    except Exception:
        pass
    with _lock:
        if last_id == 0:
            return list(_buffer)
        return [e for e in _buffer if e["id"] > last_id]

class LiveLogsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        start = time.monotonic()
        response = None
        exc_info = None
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            exc_info = exc
            raise
        finally:
            try:
                duration_ms = int((time.monotonic() - start) * 1000)
                status = response.status_code if response is not None else 500
                if exc_info is not None:
                    status = 500
                level = "INFO" if status < 400 else "WARN" if status < 500 else "ERROR"
                cause = ""
                if status >= 400:
                    # ... paste full cause block from dashboard/live_logs.py:114-373 ...
                    pass
                user_id = ""
                user_role = ""
                try:
                    if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
                        user_id = str(getattr(request.user, "id", "") or getattr(request.user, "email", ""))
                        user_role = str(getattr(request.user, "role", "")).lower()
                except Exception:
                    pass
                if not user_role:
                    user_role = "guest"
                append_log({
                    "ts": timezone.now().isoformat(),
                    "method": request.method,
                    "path": request.get_full_path(),
                    "status": status,
                    "level": level,
                    "user": user_id[:24],
                    "role": user_role,
                    "duration": duration_ms,
                    "msg": f"{request.method} {request.get_full_path()}",
                    "cause": cause,
                })
            except Exception:
                pass

@staff_member_required
def live_logs_page(request):
    from django.contrib import admin
    context = admin.site.each_context(request)
    context.update({"title": "Live Logs"})
    return render(request, "admin/live_logs.html", context)

@staff_member_required
def live_logs_stream(request):
    last_id = int(request.GET.get("last_id", "0") or 0)
    def event_stream():
        nonlocal last_id
        yield "retry: 3000\n\n"
        snapshot = get_snapshot(last_id)
        for entry in snapshot:
            last_id = entry["id"]
            yield f"id: {entry['id']}\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"
        while True:
            time.sleep(0.5)
            new_entries = get_snapshot(last_id)
            if new_entries:
                for entry in new_entries:
                    last_id = entry["id"]
                    yield f"id: {entry['id']}\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"
            else:
                yield ":\n\n"
    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Content-Encoding"] = "identity"
    return response
```

> Full `cause` block is long — copy `dashboard/live_logs.py:114-373` verbatim including `traceback`, JWT header checks, `Origin/X-Requested-With`, `AccessToken` validation, DRF `detail/code/messages` extraction.

### Step 2 — Wire middleware (`project/settings/base.py:121`)

```python
# project/settings/base.py — add AFTER allauth middleware, BEFORE common.middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # Live logs — in-memory SSE ring buffer (dashboard/live_logs.py:92)
    "dashboard.live_logs.LiveLogsMiddleware",
    "common.middleware.RequestLoggingMiddleware",
    "common.middleware.PerformanceMonitoringMiddleware",
    "common.middleware.SecurityHeadersMiddleware",
    "common.middleware.RequestEnhancementMiddleware",
]
```

Ensure `TEMPLATES[0]["DIRS"]` includes `BASE_DIR / "dashboard/templates"` (`project/settings/base.py:239`).

### Step 3 — Wire URLs (`project/urls.py:15,55-69`)

```python
# project/urls.py
from dashboard.live_logs import live_logs_page, live_logs_stream  # :15

# Inside i18n_patterns (page lives at /en/admin/live-logs/):
# project/urls.py:55-56
urlpatterns = [...] + i18n_patterns(
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/live-logs/", live_logs_page, name="admin-live-logs"),
    path("admin/live-logs/stream/", live_logs_stream, name="admin-live-logs-stream"),
    path("admin/", admin.site.urls),
)

# Fallback non-i18n so EventSource works without /en/ prefix (fix 4aab2ae):
# project/urls.py:66-69
urlpatterns += [
    path("admin/live-logs/", live_logs_page, name="admin-live-logs-nolang"),
    path("admin/live-logs/stream/", live_logs_stream, name="admin-live-logs-stream-nolang"),
]
```

### Step 4 — Admin sidebar (`project/settings/unfold_config.py:270-272`)

```python
# project/settings/unfold_config.py — inside UNFOLD["SIDEBAR"]["navigation"][0]["items"]
{
    "title": _("Live Logs"),
    "icon": "terminal",  # Material Symbols
    "link": reverse_lazy("admin-live-logs"),
},
```

Uses `reverse_lazy` so URL resolves after `project/urls.py` loads. Palette at `project/settings/unfold_config.py:61-255` already defines oklch — no change needed.

### Step 5 — Templates (6 files)

Create `dashboard/templates/admin/live_logs.html` (`73` lines) — `extends admin/base.html`, includes `_tabs`, role filters, `_stats`, `_insights`, `_controls`, `_terminal`, plus `window.__LIVE_LOGS_STREAM_URL__` bridge:

```html
{% extends 'admin/base.html' %}{% load i18n static %}
{% block extrahead %}{{ block.super }}<link rel="stylesheet" href="{% static 'dashboard/live_logs.css' %}">{% endblock %}
{% block content %}
  {% include "admin/live_logs/_tabs.html" %}
  <div id="live-logs-role-filters"> ... buttons data-role="all/customer/deliveryman/ops/guest" ... </div>
  {% include "admin/live_logs/_stats.html" %}
  {% include "admin/live_logs/_insights.html" %}
  {% include "admin/live_logs/_controls.html" %}
  {% include "admin/live_logs/_terminal.html" %}
  <script>window.__LIVE_LOGS_STREAM_URL__ = "{% url 'admin-live-logs-stream' %}";</script>
  <script src="{% static 'dashboard/live_logs.js' %}"></script>
{% endblock %}
```

Then add 5 partials verbatim:

- `dashboard/templates/admin/live_logs/_tabs.html:1-7` — 5 pills with `data-tab` + `data-count`
- `dashboard/templates/admin/live_logs/_stats.html:1-27` — grid 5 cards with `data-stat-*`
- `dashboard/templates/admin/live_logs/_insights.html:1-22` — grid 4 cards with `data-insight-*`
- `dashboard/templates/admin/live_logs/_controls.html:1-9` — Pause/Clear/Download + `#live-logs-search` + `#live-logs-status`
- `dashboard/templates/admin/live_logs/_terminal.html:1-3` — `#live-logs-terminal` 560px oklch 9.5%
- `dashboard/templates/admin/live_logs/_line.html:1-10` — reference only (JS renders)

### Step 6 — Static assets

```bash
# static/dashboard/live_logs.css  (109 lines) — @font-face + oklch utilities
# static/dashboard/live_logs.js   (241 lines) — ES module IIFE, see static/dashboard/live_logs.js:1-241
# static/fonts/JetBrainsMono-Regular.woff2 (92KB) — self-hosted

# Verify collectstatic picks them up:
python manage.py collectstatic --noinput
```

CSS must include explicit `.bg-*/.border-*/.text-*` + `.dark .dark\:*` utilities (`static/dashboard/live_logs.css:12-109`) so Tailwind purge never strips live-logs colors.

### Step 7 — Nginx — dev (`nginx.conf:60-80`)

```nginx
# nginx.conf — BEFORE the generic location /
location ~ ^/(en|ar)?/?admin/live-logs/stream/ {
    proxy_pass http://django;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    proxy_connect_timeout 10s;
    send_timeout 3600s;
    chunked_transfer_encoding on;
    gzip off;
    add_header Cache-Control "no-cache";
    add_header X-Accel-Buffering "no";
    add_header Connection "keep-alive";
}
```

Must appear **before** `location /` — regex locations are evaluated in order.

### Step 8 — Production — isolated SSE (`docker-compose.prod.yml:57-98` + `nginx.prod.conf:28-169`)

```yaml
# docker-compose.prod.yml — web-sse service
web-sse:
  build: { context: ., dockerfile: Dockerfile }
  container_name: project_web_sse
  restart: unless-stopped
  environment: [CONTAINER_ROLE=web, DJANGO_ENVIRONMENT=production, TESTING=False]
  env_file: [.env]
  command: >
    gunicorn project.wsgi:application
    --bind 0.0.0.0:8001
    --workers 2
    --worker-class gevent
    --worker-connections 1000
    --max-requests 1000
    --max-requests-jitter 100
    --timeout 0
    --graceful-timeout 0
    --keep-alive 75
    --worker-tmp-dir /dev/shm
  volumes: [static_volume:/app/staticfiles, media_volume:/app/media]
  expose: ["8001"]
  depends_on: { db: {condition: service_healthy}, redis: {condition: service_healthy} }
  networks: [project_network]
```

```nginx
# nginx.prod.conf — upstream + SSE location (same domain, no cert change)
upstream django_sse { server web-sse:8001; }  # :28-30
# inside server api.example.com:443
location ~ ^/(en|ar)?/?admin/live-logs/stream/ {
    proxy_pass http://django_sse;  # :149 — isolated gevent
    # ... same 13 directives as dev (proxy_http_version 1.1 … gzip off)
}
```

Add `web-sse` to nginx `depends_on` (`docker-compose.prod.yml:184-185`).

### Step 9 — Gevent dependency (`requirements.txt:9`)

```
gevent==24.11.1  # [NEEDED] Async worker for SSE web-sse (live logs)
```

Install: `pip install -r requirements.txt` then `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.

### Step 10 — Verify

```bash
python manage.py check
python manage.py collectstatic --noinput
curl -i http://localhost:8000/health/           # 200 healthy
curl -i http://localhost:8000/api/v1/users/me/  # 401 → see cause Missing Authorization
# Open http://localhost:8000/en/admin/live-logs/ as is_staff → lines appear live
docker compose config > /dev/null
docker compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null
```

---

## How to Adjust / Enhance

### Tune buffer size — `MAX_LINES` (`dashboard/live_logs.py:21`)

```python
MAX_LINES = 2000  # was 1000 — ~600KB RAM, more history, slower render
# Also update JS cap: static/dashboard/live_logs.js:230
if (buffer.length > 2000) buffer.shift();  # keep in sync
```

- `500 → ~150KB` (fast, low DOM); `1000 → ~300KB` (current); `2000 → ~600KB` (heavy but searchable history). No env needed — single top-level constant with `# REUSE: easy global to tune`.
- Both Redis `LTRIM 0:MAX_LINES-1` and JS `buffer.shift()` must match — mismatch causes snapshot vs display drift.

### Change colors — terminal / tabs / stat cards

| What | File | How |
|---|---|---|
| Terminal bg/text | `dashboard/templates/admin/live_logs/_terminal.html:1` | `style="background: var(--color-base-950); color: var(--color-base-100)"` → your oklch |
| Status text | `static/dashboard/live_logs.js:124-129` `color()` | `text-red-400/amber-300/blue-400/green-400` → swap Tailwind classes |
| Tab pills | `dashboard/templates/admin/live_logs/_tabs.html:2-6` | `bg-green-500/10 border-green-300` etc — swap per family |
| Stat card bg | `dashboard/templates/admin/live_logs/_stats.html:2-26` | `bg-green-500/10 text-green-700` — same pattern |
| Explicit utilities | `static/dashboard/live_logs.css:12-109` | Add your color there so purge keeps it: `.bg-lime-500\/10 { background: oklch(.../0.1) }` |

Sidebar icon: `project/settings/unfold_config.py:271` `icon: "terminal"` → any Material Symbol (`"bug_report"`, `"terminal"`, `"analytics"`).

### Add fields to log entries

In `dashboard/live_logs.py:390-403` `append_log` payload, add:

```python
append_log({
    "ts": timezone.now().isoformat(),
    "method": request.method,
    "path": request.get_full_path(),
    "status": status,
    "level": level,
    "user": user_id[:24],
    "role": user_role,
    "duration": duration_ms,
    "ip": request.META.get("REMOTE_ADDR", ""),   # NEW
    "ua": request.headers.get("User-Agent","")[:80],  # NEW — truncate
    "msg": f"{request.method} {request.get_full_path()}",
    "cause": cause,
})
```

Then render in `static/dashboard/live_logs.js:145` row template:

```js
row.innerHTML = `<span>${new Date(e.ts).toLocaleTimeString()}</span>
  <span>${highlight(e.method,q)}</span>
  <span>${highlight(e.path,q)}</span>
  <span class="${color(e.status)}">${e.status}</span>
  <span>${e.duration}ms</span>
  <span class="text-gray-400">${highlight(e.ip,q)}</span>  <!-- NEW -->
  <span>${highlight(e.msg,q)}</span>`;
```

And include in `visible()` haystack (`static/dashboard/live_logs.js:112`) + stats if needed.

### Filter by user / role / path

- **Per-user filter** — already has `e.user` and `e.role`. Add controls like roles: duplicate `dashboard/templates/admin/live_logs.html:35-41` buttons with `data-role="myemail"` or add a `<select>` populated from `buffer` unique users (JS: `[...new Set(buffer.map(e=>e.user))]`). Filter already in `visible()` (`static/dashboard/live_logs.js:106`).
- **Path filter** — search box already covers it (`static/dashboard/live_logs.js:194-199` + `visible()` haystack). For dedicated path pills, add buttons `data-path="/api/v1/users/"` and extend `visible()` with `if (activePath!=='all' && !e.path.includes(activePath)) return false`.
- **Exclude health/static** — in middleware early-return before `append_log`:

  ```python
  # dashboard/live_logs.py:390 — before append_log
  if request.path.startswith(("/health/","/static/","/media/","/__debug__/")):
      pass  # don't log
  else:
      append_log(...)
  ```

### Persist to DB (durable history)

Live logs is intentionally ephemeral. For persistence, **don't replace it** — tee to DB:

```python
# dashboard/live_logs.py:56 — inside append_log, after Redis lpush
from common.models import AuditLog  # existing model
try:
    AuditLog.objects.log_action(user=None, action="request_log", resource_type="http", details=entry)
except Exception:
    pass
```

Or create a dedicated model (`dashboard/models.py`):

```python
from common.models import TimestampedModel, UUIDModel
class RequestLog(TimestampedModel, UUIDModel):
    ts = models.DateTimeField()
    method = models.CharField(max_length=10)
    path = models.TextField()
    status = models.IntegerField(db_index=True)
    cause = models.TextField(blank=True)
    class Meta: ordering = ["-created_at"]; indexes = [models.Index(fields=["-created_at"])]
```

- Add `post_delete` cleanup via Celery beat (retain 7 days).
- Frontend can then add a tab `History` fetching `GET /api/v1/logs/?status=401` via DRF viewset — keep SSE for live, REST for archive.

### Other enhancements

| Enhancement | How |
|---|---|
| **Sampling / rate-limit** | Wrap `append_log` with `if random.random() < 0.1:` or check `request.path` allowlist before building `cause` (expensive). |
| **Expose via DRF** | Add `GET /api/v1/live-logs/?last_id=0` view returning `get_snapshot()` JSON — reuse `BaseViewSet` + `IsAdminUser` permission. |
| **WebSocket variant** | Replace `live_logs_stream` with `channels` `AsyncWebsocketConsumer` — but loses `gevent` simplicity; prefer SSE unless you need bidirectional. |
| **Multiple buffers** | Separate `REDIS_KEY = f"live_logs:{tenant}"` for multi-tenant isolation. |
| **Alert on burst** | In `append_log`, if `status>=500` count in last 60s ≥10 via `get_snapshot`, enqueue Celery `notify_ops.delay()` with `should_notify` guard. |

---

## Logic — `dashboard/live_logs.py`

Detailed above in Architecture. Key anchors: `dashboard/live_logs.py:21` MAX_LINES, `:31` _next_id, `:56` append_log, `:71` get_snapshot, `:92` LiveLogsMiddleware, `:408` live_logs_page, `:417` live_logs_stream. See source for full cause builder (`dashboard/live_logs.py:126-373`).

---

## Pages — Templates (Tailwind, component-based)

### `live_logs.html` (`dashboard/templates/admin/live_logs.html:1-73`)
`extends admin/base.html` → `branding` unfold helper → `extrahead live_logs.css` → header `Live Logs` → includes `tabs → role filters → stats → insights → controls → terminal` (`bg-white dark:bg-base-900 rounded-xl shadow-sm border`) → `script window.__LIVE_LOGS_STREAM_URL__` + `live_logs.js`.

### `_tabs.html` (`dashboard/templates/admin/live_logs/_tabs.html:1-7`)
`data-tab="all/2xx/3xx/4xx/5xx"` pills `rounded-full font-mono font-bold` `All active bg-primary-500` + `data-count="all/2xx..."` live counts.

### `_stats.html` (`dashboard/templates/admin/live_logs/_stats.html:1-27`)
`grid 5` cards: `TOTAL neutral (100%)`, `2XX green`, `3XX blue`, `4XX amber`, `5XX red` — `data-stat-total/2xx/3xx/4xx/5xx + data-stat-*-p` + `data-count`, clickable → tab (via JS handler).

### `_insights.html` (`dashboard/templates/admin/live_logs/_insights.html:1-22`)
`grid 4` cards: `ERROR RATE 4XX+5XX/Total`, `TOP ERROR PATH most frequent 4XX/5XX path`, `BUSIEST METHOD + avg ms • p95 • BURST`, `SUCCESS RATE 2XX/Total`.

### `_controls.html` (`dashboard/templates/admin/live_logs/_controls.html:1-9`)
`Pause/Resume + Clear + Download` `rounded-xl bg-white dark:bg-base-900 border` + `#live-logs-search` + `status live/connecting…/reconnecting…/BURST` `font-mono`.

### `_terminal.html` (`dashboard/templates/admin/live_logs/_terminal.html:1-3`)
`#live-logs-terminal font-mono text-xs rounded-xl shadow-sm p-4 overflow-auto` `background var(--color-base-950, oklch 9.5%) color var(--color-base-100) max-height 560px` → `#live-logs-lines space-y-1` (only scrollable area).

### `_line.html` (`dashboard/templates/admin/live_logs/_line.html:1-10`)
Reference — JS renders `flex gap-3 px-2 py-0.5 rounded border-l-2 {roleColor}` → `ts | METHOD | path truncate 260px | status font-bold color per family | duration | msg` + `cause pl-6 break-all text-amber-300 border-l-2` if present + `---` separator (`static/dashboard/live_logs.js:139-157`).

---

## Styling

### `live_logs.css` (`static/dashboard/live_logs.css:1-109`)

```css
@font-face { font-family: 'JetBrains Mono'; src: url('/static/fonts/JetBrainsMono-Regular.woff2') woff2; display: swap }
#live-logs-terminal { font-family: 'JetBrains Mono', ui-monospace, monospace }
.live-tab.active { box-shadow: 0 0 0 2px currentColor }
```

Lines `static/dashboard/live_logs.css:12-109` explicitly define every `bg-*/border-*/text-*` + `.dark .dark\:*` variant used by tabs/stats/role pills so Unfold/Tailwind purge never strips them. Add your custom color there.

### Palette — `project/settings/unfold_config.py:61-255`
Full **oklch Obsidian** — `base 50-975 ( #f2ffe7 → #000c02 )`, `primary 50-950`, `blue/red/amber/green/purple/sky/indigo/lime 50-950`, `semantic accent/blue/green/amber/red/purple/electric/navy/ink`, `background/border/text var(--color-*)`. `SIDEBAR` adds `Live Logs icon terminal → reverse_lazy("admin-live-logs")` (`project/settings/unfold_config.py:270-272`).

---

## SSE Implementation

### Backend (`live_logs_stream` — `dashboard/live_logs.py:417-444`)

See Architecture > SSE — Backend for annotated copy. Key headers (`dashboard/live_logs.py:441-443`):

```python
response["Cache-Control"] = "no-cache"
response["X-Accel-Buffering"] = "no"   # tells Nginx not to buffer
response["Content-Encoding"] = "identity"  # no gzip on SSE
```

Staff-only (`@staff_member_required` on both views). Respects `?last_id` gap-fill.

### Frontend (`live_logs.js:1-241`)

See Architecture > Frontend — JS table. Pattern: `EventSource` → `retry: 3000` gap-fill loop `0.5s` → heartbeat `:\n\n` → `DocumentFragment` + debounce `150ms` render.

---

## Nginx & Docker — Production Wiring

### Dev (`nginx.conf:60-80`)

Single `upstream django → web:8000`. SSE location `regex ^/(en|ar)?/?admin/live-logs/stream/` with `proxy_buffering off, proxy_cache off, 3600s timeouts, chunked_transfer_encoding on, gzip off, keep-alive`. Must be before `location /`.

### Prod (`nginx.prod.conf:28-30,147-169` + `docker-compose.prod.yml:57-98`)

| Piece | File:line | Detail |
|---|---|---|
| `web-sse` | `docker-compose.prod.yml:57-98` | `gunicorn gevent --bind 0.0.0.0:8001 --workers 2 --worker-connections 1000 --timeout 0 --graceful-timeout 0 --keep-alive 75 --worker-tmp-dir /dev/shm`, `expose 8001`, `depends_on db/redis` |
| `upstream django_sse` | `nginx.prod.conf:28-30` | `server web-sse:8001` |
| SSE location prod | `nginx.prod.conf:147-169` | Same 13 directives as dev but `proxy_pass http://django_sse`, `X-Forwarded-Port 443` |
| `nginx depends_on` | `docker-compose.prod.yml:183-185` | `depends_on: web, web-sse` |

Why: `gunicorn sync` workers block on long-lived SSE (one worker per tab) — 4 workers stall. Isolating to `2 gevent` with `timeout 0` (never kill SSE) keeps API workers free; `gevent` handles 1000 concurrent via greenlets. Same domain avoids CORS/cert change — Nginx routes internally. Heartbeat `:\n\n` every `0.5s` keeps `proxy_read_timeout 3600s` satisfied. `HTTP/1.1 + Connection ""` enables keep-alive without close; `gzip off` prevents chunk corruption.

---

## Changelog — Latest Updates Since Initial Replica (Exact Changes & Why)

### 4aab2ae `fix(live-logs): correct i18n URL, nginx no-buffer`
**Changed:** `live_logs.html:70` adds `window.__LIVE_LOGS_STREAM_URL__ = "{% url 'admin-live-logs-stream' %}"` + `live_logs.js:219` reads `baseUrl = window.__LIVE_LOGS_STREAM_URL__ || '/admin/live-logs/stream/'` (instead of hardcoded `/admin/...`). `project/urls.py:66-69` adds fallback `admin/live-logs/` + `admin/live-logs/stream/` **without** `i18n` prefix. `nginx.conf:60-80` adds `location ~ ^/(en|ar)?/?admin/live-logs/stream/` with `proxy_buffering off; proxy_cache off; proxy_read_timeout 3600s; chunked_transfer_encoding on`.
**Why:** Page lives under `i18n_patterns` at `/en/admin/live-logs/` but JS `EventSource("/admin/...")` hit non-i18n 404 — fallback fixes. Nginx was buffering SSE, delaying lines until buffer flush — `no-buffer` makes stream live.

### c023064 `isolate SSE: web-sse gthread timeout 0`
**Changed:** `docker-compose.prod.yml:57-98` adds `web-sse` service — same image as `web`, but `--bind 0.0.0.0:8001 --workers 2 --worker-class gthread --threads 4 --timeout 0 --graceful-timeout 0 --keep-alive 75` + `expose 8001` + `depends_on db/redis`. `nginx.prod.conf:28-30,147-169` adds `upstream django_sse { server web-sse:8001 }` + location `~ ^/(en|ar)?/?admin/live-logs/stream/` → `proxy_pass http://django_sse` (same domain, no cert change), `depends_on web-sse` for nginx.
**Why:** `gunicorn sync` workers block on long-lived SSE (one worker per tab) — under 4 workers, 4 admin tabs stall the API. Isolating SSE to 2 `gthread` workers with `timeout 0` (never kill SSE) keeps API workers free. Same domain avoids CORS/cert change — Nginx routes internally.

### 24c2e69 `perf(sse): gevent, heartbeat, no-buffer keep-alive`
**Changed:** `web-sse` switches `gthread` → `gevent` + `--worker-connections 1000` (async, 1000 concurrent per worker) (`docker-compose.prod.yml:75-76`). `requirements.txt:9` adds `gevent==24.11.1`. Both `nginx.conf:60-80` + `nginx.prod.conf:147-169` SSE locations add `proxy_http_version 1.1; proxy_set_header Connection ""; proxy_connect_timeout 10s; send_timeout 3600s; gzip off; add_header Connection "keep-alive"` (in addition to existing `proxy_buffering off` etc).
**Why:** `gthread` still uses threads — under many concurrent tabs it exhausts. `gevent` async handles 1000 connections with one worker via greenlets. `HTTP/1.1` + empty `Connection` enables keep-alive without close, `gzip off` prevents SSE chunk corruption, `heartbeat :\n\n` every `0.5s` keeps connection alive through proxies that kill idle.

### c07bb76 `fix(live-logs): share buffer via Redis`
**Changed:** `dashboard/live_logs.py:22-89` rewrites buffer: `REDIS_KEY="live_logs:buffer"`, `REDIS_SEQ="live_logs:seq"`. `_next_id()` tries `get_redis_connection("default").incr(REDIS_SEQ)` else fallback `Lock + _seq`. `append_log()` tries `lpush REDIS_KEY json.dumps(entry) + ltrim 0:999` else fallback `deque.append`. `get_snapshot(last_id)` tries `lrange REDIS_KEY 0:999 → json.loads + reverse chronological` + filter `id > last_id` else fallback `deque`.
**Why:** In-memory `deque` is per-process — `web:8000` (4 sync workers) and `web-sse:8001` (2 gevent) each had own buffer, so normal API requests logged on `web` never appeared on SSE stream served by `web-sse`. Redis `list` + `incr` is shared across all containers (web, web-sse, celery), so every request appears live. Fallback keeps `TESTING` / local-without-Redis working (in-memory).

**Files changed in these 4 commits:** `dashboard/live_logs.py` (Redis), `dashboard/templates/admin/live_logs.html:70` (+ JS var), `static/dashboard/live_logs.js:219` (baseUrl), `project/urls.py:66-69` (fallback), `nginx.conf` + `nginx.prod.conf` (hardened SSE), `docker-compose.prod.yml:57-98` (web-sse), `requirements.txt:9` (gevent).

---

## Tradeoffs

| Decision | Benefit | Cost |
|---|---|---|
| `deque 1000` fallback (`dashboard/live_logs.py:26`) | Zero I/O, ~300KB, O(1), works without Redis/tests | Ephemeral — lost on restart/deploy, no audit history |
| **Redis list shared (current)** (`dashboard/live_logs.py:56-68,71-89`) | Shared across web + web-sse + workers — live is actually live | Needs Redis (already required for Celery), adds ~60 lines fallback logic |
| **Isolated web-sse gevent** (`docker-compose.prod.yml:57-98`) | SSE never blocks API workers, 1000 concurrent, timeout 0 | Extra container `project_web_sse:8001` + `gevent` dep (`requirements.txt:9`) |
| SSE vs WebSocket | HTTP-only, auto-reconnect (`retry: 3000`), no Channels, Nginx-friendly | One-way server→client only; no client push |
| Self-hosted `JetBrainsMono-Regular.woff2` 92KB (`static/fonts/`) | Offline, no CDN, cached via `staticfiles` | +92KB repo |
| 1000 cap (`dashboard/live_logs.py:21`) | No DOM leak, `DocumentFragment` render stays fast (`static/dashboard/live_logs.js:134`) | Old lines lost — `Download` quickly or tee to DB |
| Heartbeat `:\n\n` every 0.5s (`dashboard/live_logs.py:438`) | Keeps proxies/Nginx from killing idle (`proxy_read_timeout 3600s` still safe) | Tiny bandwidth (2 bytes * 2/s) |
| `@staff_member_required` (`dashboard/live_logs.py:408,417`) | No extra permission infra; piggybacks Django admin session | API JWT users can't open stream — by design |

---

## How to Use (already wired)

### 1. Open the terminal

```python
# project/settings/base.py:121 — already present
MIDDLEWARE = ["dashboard.live_logs.LiveLogsMiddleware", ...]

# project/urls.py:55,66 — already present
from dashboard.live_logs import live_logs_page, live_logs_stream
path("admin/live-logs/", live_logs_page, name="admin-live-logs"),
path("admin/live-logs/stream/", live_logs_stream, name="admin-live-logs-stream"),
# + fallback nolang
```

Visit `/en/admin/live-logs/` as `is_staff` → live terminal, tabs `All/2XX/3XX/4XX/5XX`, role pills `All Roles/Customer/Deliveryman/Ops/Guest`, stats + insights update live. `Pause/Clear/Download` + `Search` + `Auto-scroll` + status.

### 2. Read logs programmatically (copy-paste)

```python
from dashboard.live_logs import get_snapshot, append_log

# Get last 1000 entries (shared Redis list, fallback deque)
logs = get_snapshot(last_id=0)  # list[dict] with ts/method/path/status/level/user/role/duration/msg/cause
# Filter in Python
errors = [e for e in logs if e["status"] >= 400]
for e in errors:
    print(e["msg"], e["cause"])

# Append custom entry (e.g. from signal)
append_log({"ts": "12:00:00", "method": "POST", "path": "/api/v1/orders/", "status": 201, "level": "INFO", "msg": "Order created", "cause": ""})

# Gap-fill after disconnect: client sends ?last_id=123
new_logs = get_snapshot(last_id=123)
```

### 3. Trigger and verify JWT diagnostics

```bash
curl -i http://localhost:8000/api/v1/users/me/  # no Authorization
# → terminal shows amber 401: Missing Authorization (expected 'Bearer <access>')

curl -i http://localhost:8000/api/v1/users/me/ -H "Authorization: Bearer bad.token"
# → amber 401: Malformed JWT: 2 parts (expected 3 header.payload.signature)

curl -i http://localhost:8000/api/v1/users/me/ -H "Authorization: bearer eyJ..."
# → amber 401: Wrong scheme 'bearer' (must be 'Bearer' capital B)

curl -X POST http://localhost:8000/api/v1/users/auth/social/google/ -H "Content-Type: application/json" -d '{}'
# → if missing Origin: Missing Origin header on OAuth POST (CORS may block)
```

---

## Verification

- Open `/en/admin/live-logs/` as `is_staff` → lines appear live, no DB query in debug-toolbar (`__debug__/`)
- Trigger `POST /api/v1/users/token/refresh/` with missing `Bearer` → `4XX amber` with `Missing Authorization` cause + `JWT invalid/expired — check ACCESS_TOKEN_LIFETIME`
- Send `Authorization: Bearer bad.token` → `Malformed JWT: 2 parts` cause (`dashboard/live_logs.py:188`)
- Trigger `500` (raise in shell) → `5XX red` with `ValueError | Trace: dashboard/live_logs.py:116`
- Search `401` or `/users/me` → `<mark>` highlights, `No results for "q"` empty state if filtered
- Roles: request as `customer` vs `guest` → left border `blue-500` vs `white` (`static/dashboard/live_logs.js:115-122`), role pills filter
- `Download` → `live-logs-YYYY-MM-DDTHH:MM:SS.txt` with `-----------` separators
- Restart server or `redis-cli del live_logs:buffer live_logs:seq` → buffer clears (expected, ephemeral)
- `TESTING=True python manage.py test` → fallback deque path, no Redis required

---

## REUSE Notes

- **Copy verbatim** — no domain logic (JWT paths cover generic `/users/ /token /jwt /auth /social /accounts/` + `/social/ /oauth /google /facebook /firebase` at `dashboard/live_logs.py:134-141`)
- `BUSINESS_TIME_ZONE` not required — logs use `UTC` `timezone.now().isoformat()` (`dashboard/live_logs.py:392`)
- Font pushed to repo — no CDN; collectstatic handles `static/fonts/JetBrainsMono-Regular.woff2`
- No migrations, no settings beyond `MIDDLEWARE` (`project/settings/base.py:121`) + `gevent` (`requirements.txt:9`)
- Roles are generic — change `dashboard/templates/admin/live_logs.html:36-41` pills + `static/dashboard/live_logs.js:115-122` `roleColor()` to match your `CustomUser.Role` (e.g. `admin/user/guest`). Keep `"guest"` fallback (`dashboard/live_logs.py:389`).
- `MAX_LINES` is the only tunables — no env var, single file edit (`dashboard/live_logs.py:21` + `static/dashboard/live_logs.js:230`)

---

## Removal — How to Remove This Feature

> Fully decoupled — live logs touches no other app. Deleting it frees ~300KB Redis + one container.

### Full Removal (drop middleware + page + SSE)

1. **Middleware `project/settings/base.py:121`** → delete `"dashboard.live_logs.LiveLogsMiddleware"` from `MIDDLEWARE` (1 line).
2. **URLs `project/urls.py:15,66-69`** → delete `from dashboard.live_logs import live_logs_page, live_logs_stream` + `i18n_patterns admin/live-logs/` + `admin/live-logs/stream/` + fallback `admin/live-logs-nolang` (4 paths + import).
3. **Delete app files** `dashboard/live_logs.py` (444 lines), `dashboard/templates/admin/live_logs.html` + `dashboard/templates/admin/live_logs/` (6 files: `_tabs.html`, `_stats.html`, `_insights.html`, `_controls.html`, `_terminal.html`, `_line.html`), `static/dashboard/live_logs.js` (241 lines), `static/dashboard/live_logs.css` (109 lines), `static/fonts/JetBrainsMono-Regular.woff2` (92KB) — **or keep font if you use JetBrains elsewhere**.
4. **Admin `project/settings/unfold_config.py:270-272`** → delete `Live Logs` item under `SIDEBAR Navigation` (`title: Live Logs`, `icon: terminal`, `link: admin-live-logs`).
5. **Docker `docker-compose.prod.yml:57-98`** → delete entire `web-sse` service (42 lines: `gunicorn gevent :8001`, `expose 8001`, `depends_on db/redis`).
6. **Nginx `nginx.conf:60-80` + `nginx.prod.conf:28-30,147-169`** → delete both `location ~ ^/(en|ar)?/?admin/live-logs/stream/` blocks (each ~20 lines, `proxy_buffering off` etc) + `upstream django_sse` (prod `nginx.prod.conf:28-30`). Remove `web-sse` from `nginx depends_on` (`docker-compose.prod.yml:184-185`).
7. **Requirements `requirements.txt:9`** → delete `gevent==24.11.1` **only if** no other `gevent` usage (live logs is the sole consumer). Else keep.
8. **Check** `python manage.py check && docker compose config > /dev/null && docker compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null` — ensure no `ModuleNotFoundError: dashboard.live_logs`.

### Partial — Keep Logging, Drop SSE Page Only

- Keep `dashboard/live_logs.py:56-89` buffer + `LiveLogsMiddleware` (`dashboard/live_logs.py:92-405`) (still logs to Redis/deque for debugging via shell: `from dashboard.live_logs import get_snapshot; get_snapshot()`).
- Delete only `live_logs_page`/`live_logs_stream` views (`dashboard/live_logs.py:408-444`) + templates/static + URL routes + admin nav + `web-sse` + nginx SSE blocks. Logs remain queryable programmatically via `get_snapshot()` / `append_log()`.

After removal, run `make check-format && make test` (or `python manage.py check && pytest`).