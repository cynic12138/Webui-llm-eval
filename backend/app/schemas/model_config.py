from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ModelConfigCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    provider: str  # openai, anthropic, azure, vllm, sglang, dashscope, deepseek, zhipu, custom
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str
    params: Optional[dict] = None
    tags: Optional[list[str]] = None


class ModelConfigRead(BaseModel):
    id: int
    user_id: int
    name: str
    provider: str
    base_url: Optional[str]
    model_name: str
    params: Optional[dict]
    tags: Optional[list[str]] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ModelConfigUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    params: Optional[dict] = None
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None


class TestConnectionRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str


class TestConnectionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    success: bool
    latency_ms: Optional[float] = None
    output: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None
