"""
╔══════════════════════════════════════════════════════════════════╗
║  Rafeeq Kernel v2.3.0 — Middleware (Rate Limiting, Logging)      ║
║  الوسائط: تقييد المعدل + التسجيل + الأمان                        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import time
import redis
import json
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/Response logging middleware"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()

        # Log request
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        response = await call_next(request)
        duration = time.time() - start

        # Log response
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "method": method,
            "path": path,
            "status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "unknown")
        }

        # Print to console (also logged by Docker)
        status_icon = "✅" if response.status_code < 400 else "❌"
        print(f"{status_icon} [{log_entry['timestamp']}] {method} {path} → {response.status_code} ({log_entry['duration_ms']}ms)")

        # Store in Redis for analytics (expire after 24h)
        try:
            redis_client.lpush("rafeeq:access_logs", json.dumps(log_entry))
            redis_client.ltrim("rafeeq:access_logs", 0, 9999)  # Keep last 10k
            redis_client.expire("rafeeq:access_logs", 86400)
        except:
            pass

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis"""

    async def dispatch(self, request: Request, call_next):
        if os.getenv("RATE_LIMIT_ENABLED", "false").lower() != "true":
            return await call_next(request)

        # Skip health checks
        if request.url.path.startswith("/api/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Auth endpoints: stricter limit
        if path.startswith("/api/auth/"):
            key = f"rafeeq:ratelimit:auth:{client_ip}"
            limit = 10
            window = 60
        # API endpoints: standard limit
        else:
            key = f"rafeeq:ratelimit:api:{client_ip}"
            limit = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
            window = int(os.getenv("RATE_LIMIT_WINDOW", 60))

        try:
            current = redis_client.get(key)
            if current and int(current) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "limit": limit,
                        "window_seconds": window,
                        "retry_after": redis_client.ttl(key)
                    }
                )

            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            pipe.execute()
        except:
            # If Redis fails, allow request (fail-open)
            pass

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

        # CORS is handled by CORSMiddleware, but add strict CSP
        if request.url.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        return response
