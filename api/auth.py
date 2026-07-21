"""
Rafeeq Kernel - Authentication API
Handles login, register, logout, and session management
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import bcrypt
import secrets

from database import UserModel, SessionModel, ActivityModel, get_system_stats

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic Models
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

# Helper: Get client info
def get_client_info(request: Request):
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")
    }

@router.post("/register", response_model=AuthResponse)
async def register(data: RegisterRequest, request: Request):
    """Register new user"""
    client = get_client_info(request)

    # Validate password
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check if email exists
    existing = UserModel.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = UserModel.create(
        email=data.email,
        password=data.password,
        username=data.username,
        full_name=data.full_name
    )

    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Create session
    session = SessionModel.create(
        user_id=user["id"],
        ip_address=client["ip"],
        user_agent=client["user_agent"]
    )

    # Log activity
    ActivityModel.log(
        user_id=user["id"],
        action="user_registered",
        description=f"New user registered: {data.email}",
        ip_address=client["ip"]
    )

    return AuthResponse(
        success=True,
        message="Registration successful",
        token=session["token"],
        user={
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "avatar": user["avatar"],
            "role": user["role"]
        }
    )

@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, request: Request):
    """Login user"""
    client = get_client_info(request)

    # Verify credentials
    user = UserModel.verify_password(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check status
    if user["status"] != "active":
        raise HTTPException(status_code=403, detail="Account is suspended")

    # Update last login
    UserModel.update_last_login(user["id"])

    # Create session
    session = SessionModel.create(
        user_id=user["id"],
        ip_address=client["ip"],
        user_agent=client["user_agent"]
    )

    # Log activity
    ActivityModel.log(
        user_id=user["id"],
        action="user_login",
        description=f"User logged in: {data.email}",
        ip_address=client["ip"]
    )

    return AuthResponse(
        success=True,
        message="Login successful",
        token=session["token"],
        user={
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "avatar": user["avatar"],
            "role": user["role"]
        }
    )

@router.post("/logout")
async def logout(request: Request):
    """Logout user"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        SessionModel.delete_by_token(token)
    return {"success": True, "message": "Logged out successfully"}

@router.get("/me")
async def get_current_user(request: Request):
    """Get current user info"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    session = SessionModel.get_by_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {
        "success": True,
        "user": {
            "id": session["user_id"],
            "email": session["email"],
            "username": session["username"],
            "full_name": session["full_name"],
            "avatar": session["avatar"],
            "role": session["role"]
        }
    }

@router.get("/stats")
async def auth_stats():
    """Get authentication statistics"""
    return get_system_stats()
