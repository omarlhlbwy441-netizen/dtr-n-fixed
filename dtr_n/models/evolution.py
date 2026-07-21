"""
Evolution Log Model
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class EvolutionLog(BaseModel):
    id: str
    type: str
    feature: Optional[str] = None
    file: Optional[str] = None
    iq_level: float = 0.0
    timestamp: str
    details: Optional[Dict[str, Any]] = None
