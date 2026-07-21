"""
╔══════════════════════════════════════════════════════════════════╗
║  Rafeeq Kernel v2.1.0 — Container Edition                       ║
║  نظام الحاويات المخصص لبيانات تسجيل الدخول                      ║
╚══════════════════════════════════════════════════════════════════╝
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

# Import Container System
from database import (
    ContainerManager, AuthService, get_container_stats,
    auth_router, SessionContainerOps
)

app = FastAPI(
    title="Rafeeq Kernel",
    description="Your intelligent AI companion — Container Edition",
    version="2.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize containers on startup
@app.on_event("startup")
async def startup_event():
    print("🚀 Rafeeq Kernel v2.1.0 (Container Edition) starting...")
    try:
        ContainerManager.init_containers()
        print("✅ All containers initialized")
        # Cleanup expired sessions
        SessionContainerOps.cleanup_expired()
        print("✅ Expired sessions cleaned")
    except Exception as e:
        print(f"⚠️ Container init warning: {e}")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include auth router (container-based)
app.include_router(auth_router)

# Health check — shows container stats
@app.get("/health")
async def health_check():
    return get_container_stats()

# Root
@app.get("/")
async def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return JSONResponse({
        "name": "Rafeeq Kernel",
        "version": "2.1.0",
        "edition": "Container Edition",
        "status": "active",
        "message": "من بعد فضل الله اشكر دولة مصر لانها اتاحت لي فرصة لكي اقوم بهذا العمل"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
