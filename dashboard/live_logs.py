"""Live log streaming for the admin.

Captures request/response metadata via middleware, buffers it in Redis (fallback
to in-memory deque), and exposes SSE endpoints for real-time admin monitoring.
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

MAX_LINES = 500
REDIS_KEY = "live_logs:buffer"
REDIS_SEQ = "live_logs:seq"

# Fallback in-memory for when Redis is down (tests, local without Redis)
_buffer: deque = deque(maxlen=MAX_LINES)
_lock = Lock()
_seq = 0


def _next_id() -> int:
    """Return a monotonically increasing log entry ID via Redis or memory."""
    try:
        from django.core.cache import cache
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        return int(conn.incr(REDIS_SEQ))
    except Exception:
        global _seq
        with _lock:
            _seq += 1
            return _seq


def _redis_available() -> bool:
    """Check whether Redis is reachable for shared log buffering."""
    try:
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        conn.ping()
        return True
    except Exception:
        return False


def append_log(entry: dict) -> None:
    """Append a log entry to Redis or the in-memory fallback buffer."""
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
    """Return buffered log entries after the given ID in chronological order."""

    # Try Redis first (shared across web + web-sse workers)
    try:
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        raw = conn.lrange(REDIS_KEY, 0, MAX_LINES - 1)
        if raw:
            entries = [json.loads(x) for x in raw]
            entries.reverse()  # lpush → reverse to chronological
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
    """Middleware that captures request timing and auth diagnostics for live logs."""

    def __init__(self, get_response):
        """Initialize the middleware with the next handler."""
        self.get_response = get_response

    def __call__(self, request):
        """Process the request and append a structured log entry.

        Captures JWT/OAuth header diagnostics on 4xx/5xx responses to speed up
        authentication debugging without leaking tokens.
        """
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
                    if exc_info is not None:
                        tb = traceback.format_exception(
                            type(exc_info), exc_info, exc_info.__traceback__
                        )
                        tail = "".join(tb[-3:])[-800:]
                        cause = f"{type(exc_info).__name__}: {exc_info} | {tail}"
                    else:
                        cause = getattr(response, "reason_phrase", "") or (
                            response.reason_phrase if response else ""
                        )
                        # JWT / OAuth detailed cause (forget normal auth, focus on these)
                        try:
                            path_lc = request.get_full_path().lower()
                            data = getattr(response, "data", None)
                            header = (
                                request.headers.get("Authorization")
                                or request.META.get("HTTP_AUTHORIZATION")
                                or ""
                            )
                            is_jwt_path = any(
                                k in path_lc
                                for k in ["/users/", "/token", "/jwt", "/auth/social", "/accounts/"]
                            )
                            is_oauth_path = any(
                                k in path_lc
                                for k in ["/social/", "/oauth", "/google", "/facebook", "/firebase"]
                            )
                            if is_jwt_path or is_oauth_path or status in (401, 403):
                                details = []
                                # Low-level header diagnostics (no token leakage) — the juice for JWT/OAuth
                                raw_header = header
                                header_stripped = header.strip() if header else ""
                                if not header:
                                    details.append(
                                        "Missing Authorization header (expected 'Bearer <access>')"
                                    )
                                else:
                                    # Raw vs stripped whitespace
                                    if raw_header != header_stripped:
                                        details.append(
                                            "Header has leading/trailing whitespace (trimmed)"
                                        )
                                    # Multiple values (comma)
                                    if "," in header_stripped:
                                        details.append(
                                            "Multiple Authorization values (comma-separated) — only first will be used"
                                        )
                                    # Scheme check — case-sensitive per RFC 6750
                                    scheme = (
                                        header_stripped.split(" ", 1)[0]
                                        if " " in header_stripped
                                        else header_stripped
                                    )
                                    if scheme != "Bearer":
                                        details.append(
                                            f"Wrong scheme '{scheme}' (must be 'Bearer' capital B) — got '{header_stripped[:24]}...'"
                                        )
                                    elif header_stripped == "Bearer":
                                        details.append(
                                            "Bearer scheme with no token (empty after 'Bearer ')"
                                        )
                                    elif "  " in header_stripped:
                                        details.append(
                                            "Double-space after Bearer (expected single space)"
                                        )
                                    else:
                                        token = header_stripped[len("Bearer ") :].strip()
                                        if not token:
                                            details.append("Empty token after Bearer")
                                        else:
                                            # JWT structure low-level
                                            parts = token.split(".")
                                            if len(parts) != 3:
                                                details.append(
                                                    f"Malformed JWT: {len(parts)} parts (expected 3 header.payload.signature)"
                                                )
                                            else:
                                                # Check each part is base64-ish and starts like a JWT
                                                import base64
                                                import re

                                                for idx, p in enumerate(parts):
                                                    if not p:
                                                        details.append(f"JWT part {idx+1} is empty")
                                                    elif not re.match(r"^[A-Za-z0-9_-]+={0,2}$", p):
                                                        details.append(
                                                            f"JWT part {idx+1} has invalid base64 chars"
                                                        )
                                                if not token.startswith("eyJ"):
                                                    details.append(
                                                        "Token doesn't start with 'eyJ' — likely not a JWT access token (maybe refresh token or truncated)"
                                                    )
                                                # Quick header decode peek (no verify)
                                                try:
                                                    pad = "=" * (-len(parts[0]) % 4)
                                                    hdr = json.loads(
                                                        base64.urlsafe_b64decode(
                                                            parts[0] + pad
                                                        ).decode()
                                                    )
                                                    if hdr.get("alg") not in (
                                                        "HS256",
                                                        "RS256",
                                                        None,
                                                    ):
                                                        details.append(
                                                            f"JWT alg={hdr.get('alg')} unexpected"
                                                        )
                                                except Exception:
                                                    details.append(
                                                        "JWT header not decodable (corrupted base64)"
                                                    )
                                # Other low-level headers that affect auth (CORS/CSRF)
                                origin = (
                                    request.headers.get("Origin")
                                    or request.META.get("HTTP_ORIGIN")
                                    or ""
                                )
                                ct = (  # noqa: F841 - kept for parity with ras-elbar-go diagnostics
                                    request.headers.get("Content-Type")
                                    or request.META.get("CONTENT_TYPE")
                                    or ""
                                )
                                if is_oauth_path and not origin and request.method == "POST":
                                    details.append(
                                        "Missing Origin header on OAuth POST (CORS may block)"
                                    )
                                if (
                                    is_jwt_path
                                    and status == 401
                                    and not header
                                    and request.headers.get("X-Requested-With")
                                ):
                                    details.append(
                                        "XHR without Authorization — ensure Flutter/Dio attaches Bearer on retries"
                                    )
                                # Response payload details (DRF)
                                if isinstance(data, dict):
                                    # SimpleJWT style
                                    det = data.get("detail") or data.get("message") or ""
                                    code = data.get("code") or (
                                        data.get("error", {}).get("code")
                                        if isinstance(data.get("error"), dict)
                                        else ""
                                    )
                                    msgs = data.get("messages") or []
                                    if det:
                                        details.append(f"detail={det}")
                                    if code:
                                        details.append(f"code={code}")
                                    if msgs:
                                        details.append(f"messages={str(msgs)[:200]}")
                                    # allauth / DRF error envelope
                                    err = data.get("error")
                                    if isinstance(err, dict):
                                        if err.get("message"):
                                            details.append(f"error.message={err['message']}")
                                        if err.get("details"):
                                            details.append(
                                                f"error.details={str(err['details'])[:200]}"
                                            )
                                    # OAuth specific
                                    if "token_not_valid" in str(code) or "token_not_valid" in str(
                                        det
                                    ):
                                        details.append(
                                            "JWT invalid/expired — check ACCESS_TOKEN_LIFETIME, SECRET_KEY, or refresh flow"
                                        )
                                    if "expired" in str(det).lower():
                                        details.append(
                                            "JWT expired — client should refresh via /users/token/refresh/"
                                        )
                                    if is_oauth_path and status >= 400:
                                        details.append(f"OAuth path {request.path} failed")
                                # Fallback to response body snippet if no data
                                if not details and hasattr(response, "content"):
                                    try:
                                        snippet = response.content[:300].decode(errors="ignore")
                                        if snippet:
                                            details.append(f"body={snippet[:200]}")
                                    except Exception:
                                        pass
                                if details:
                                    cause = " | ".join(details)[:1000]
                        except Exception:
                            pass
                user_id = ""
                try:
                    if hasattr(request, "user") and getattr(
                        request.user, "is_authenticated", False
                    ):
                        user_id = str(
                            getattr(request.user, "id", "") or getattr(request.user, "email", "")
                        )
                except Exception:
                    pass
                append_log(
                    {
                        "ts": timezone.now().isoformat(),
                        "method": request.method,
                        "path": request.get_full_path(),
                        "status": status,
                        "level": level,
                        "user": user_id[:24],
                        "duration": duration_ms,
                        "msg": f"{request.method} {request.get_full_path()}",
                        "cause": cause[:1000],
                    }
                )
            except Exception:
                pass


@staff_member_required
def live_logs_page(request):
    """Render the admin live-logs HTML page (staff only)."""
    from django.contrib import admin

    context = admin.site.each_context(request)
    context.update({"title": "Live Logs"})
    return render(request, "admin/live_logs.html", context)


@staff_member_required
def live_logs_stream(request):
    """SSE endpoint that streams log entries as an event-stream (staff only)."""
    last_id = int(request.GET.get("last_id", "0") or 0)

    def event_stream():
        nonlocal last_id
        yield "retry: 3000\n\n"
        # Send snapshot gap-fill
        snapshot = get_snapshot(last_id)
        for entry in snapshot:
            last_id = entry["id"]
            yield f"id: {entry['id']}\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"
        # Keep alive
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
