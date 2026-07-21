"""
User Model
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: str
    email: EmailStr
    password_hash: str
    created_at: str = ""
    last_login: Optional[str] = None
    is_active: bool = True
    role: str = "user"

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str
    is_active: bool
