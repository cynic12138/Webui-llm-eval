"""
Agent Model configuration API.
Configure the LLM backend used by the AI assistant.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.deps import get_db, get_current_user
from app.core.security import encrypt_api_key, decrypt_api_key
from app.db import models
from typing import Optional
import asyncio

router = APIRouter(prefix="/agent-model", tags=["agent-model"])


class AgentModelCreate(BaseModel):
    name: str
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    params: Optional[dict] = None


class AgentModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    params: Optional[dict] = None
    is_active: Optional[bool] = None


def _serialize(am: models.AgentModelConfig) -> dict:
    return {
        "id": am.id,
        "user_id": am.user_id,
        "name": am.name,
        "provider": am.provider,
        "base_url": am.base_url,
        "model_name": am.model_name,
        "max_tokens": am.max_tokens,
        "temperature": am.temperature,
        "params": am.params or {},
        "is_active": am.is_active,
        "created_at": am.created_at.isoformat() if am.created_at else "",
    }


@router.get("/")
async def get_agent_model(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the current user's agent model config (returns the active one, or null)."""
    result = await db.execute(
        select(models.AgentModelConfig)
        .where(
            models.AgentModelConfig.user_id == current_user.id,
            models.AgentModelConfig.is_active == True,
        )
        .order_by(models.AgentModelConfig.updated_at.desc())
        .limit(1)
    )
    am = result.scalar_one_or_none()
    if not am:
        return None
    return _serialize(am)


@router.put("/")
async def upsert_agent_model(
    data: AgentModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create or update the user's agent model config (single active config per user)."""
    encrypted_key = encrypt_api_key(data.api_key) if data.api_key else None

    # Find existing active config
    result = await db.execute(
        select(models.AgentModelConfig)
        .where(
            models.AgentModelConfig.user_id == current_user.id,
            models.AgentModelConfig.is_active == True,
        )
        .limit(1)
    )
    am = result.scalar_one_or_none()

    if am:
        am.name = data.name
        am.provider = data.provider
        if encrypted_key:
            am.api_key_encrypted = encrypted_key
        am.base_url = data.base_url
        am.model_name = data.model_name
        am.max_tokens = data.max_tokens
        am.temperature = data.temperature
        if data.params is not None:
            am.params = data.params
    else:
        am = models.AgentModelConfig(
            user_id=current_user.id,
            name=data.name,
            provider=data.provider,
            api_key_encrypted=encrypted_key,
            base_url=data.base_url,
            model_name=data.model_name,
            max_tokens=data.max_tokens,
            temperature=data.temperature,
            params=data.params or {},
        )
        db.add(am)

    await db.flush()
    await db.refresh(am)
    return _serialize(am)


@router.delete("/", status_code=204)
async def delete_agent_model(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Delete the user's agent model config (reverts to system default)."""
    result = await db.execute(
        select(models.AgentModelConfig)
        .where(
            models.AgentModelConfig.user_id == current_user.id,
            models.AgentModelConfig.is_active == True,
        )
    )
    for am in result.scalars().all():
        await db.delete(am)


@router.post("/test")
async def test_agent_model(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Test the active agent model's connection."""
    result = await db.execute(
        select(models.AgentModelConfig)
        .where(
            models.AgentModelConfig.user_id == current_user.id,
            models.AgentModelConfig.is_active == True,
        )
        .limit(1)
    )
    am = result.scalar_one_or_none()
    if not am:
        raise HTTPException(status_code=404, detail="未配置 AI 助手模型")

    api_key = decrypt_api_key(am.api_key_encrypted) if am.api_key_encrypted else ""
    from app.api.v1.models import _test_connection_sync
    return await asyncio.to_thread(
        _test_connection_sync,
        am.provider, api_key, am.base_url, am.model_name,
    )
