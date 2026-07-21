"""
Rafeeq Kernel v2.2.1 — Fixed & Working
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

# Import everything from unified database module
from database import (
    ContainerManager, AuthService, get_system_stats,
    auto_migrate, get_migration_status, SessionContainerOps
)

app = FastAPI(
    title="Rafeeq Kernel",
    description="Your intelligent AI companion",
    version="2.2.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Starting Rafeeq Kernel v2.2.1...")
    try:
        result = auto_migrate("Startup migration")
        if result["success"]:
            print(f"Migration OK: {result.get('changes_count', 0)} changes")
        else:
            print(f"Migration warning: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"Migration error: {e}")

    try:
        SessionContainerOps.cleanup_expired()
    except Exception as e:
        print(f"Cleanup error: {e}")

    print("System ready!")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ═════════════════════════════════════════════════════════════════
# AUTH ROUTES (inline to avoid import issues)
# ═════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None

def get_client_info(request: Request):
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", ""),
        "location": request.headers.get("x-forwarded-for", "")
    }

@app.post("/auth/register", response_model=AuthResponse)
async def register(data: RegisterRequest, request: Request):
    client = get_client_info(request)
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    result = AuthService.register(
        email=data.email, password=data.password,
        username=data.username, full_name=data.full_name,
        ip=client["ip"], user_agent=client["user_agent"]
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return AuthResponse(success=True, message="Registration successful", token=result["token"], user=result["user"])

@app.post("/auth/login", response_model=AuthResponse)
async def login(data: LoginRequest, request: Request):
    client = get_client_info(request)
    result = AuthService.login(
        email=data.email, password=data.password,
        ip=client["ip"], user_agent=client["user_agent"],
        location=client["location"]
    )
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return AuthResponse(success=True, message="Login successful", token=result["token"], user=result["user"])

@app.post("/auth/logout")
async def logout(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    client = get_client_info(request)
    AuthService.logout(token, ip=client["ip"])
    return {"success": True, "message": "Logged out"}

@app.get("/auth/me")
async def get_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    session = AuthService.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    return {"success": True, "user": {"id": session["user_id"], "email": session["email"], "username": session["username"], "full_name": session["full_name"], "role": session["role"]}}

# ═════════════════════════════════════════════════════════════════
# MIGRATION ROUTES
# ═════════════════════════════════════════════════════════════════

@app.get("/migrate/status")
async def migration_status():
    return get_migration_status()

@app.post("/migrate/run")
async def run_migration(description: str = ""):
    result = auto_migrate(description)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    return result

@app.get("/migrate/history")
async def migration_history(limit: int = 50):
    from database import MigrationEngine
    engine = MigrationEngine()
    return {"migrations": engine.get_migration_history(limit)}

# ═════════════════════════════════════════════════════════════════
# HEALTH & ROOT
# ═════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    stats = get_system_stats()
    migration = get_migration_status()
    return {"system": stats, "migration": migration, "status": "active", "version": "2.2.1"}

@app.get("/")
async def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return JSONResponse({
        "name": "Rafeeq Kernel",
        "version": "2.2.1",
        "status": "active",
        "message": "من بعد فضل الله اشكر دولة مصر لانها اتاحت لي فرصة لكي اقوم بهذا العمل"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
