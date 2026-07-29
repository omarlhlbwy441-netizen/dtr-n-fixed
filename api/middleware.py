"""
╔══════════════════════════════════════════════════════════════════╗
║  Rafeeq Kernel v2.3.0 — Middleware (Rate Limiting, Logging)      ║
║  الوسائط: تقييد المعدل + التسجيل + الأمان                        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import time
import json
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ─── Redis (optional) ─────────────────────────────────────────────
# Redis is used for access-log analytics and rate limiting.
# If REDIS_URL is not set or Redis is unreachable, the app continues
# without caching/rate-limiting — it never crashes on startup.
_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None
    try:
        import redis as redis_lib
        client = redis_lib.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception:
        return None


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/Response logging middleware"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()

        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        response = await call_next(request)
        duration = time.time() - start

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "method": method,
            "path": path,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "unknown"),
        }

        status_icon = "✅" if response.status_code < 400 else "❌"
        print(
            f"{status_icon} [{log_entry['timestamp']}] {method} {path} "
            f"→ {response.status_code} ({log_entry['duration_ms']}ms)"
        )

        # Store in Redis for analytics (optional — silently skipped if unavailable)
        try:
            rc = _get_redis()
            if rc:
                rc.lpush("rafeeq:access_logs", json.dumps(log_entry))
                rc.ltrim("rafeeq:access_logs", 0, 9999)   # keep last 10k
                rc.expire("rafeeq:access_logs", 86400)    # expire after 24h
        except Exception:
            pass

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware — requires Redis; skipped transparently when unavailable"""

    async def dispatch(self, request: Request, call_next):
        if os.getenv("RATE_LIMIT_ENABLED", "false").lower() != "true":
            return await call_next(request)

        # Skip health checks
        if request.url.path.startswith("/api/health"):
            return await call_next(request)

        rc = _get_redis()
        if rc is None:
            # Redis unavailable → allow all requests (fail-open)
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if path.startswith("/api/auth/"):
            key = f"rafeeq:ratelimit:auth:{client_ip}"
            limit = 10
            window = 60
        else:
            key = f"rafeeq:ratelimit:api:{client_ip}"
            limit = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
            window = int(os.getenv("RATE_LIMIT_WINDOW", 60))

        try:
            current = rc.get(key)
            if current and int(current) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "limit": limit,
                        "window_seconds": window,
                        "retry_after": rc.ttl(key),
                    },
                )
            pipe = rc.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            pipe.execute()
        except Exception:
            pass  # fail-open

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        if request.url.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )

        return response
