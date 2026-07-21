"""
Session Model
"""

from pydantic import BaseModel
from typing import Optional


class Session(BaseModel):
    token: str
    user_id: str
    email: str
    created_at: str
    last_active: str
    expires_at: Optional[str] = None
    is_valid: bool = True
