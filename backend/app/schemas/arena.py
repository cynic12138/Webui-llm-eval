from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ArenaMatchCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    prompt: str
    model_a_id: int
    model_b_id: int


class ArenaVote(BaseModel):
    winner: str  # "a", "b", "tie"


class ArenaMatchRead(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    user_id: int
    prompt: str
    model_a_id: int
    model_b_id: int
    output_a: Optional[str] = None
    output_b: Optional[str] = None
    winner: Optional[str] = None
    latency_a_ms: Optional[float] = None
    latency_b_ms: Optional[float] = None
    created_at: datetime
