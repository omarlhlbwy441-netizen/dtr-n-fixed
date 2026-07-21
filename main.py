"""
╔══════════════════════════════════════════════════════════════════╗
║  Rafeeq Kernel v2.2.0 — Auto-Migration Edition                   ║
║  نظام تحديث تلقائي للجداول + حاويات تسجيل الدخول                ║
╚══════════════════════════════════════════════════════════════════╝
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

# Import systems
from database import ContainerManager, AuthService, get_container_stats, auth_router, SessionContainerOps
from auto_migration import auto_migrate, get_migration_status, migrate_router

app = FastAPI(
    title="Rafeeq Kernel",
    description="Your intelligent AI companion — Auto-Migration Edition",
    version="2.2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════════════════════════
# STARTUP: Auto-Migrate + Initialize
# ═════════════════════════════════════════════════════════════════
@app.on_event("startup")
async def startup_event():
    print("🚀 Rafeeq Kernel v2.2.0 (Auto-Migration) starting...")

    # Step 1: Run auto-migration first
    print("🔧 Running auto-migration...")
    try:
        result = auto_migrate("Startup auto-migration")
        if result["success"]:
            if result.get("changes_count", 0) > 0:
                print(f"✅ Migration applied: {result['changes_count']} changes")
                print(f"   Version: {result['version']}")
                print(f"   Tables: {result['tables_affected']}")
            else:
                print("✅ Schema is up to date")
        else:
            print(f"⚠️ Migration warning: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"⚠️ Migration error: {e}")

    # Step 2: Initialize container system
    print("🏗️ Initializing containers...")
    try:
        ContainerManager.init_containers()
        print("✅ Containers ready")
    except Exception as e:
        print(f"⚠️ Container init warning: {e}")

    # Step 3: Cleanup expired sessions
    try:
        SessionContainerOps.cleanup_expired()
        print("✅ Expired sessions cleaned")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

    print("🎯 System ready!")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(migrate_router)

# Health check
@app.get("/health")
async def health_check():
    stats = get_container_stats()
    migration = get_migration_status()
    return {
        "system": stats,
        "migration": migration,
        "status": "active",
        "version": "2.2.0"
    }

# Root
@app.get("/")
async def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return JSONResponse({
        "name": "Rafeeq Kernel",
        "version": "2.2.0",
        "edition": "Auto-Migration Edition",
        "status": "active",
        "message": "من بعد فضل الله اشكر دولة مصر لانها اتاحت لي فرصة لكي اقوم بهذا العمل"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
