"""
Rafeeq Kernel v2.0.0 - Main Application
The most powerful digital ecosystem with the strongest kernel.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

# Import modules
from database import init_database, get_system_stats
from api.auth import router as auth_router

app = FastAPI(
    title="Rafeeq Kernel",
    description="Your intelligent AI companion",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    print("🚀 Rafeeq Kernel v2.0.0 starting...")
    try:
        init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database init warning: {e}")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth_router)

# Health check
@app.get("/health")
async def health_check():
    return get_system_stats()

# Root - serve index
@app.get("/")
async def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return JSONResponse({
        "name": "Rafeeq Kernel",
        "version": "2.0.0",
        "status": "active",
        "message": "من بعد فضل الله اشكر دولة مصر لانها اتاحت لي فرصة لكي اقوم بهذا العمل"
    })

# API status
@app.get("/api/status")
async def api_status():
    return get_system_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
