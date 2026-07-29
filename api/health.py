"""
╔══════════════════════════════════════════════════════════════════╗
║  Rafeeq Kernel v2.3.0 — Health Check Endpoints                   ║
║  نقاط فحص صحة النظام                                             ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import time
import psycopg2
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    Gauge,
)

router = APIRouter(prefix="/api/health", tags=["Health"])

# ─── Prometheus metrics ───────────────────────────────────────────
REQUEST_COUNT = Counter(
    "rafeeq_requests_total", "Total requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram("rafeeq_request_duration_seconds", "Request duration")
ACTIVE_SESSIONS = Gauge("rafeeq_active_sessions", "Number of active sessions")
DB_CONNECTIONS = Gauge("rafeeq_db_connections", "Database connections")

# ─── Redis (optional, lazy) ───────────────────────────────────────
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


start_time = time.time()


@router.get("")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "rafeeq-kernel",
        "version": "2.3.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "uptime_seconds": int(time.time() - start_time),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@router.get("/db")
async def db_health():
    """Database health check"""
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {
            "status": "healthy",
            "database": "postgresql",
            "users_count": user_count,
            "response_ms": 0,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")


@router.get("/redis")
async def redis_health():
    """Redis health check — returns degraded (not error) when Redis is not configured"""
    rc = _get_redis()
    if rc is None:
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "reason": "Redis not configured (REDIS_URL not set)",
            },
        )
    try:
        rc.ping()
        info = rc.info()
        return {
            "status": "healthy",
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unhealthy: {str(e)}")


@router.get("/github")
async def github_health():
    """GitHub API health check"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.github.com")
            return {
                "status": "healthy" if r.status_code == 200 else "degraded",
                "github_api_status": r.status_code,
                "rate_limit_remaining": r.headers.get("x-ratelimit-remaining", "unknown"),
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"GitHub API unreachable: {str(e)}")


@router.get("/system")
async def system_health():
    """System resources health check"""
    import psutil
    try:
        return {
            "status": "healthy",
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 2),
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total_gb": round(psutil.disk_usage("/").total / (1024 ** 3), 2),
                "used_gb": round(psutil.disk_usage("/").used / (1024 ** 3), 2),
                "percent": psutil.disk_usage("/").percent,
            },
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe — only DB is required.
    Redis is optional; its absence degrades but does not block readiness.
    """
    checks = {}
    healthy = True

    # Required: Database
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
        conn.close()
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"not_ready: {str(e)}"
        healthy = False

    # Optional: Redis
    try:
        rc = _get_redis()
        if rc:
            rc.ping()
            checks["redis"] = "ready"
        else:
            checks["redis"] = "degraded (not configured)"
    except Exception as e:
        checks["redis"] = f"degraded: {str(e)}"
        # Redis failure does NOT mark the service as not ready

    if healthy:
        return {"status": "ready", "checks": checks}
    raise HTTPException(
        status_code=503, detail={"status": "not_ready", "checks": checks}
    )


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive", "uptime_seconds": int(time.time() - start_time)}
