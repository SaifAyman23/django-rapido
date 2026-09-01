# Live Logs Guide — SSE In-Memory Admin Terminal (REUSE)

> Exact replica from `ras-elbar-go` — `dashboard/live_logs.py` hash `48b161be441f`. No DB, no files, no WebSockets.

## Goal

Live, zero-refresh request stream inside Django admin. Watch every `2XX/3XX/4XX/5XX` with cause diagnostics for JWT/OAuth, without disk or DB load.

```
Request → LiveLogsMiddleware → deque(maxlen=500) ──→ SSE (StreamingHttpResponse) ──→ EventSource → terminal + stats + insights
                      500 lines ~100KB              text/event-stream  retry:3000  heartbeat :\n\n every 0.5s
```

---

## Files (exact replica)

```
dashboard/live_logs.py                           # 225 lines — buffer + middleware + views
dashboard/templates/admin/live_logs.html         # shell: tabs + stats + insights + controls + terminal
dashboard/templates/admin/live_logs/_tabs.html   # pills All/2XX/3XX/4XX/5XX data-count
dashboard/templates/admin/live_logs/_stats.html  # 5 cards Total/2XX/3XX/4XX/5XX data-stat-*
dashboard/templates/admin/live_logs/_insights.html # 4 cards Error Rate/Top Path/Busiest Method/Success Rate
dashboard/templates/admin/live_logs/_controls.html # Pause/Clear + status connecting…
dashboard/templates/admin/live_logs/_terminal.html # #live-logs-terminal oklch 9.5% 560px scroll
dashboard/templates/admin/live_logs/_line.html   # reference partial (JS renders lines)
static/dashboard/live_logs.js                    # 153 lines — EventSource + tab/filter + stats
static/dashboard/live_logs.css                   # @font-face JetBrains Mono + terminal styles
static/fonts/JetBrainsMono-Regular.woff2         # 92380 bytes self-hosted
project/settings/base.py:127                     # MIDDLEWARE dashboard.live_logs.LiveLogsMiddleware
project/urls.py:43                               # i18n admin/live-logs/ + admin/live-logs/stream/
project/settings/unfold_config.py                # oklch palette + SIDEBAR Live Logs (terminal icon)
```

---

## Logic — `dashboard/live_logs.py`

### Buffer

```python
MAX_LINES = 500
_buffer: deque = deque(maxlen=MAX_LINES)
_lock = Lock()
_seq = 0

def _next_id() -> int:  # Lock → _seq +=1
def append_log(entry: dict) -> None:  # {**entry, "id": _next_id()} → _buffer.append
def get_snapshot(last_id: int = 0) -> list[dict]:  # all if 0 else [e for e if e["id"] > last_id]
```

`500 * ~200 bytes ≈ 100KB` — `O(1)` append, auto-evicts oldest. Ephemeral — vanishes on restart/redeploy. Single-process (each Gunicorn worker has own buffer; admin sees its worker).

### Middleware — Full Context

```python
class LiveLogsMiddleware:
    def __call__(self, request):
        start = time.monotonic()
        response = None; exc_info = None
        try: response = self.get_response(request); return response
        except Exception as exc: exc_info = exc; raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            status = response.status_code if response else 500
            if exc_info: status = 500
            level = "INFO" if status < 400 else "WARN" if status < 500 else "ERROR"
            cause = ""  # for >=400
```

`cause` building for `status >=400`:
- `exc_info → traceback.format_exception(...)[-3:] → type: msg | tail -800`
- Else `response.reason_phrase`
- **JWT/OAuth diagnostics** (juice for `401/403` + paths `/users/ /token /jwt /auth/social /oauth /google /facebook`):
  - Header `Authorization` / `HTTP_AUTHORIZATION` raw vs stripped → `Missing Authorization`, `leading/trailing whitespace`, `Multiple values (comma)`, `scheme != 'Bearer'`, `Bearer` empty, `Double-space`, `Empty token`
  - Token → `len(parts) !=3 (header.payload.signature)`, per-part empty / `^[A-Za-z0-9_-]+={0,2}$`, `not startswith eyJ`, header decode `base64.urlsafe_b64decode(parts[0]) → alg HS256/RS256`
  - `Origin` missing on OAuth POST, `XHR without Authorization`
  - `response.data` → `detail/code/messages/error.message/error.details`, `token_not_valid → check ACCESS_TOKEN_LIFETIME/SECRET_KEY`, `expired → refresh via /users/token/refresh/`, `OAuth path failed`
  - Fallback `response.content[:300]`

`user_id = request.user.id/email[:24]` if authenticated, then `append_log({ts, method, path, status, level, user, duration, msg: "METHOD path", cause[:1000]})`.

### Views

```python
@staff_member_required
def live_logs_page(request):  # admin.site.each_context + render admin/live_logs.html

@staff_member_required
def live_logs_stream(request):  # GET ?last_id=0
    # event_stream() yields retry:3000, snapshot gap-fill, then loop sleep 0.5 → get_snapshot or :\n\n heartbeat
    # StreamingHttpResponse(text/event-stream) + Cache-Control no-cache / X-Accel-Buffering no / Content-Encoding identity
```

REUSE: Wire once — `base.py:127` `dashboard.live_logs.LiveLogsMiddleware` + `project/urls.py:43` `i18n_patterns admin/live-logs/`.

---

## Pages — Templates (Tailwind, component-based)

### `live_logs.html`
`extends admin/base.html` → `branding` unfold helper → `extrahead live_logs.css` → header `Live Logs` → includes `tabs → stats → insights → controls → terminal` (`bg-white dark:bg-base-900 rounded-xl shadow-sm border`) → `script live_logs.js`.

### `_tabs.html`
`data-tab="all/2xx/3xx/4xx/5xx"` pills `rounded-full font-mono font-bold` `All active bg-primary-500` + `data-count="all/2xx..."` live counts.

### `_stats.html`
`grid 5` cards: `TOTAL neutral (100%)`, `2XX green`, `3XX blue`, `4XX amber (primary-100)`, `5XX red` — `data-stat-total/2xx/3xx/4xx/5xx + data-stat-*-p` percentages, clickable → tab.

### `_insights.html`
`grid 4` cards: `ERROR RATE 4XX+5XX/Total`, `TOP ERROR PATH most frequent 4XX/5XX path (click to filter)`, `BUSIEST METHOD + avg ms`, `SUCCESS RATE 2XX/Total`.

### `_controls.html`
`Pause/Resume + Clear` `rounded-xl bg-white dark:bg-base-900 border` + `status live/connecting…/reconnecting…` `font-mono`.

### `_terminal.html`
`#live-logs-terminal font-mono text-xs rounded-xl shadow-sm p-4 overflow-auto` `background var(--color-base-950, oklch 9.5%) color var(--color-base-100) max-height 560px` → `#live-logs-lines space-y-1` (only scrollable area).

### `_line.html`
Reference — JS renders `flex gap-3 px-2 py-0.5 rounded` → `ts | METHOD | path truncate 260px | status font-bold color per family | duration | msg` + `cause pl-6 truncate text-amber-300` if present.

---

## Styling

### `live_logs.css`
```css
@font-face { font-family: 'JetBrains Mono'; src: url('/static/fonts/JetBrainsMono-Regular.woff2') woff2; display: swap }
#live-logs-terminal { font-family: 'JetBrains Mono', ui-monospace, monospace }
.live-tab.active { box-shadow: 0 0 0 2px }
.live-line.cause-open { background: rgba(255,255,255,0.06) }
```

### Palette — `project/settings/unfold_config.py`
Full **oklch Obsidian** — `base 50-975 ( #f2ffe7 obsidian white → #000c02 pure obsidian )`, `primary 50-950`, `blue 50-950`, `red 50-950`, `amber 50-950`, `green 50-950`, `semantic accent/blue/green/amber/red/purple/electric/navy/ink`, `background/border/text` `var(--color-*)`. `SIDEBAR` adds `Live Logs icon terminal → reverse_lazy("admin-live-logs")`.

---

## SSE Implementation

### Backend (`live_logs_stream`)
```python
def event_stream():
    nonlocal last_id
    yield "retry: 3000\n\n"  # EventSource auto-reconnect 3s
    for entry in get_snapshot(last_id): yield f"id: {entry['id']}\ndata: {json.dumps(entry)}\n\n"
    while True:
        time.sleep(0.5)
        new_entries = get_snapshot(last_id)
        if new_entries:
            for entry in new_entries: yield f"id: {entry['id']}\ndata: {json.dumps(entry)}\n\n"
        else: yield ":\n\n"  # heartbeat

StreamingHttpResponse(event_stream(), content_type="text/event-stream")
response["Cache-Control"] = "no-cache"
response["X-Accel-Buffering"] = "no"
response["Content-Encoding"] = "identity"
```

Staff-only (`@staff_member_required`). Respects `Last-Event-ID / ?last_id` gap-fill.

### Frontend (`live_logs.js:1-153`)

```js
els = { tabs, total, s2xx..s5xx, cAll..c5xx, errRate, topPath, method, avg, successRate, lines, term, pauseBtn, clearBtn, auto, status }
activeTab='all', paused=false, lastId=0, buffer=[]

family(status) → 5xx>=500 4xx>=400 3xx>=300 2xx>=200
renderStats() → total=len, c{2xx,3xx,4xx,5xx}, paths 4XX/5XX freq, methods freq, durSum → pct, successRate, topPath, topM, avg
visible(e) → all or family==activeTab
color(status) → red-400/amber-300/blue-400/green-400
render() → if paused stats only; else clear lines → create div live-line flex gap-3 + cause amber-300 truncate → renderStats → auto.checked scroll
scheduleRender() → debounced 150ms
tabs click → activeTab + active class → render
pause → toggle Resume/Pause; clear → buffer=[]
connect() → EventSource /admin/live-logs/stream/?last_id → onopen live, onmessage JSON.parse, lastId=ev.lastEventId||data.id, buffer push shift>500, scheduleRender, onerror reconnecting… close setTimeout 3000
```

Nginx needs `proxy_read_timeout 3600s` for long-lived SSE (most proxies default ok).

---

## Changelog — Latest Updates Since Initial Replica (Exact Changes & Why)

### 4aab2ae `fix(live-logs): correct i18n URL, nginx no-buffer`
**Changed:** `live_logs.html` adds `window.__LIVE_LOGS_STREAM_URL__ = "{% url 'admin-live-logs-stream' %}"` + `live_logs.js` reads `baseUrl = window.__LIVE_LOGS_STREAM_URL__ || '/admin/live-logs/stream/'` (instead of hardcoded `/admin/...`). `project/urls.py` adds fallback `admin/live-logs/` + `admin/live-logs/stream/` **without** `i18n` prefix. `nginx.conf` adds `location ~ ^/(en|ar)?/?admin/live-logs/stream/` with `proxy_buffering off; proxy_cache off; proxy_read_timeout 3600s; chunked_transfer_encoding on`.
**Why:** Page lives under `i18n_patterns` at `/en/admin/live-logs/` but JS `EventSource("/admin/...")` hit non-i18n 404 — fallback fixes. Nginx was buffering SSE, delaying lines until buffer flush — `no-buffer` makes stream live.

### c023064 `isolate SSE: web-sse gthread timeout 0`
**Changed:** `docker-compose.prod.yml` adds `web-sse` service — same image as `web`, but `--bind 0.0.0.0:8001 --workers 2 --worker-class gthread --threads 4 --timeout 0 --graceful-timeout 0 --keep-alive 75` + `expose 8001` + `depends_on db/redis`. `nginx.prod.conf` adds `upstream django_sse { server web-sse:8001 }` + location `~ ^/(en|ar)?/?admin/live-logs/stream/` → `proxy_pass http://django_sse` (same domain, no cert change), `depends_on web-sse` for nginx.
**Why:** `gunicorn sync` workers block on long-lived SSE (one worker per tab) — under 4 workers, 4 admin tabs stall the API. Isolating SSE to 2 `gthread` workers with `timeout 0` (never kill SSE) keeps API workers free. Same domain avoids CORS/cert change — Nginx routes internally.

### 24c2e69 `perf(sse): gevent, heartbeat, no-buffer keep-alive`
**Changed:** `web-sse` switches `gthread` → `gevent` + `--worker-connections 1000` (async, 1000 concurrent per worker). `requirements.txt` adds `gevent==24.11.1`. Both `nginx.conf` + `nginx.prod.conf` SSE locations add `proxy_http_version 1.1; proxy_set_header Connection ""; proxy_connect_timeout 10s; send_timeout 3600s; gzip off; add_header Connection "keep-alive"` (in addition to existing `proxy_buffering off` etc).
**Why:** `gthread` still uses threads — under many concurrent tabs it exhausts. `gevent` async handles 1000 connections with one worker via greenlets. `HTTP/1.1` + empty `Connection` enables keep-alive without close, `gzip off` prevents SSE chunk corruption, `heartbeat :\n\n` every 0.5s keeps connection alive through proxies that kill idle.

### c07bb76 `fix(live-logs): share buffer via Redis`
**Changed:** `dashboard/live_logs.py` rewrites buffer: `REDIS_KEY="live_logs:buffer"`, `REDIS_SEQ="live_logs:seq"`. `_next_id()` tries `get_redis_connection("default").incr(REDIS_SEQ)` else fallback `Lock + _seq`. `append_log()` tries `lpush REDIS_KEY json.dumps(entry) + ltrim 0:499` else fallback `deque.append`. `get_snapshot(last_id)` tries `lrange REDIS_KEY 0:499 → json.loads + reverse chronological` + filter `id > last_id` else fallback `deque`.
**Why:** In-memory `deque` is per-process — `web:8000` (4 sync workers) and `web-sse:8001` (2 gevent) each had own buffer, so normal API requests logged on `web` never appeared on SSE stream served by `web-sse`. Redis `list` + `incr` is shared across all containers (web, web-sse, celery), so every request appears live. Fallback keeps `TESTING` / local-without-Redis working (in-memory).

**Files changed in these 4 commits:** `dashboard/live_logs.py` (Redis), `dashboard/templates/admin/live_logs.html` (+ JS var), `static/dashboard/live_logs.js` (baseUrl), `project/urls.py` (fallback), `nginx.conf` + `nginx.prod.conf` (hardened SSE), `docker-compose.prod.yml` (web-sse), `requirements.txt` (gevent).

---

## Tradeoffs (Updated)

| Decision | Benefit | Cost |
|----------|---------|------|
| `deque 500` in-memory (fallback) | Zero I/O, ~100KB, O(1), works without Redis/tests | Ephemeral — lost on restart/deploy, no audit history |
| **Redis list shared (latest)** | Shared across web + web-sse + workers — live is actually live | Needs Redis (already required for Celery), adds ~44 lines fallback logic |
| **Isolated web-sse gevent** | SSE never blocks API workers, 1000 concurrent, timeout 0 | Extra container `project_web_sse:8001` + `gevent` dep |
| SSE vs WebSocket | HTTP-only, auto-reconnect, no Channels | One-way server→client only |
| Self-hosted `JetBrainsMono-Regular.woff2` 92KB | Offline, no CDN, cached | +92KB repo |
| 500 cap | No DOM leak, fast render | Old lines lost — copy quickly |

---

## Usage

1. Add to `MIDDLEWARE`: `dashboard.live_logs.LiveLogsMiddleware` (already wired `base.py:127`)
2. Open `/admin/live-logs/` as staff → live terminal
3. Trigger requests — watch cards increment, insights update, causes appear for 4XX/5XX with JWT diagnostics
4. Filter via tabs (pure JS on buffer, no fetch), pause/clear, auto-scroll toggle

## Verification

- Open `/admin/live-logs/` → lines appear live, no DB query in debug-toolbar
- Trigger `POST /api/v1/users/token/refresh/` with missing `Bearer` → `4XX amber` with `Missing Authorization` cause
- Trigger `500` → `5XX red` with `IntegrityError | Trace: orders/views.py:88`
- Restart server → buffer clears (expected)

## REUSE Notes

- **Copy verbatim** — no domain logic (JWT paths cover generic `/users/ /token /jwt /auth /social`)
- `BUSINESS_TIME_ZONE` not required here — logs use `UTC` `timezone.now().isoformat()`
- Font pushed to repo — no CDN
- No migrations, no settings beyond middleware

See `docs/plan-live-logging.md` (original plan) for context.

---

## Removal — How to Remove This Feature

> Fully decoupled — live logs touches no other app. Deleting it frees ~500KB Redis + one container.

### Full Removal (drop middleware + page + SSE)

1. **Settings `project/settings/base.py:127`** → delete `dashboard.live_logs.LiveLogsMiddleware` from `MIDDLEWARE` (1 line).
2. **URLs `project/urls.py`** → delete `from dashboard.live_logs import live_logs_page, live_logs_stream` + `i18n_patterns admin/live-logs/` + `admin/live-logs/stream/` + fallback `admin/live-logs-nolang` (4 paths + import).
3. **Delete app files** `dashboard/live_logs.py` (225 lines), `dashboard/templates/admin/live_logs.html` + `dashboard/templates/admin/live_logs/` (6 files: `_tabs.html`, `_stats.html`, `_insights.html`, `_controls.html`, `_terminal.html`, `_line.html`), `static/dashboard/live_logs.js` (153 lines), `static/dashboard/live_logs.css` (10 lines), `static/fonts/JetBrainsMono-Regular.woff2` (92KB) — **or keep font if you use JetBrains elsewhere**.
4. **Admin** `project/settings/unfold_config.py` → delete `Live Logs` item under `Navigation` (`title: Live Logs`, `icon: terminal`, `link: admin-live-logs`).
5. **Docker `docker-compose.prod.yml`** → delete entire `web-sse` service (50 lines: `gunicorn gevent :8001`, `expose 8001`, `depends_on db/redis`).
6. **Nginx `nginx.conf:56` + `nginx.prod.conf:144`** → delete both `location ~ ^/(en|ar)?/?admin/live-logs/stream/` blocks (each 15 lines, `proxy_buffering off` etc) + `upstream django_sse` (prod). Keep `depends_on web-sse` removal in prod `nginx` service.
7. **Requirements `requirements.txt:8`** → delete `gevent==24.11.1` **only if** no other `gevent` usage (live logs is the sole consumer). Else keep.
8. **Check** `make check && docker compose config > /dev/null && docker compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null` — ensure no `ModuleNotFoundError: dashboard.live_logs`.

### Partial — Keep Logging, Drop SSE Page Only

- Keep `dashboard/live_logs.py` middleware (still logs to Redis/deque for debugging via shell: `from dashboard.live_logs import get_snapshot; get_snapshot()`).
- Delete only `live_logs_page`/`live_logs_stream` views + templates/static + URL routes + admin nav + `web-sse` + nginx blocks. Logs remain queryable programmatically.

After removal, run `make check-format && make test`.
