"""
REUSE: Generic live logs — Redis-shared (fallback deque), SSE, JWT diagnostics.

- MAX_LINES 1000 easy global to tune, ~300KB RAM, no env needed
- Roles: generic — reads user.role lowercased, fallback "guest" (change role filters in templates to match your Role)
- JWT diagnostics: generic, no token leakage, safe metadata only
- From ras-elbar-go/backend/dashboard/live_logs.py — project-agnostic, decoupled.
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

# Fallback in-memory for when Redis is down (tests, local without Redis)
_buffer: deque = deque(maxlen=MAX_LINES)
_lock = Lock()
_seq = 0


def _next_id() -> int:
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
                    if exc_info is not None:
                        tb = traceback.format_exception(
                            type(exc_info), exc_info, exc_info.__traceback__
                        )
                        tail = "".join(tb[-5:])
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
                                ct = (  # noqa: F841 - kept for parity
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
                                # ── Received JWT metadata (for /users/me/ etc.) — safe, no token ──
                                if (
                                    header
                                    and status in (401, 403)
                                    and any(k in path_lc for k in ["/users/me", "/users/users/me"])
                                ):
                                    try:
                                        import base64
                                        import hashlib
                                        import re

                                        from rest_framework_simplejwt.settings import api_settings
                                        from rest_framework_simplejwt.tokens import AccessToken

                                        # Try to decode header/payload without verification for metadata
                                        token = (
                                            header_stripped[len("Bearer ") :]
                                            .strip()
                                            .strip('"')
                                            .strip("'")
                                            if header_stripped.startswith("Bearer ")
                                            else ""
                                        )
                                        if token and token.count(".") == 2:
                                            parts = token.split(".")
                                            try:
                                                pad = "=" * (-len(parts[1]) % 4)
                                                payload = json.loads(
                                                    base64.urlsafe_b64decode(
                                                        parts[1] + pad
                                                    ).decode()
                                                )
                                                # Safe metadata
                                                token_type = payload.get("token_type", "")
                                                user_id = payload.get("user_id") or payload.get(
                                                    api_settings.USER_ID_CLAIM, ""
                                                )
                                                iss = payload.get("iss", "")
                                                aud = payload.get("aud", "")
                                                exp = payload.get("exp", "")
                                                iat = payload.get("iat", "")
                                                # Try actual validation
                                                try:
                                                    validated = AccessToken(token)
                                                    signing_hash = hashlib.sha256(
                                                        str(api_settings.SIGNING_KEY).encode()
                                                    ).hexdigest()[:8]
                                                    details.append(
                                                        f"recv JWT validated OK type={validated.get('token_type')} user_id={str(validated.get('user_id'))[:8]} alg={api_settings.ALGORITHM} hash={signing_hash}"
                                                    )
                                                except Exception as ve:
                                                    signing_hash = hashlib.sha256(
                                                        str(api_settings.SIGNING_KEY).encode()
                                                    ).hexdigest()[:8]
                                                    details.append(
                                                        f"recv JWT validation FAILED type={token_type} user_id={str(user_id)[:8]} alg={api_settings.ALGORITHM} hash={signing_hash} err={str(ve)[:80]}"
                                                    )
                                                    # Also log payload fields for comparison
                                                    details.append(
                                                        f"recv payload type={token_type} iss={iss} aud={aud} exp={exp} iat={iat}"
                                                    )
                                            except Exception:
                                                pass
                                        # Check for quoted token
                                        if '"' in header or "'" in header:
                                            details.append(
                                                "Authorization header contains quotes — Flutter may be storing token with extra quotes"
                                            )
                                        # Check for Bearer duplication
                                        if header_stripped.lower().count("bearer") > 1:
                                            details.append(
                                                "Multiple Bearer prefixes (e.g. 'Bearer Bearer ...')"
                                            )
                                    except Exception:
                                        pass

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
                                        details.append(f"messages={str(msgs)}")
                                    # allauth / DRF error envelope
                                    err = data.get("error")
                                    if isinstance(err, dict):
                                        if err.get("message"):
                                            details.append(f"error.message={err['message']}")
                                        if err.get("details"):
                                            details.append(f"error.details={str(err['details'])}")
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
                                        snippet = response.content[:2000].decode(errors="ignore")
                                        if snippet:
                                            details.append(f"body={snippet}")
                                    except Exception:
                                        pass
                                if details:
                                    cause = " | ".join(details)
                        except Exception:
                            pass
                user_id = ""
                user_role = ""
                try:
                    if hasattr(request, "user") and getattr(
                        request.user, "is_authenticated", False
                    ):
                        user_id = str(
                            getattr(request.user, "id", "") or getattr(request.user, "email", "")
                        )
                        user_role = str(getattr(request.user, "role", "")).lower()
                except Exception:
                    pass
                if not user_role:
                    # Keep sequential flow, just mark role for vertical line + filters
                    user_role = "guest"
                append_log(
                    {
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
                    }
                )
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
