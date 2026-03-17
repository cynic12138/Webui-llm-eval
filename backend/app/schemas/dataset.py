from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str  # qa, code, chat, rag, safety
    format: str = "jsonl"


class DatasetRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    category: str
    format: str
    size: int
    status: str
    schema_meta: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
