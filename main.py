"""Rafeeq Kernel v2.2.1 — Fixed Unified Auth & Router"""
from fastapi import FastAPI, Request, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import os

from database import (
    ContainerManager, AuthService, get_system_stats,
    auto_migrate, get_migration_status, SessionContainerOps, UserContainerOps
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
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    print("Starting Rafeeq Kernel v2.2.1...")
    try:
        result = auto_migrate("Startup migration")
        print(f"Migration result: {result.get('message')}")
    except Exception as e:
        print(f"Migration error: {e}")
    try:
        # Seed default admin / user if empty
        if UserContainerOps.count() == 0:
            UserContainerOps.create(
                email="omarlhlbwy441@gmail.com",
                password="password",
                username="omarlhlbwy441",
                full_name="Omar Elhelbawy",
                role="admin"
            )
            print("Default user omarlhlbwy441@gmail.com created!")
    except Exception as e:
        print(f"User seed error: {e}")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: Optional[str] = None
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None
    error: Optional[str] = None

def get_client_info(request: Request):
    return {
        "ip": request.client.host if request.client else "127.0.0.1",
        "user_agent": request.headers.get("user-agent", ""),
        "location": request.headers.get("x-forwarded-for", "")
    }

# Create router for /auth and /api/auth
auth_router = APIRouter()

@auth_router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, request: Request):
    client = get_client_info(request)
    if len(data.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    result = AuthService.register(
        email=data.email, password=data.password,
        username=data.username or data.email.split('@')[0],
        full_name=data.full_name or data.email.split('@')[0],
        ip=client["ip"], user_agent=client["user_agent"]
    )
    if not result.get("success"):
        return AuthResponse(success=False, message=result.get("error", "Registration failed"), error=result.get("error"))
    return AuthResponse(success=True, message="Registration successful", token=result["token"], user=result["user"])

@auth_router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, request: Request):
    client = get_client_info(request)
    result = AuthService.login(
        email=data.email, password=data.password,
        ip=client["ip"], user_agent=client["user_agent"],
        location=client["location"]
    )
    # If user doesn't exist, auto-register on first login!
    if not result.get("success") and "Invalid email or password" in result.get("error", ""):
        reg_res = AuthService.register(
            email=data.email, password=data.password,
            username=data.email.split('@')[0],
            full_name=data.email.split('@')[0],
            ip=client["ip"], user_agent=client["user_agent"]
        )
        if reg_res.get("success"):
            return AuthResponse(success=True, message="Login successful", token=reg_res["token"], user=reg_res["user"])
        
    if not result.get("success"):
        return AuthResponse(success=False, message=result.get("error", "Invalid credentials"), error=result.get("error", "Invalid credentials"))
    return AuthResponse(success=True, message="Login successful", token=result["token"], user=result["user"])

@auth_router.post("/logout")
async def logout(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    client = get_client_info(request)
    AuthService.logout(token, ip=client["ip"])
    return {"success": True, "message": "Logged out"}

@auth_router.get("/me")
async def get_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    session = AuthService.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    return {"success": True, "user": {"id": session["user_id"], "email": session["email"], "username": session["username"], "full_name": session["full_name"], "role": session["role"]}}

# Include auth router under /auth AND /api/auth
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

# Migration routes
@app.get("/migrate/status")
@app.get("/api/migrate/status")
async def migration_status():
    return get_migration_status()

@app.post("/migrate/run")
@app.post("/api/migrate/run")
async def run_migration(description: str = ""):
    result = auto_migrate(description)
    return result

@app.get("/migrate/history")
@app.get("/api/migrate/history")
async def migration_history(limit: int = 50):
    from database import MigrationEngine
    engine = MigrationEngine()
    return {"migrations": engine.get_migration_history(limit)}

# Health and Root
@app.get("/health")
@app.get("/api/health")
async def health_check():
    stats = get_system_stats()
    migration = get_migration_status()
    return {"system": stats, "migration": migration, "status": "active", "version": "2.2.1"}

@app.get("/app.html")
@app.get("/login.html")
@app.get("/dashboard.html")
@app.get("/session-dashboard.html")
@app.get("/app")
@app.get("/login")
async def serve_app():
    if os.path.exists("app.html"):
        return FileResponse("app.html")
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return JSONResponse({"status": "ok"})

@app.get("/")
async def root():
    if os.path.exists("app.html"):
        return FileResponse("app.html")
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
