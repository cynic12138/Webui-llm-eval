"""
Dedicated Judge Model configuration API.
Separate from general model management — these are high-capability models
used specifically as evaluators/judges (e.g., GPT-4o, Claude-3.5, Qwen-Max).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.deps import get_db, get_current_user
from app.core.security import encrypt_api_key, decrypt_api_key
from app.db import models
from typing import List, Optional
import asyncio

router = APIRouter(prefix="/judge-models", tags=["judge-models"])


class JudgeModelCreate(BaseModel):
    name: str
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str
    is_default: bool = False
    params: Optional[dict] = None


class JudgeModelRead(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    user_id: int
    name: str
    provider: str
    base_url: Optional[str]
    model_name: str
    params: Optional[dict]
    is_default: bool
    is_active: bool
    created_at: str


class JudgeModelUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    params: Optional[dict] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_judge_models(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.JudgeModelConfig)
        .where(models.JudgeModelConfig.user_id == current_user.id)
        .order_by(models.JudgeModelConfig.is_default.desc(), models.JudgeModelConfig.created_at.desc())
    )
    judge_models = result.scalars().all()
    return [
        {
            "id": jm.id,
            "user_id": jm.user_id,
            "name": jm.name,
            "provider": jm.provider,
            "base_url": jm.base_url,
            "model_name": jm.model_name,
            "params": jm.params or {},
            "is_default": jm.is_default,
            "is_active": jm.is_active,
            "created_at": jm.created_at.isoformat() if jm.created_at else "",
        }
        for jm in judge_models
    ]


@router.post("/", status_code=201)
async def create_judge_model(
    data: JudgeModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    encrypted_key = encrypt_api_key(data.api_key) if data.api_key else None

    # If setting as default, unset other defaults
    if data.is_default:
        existing = await db.execute(
            select(models.JudgeModelConfig).where(
                models.JudgeModelConfig.user_id == current_user.id,
                models.JudgeModelConfig.is_default == True,
            )
        )
        for jm in existing.scalars().all():
            jm.is_default = False

    jm = models.JudgeModelConfig(
        user_id=current_user.id,
        name=data.name,
        provider=data.provider,
        api_key_encrypted=encrypted_key,
        base_url=data.base_url,
        model_name=data.model_name,
        params=data.params or {},
        is_default=data.is_default,
    )
    db.add(jm)
    await db.flush()
    await db.refresh(jm)
    return {
        "id": jm.id,
        "user_id": jm.user_id,
        "name": jm.name,
        "provider": jm.provider,
        "base_url": jm.base_url,
        "model_name": jm.model_name,
        "params": jm.params or {},
        "is_default": jm.is_default,
        "is_active": jm.is_active,
        "created_at": jm.created_at.isoformat() if jm.created_at else "",
    }


@router.put("/{judge_model_id}")
async def update_judge_model(
    judge_model_id: int,
    data: JudgeModelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.JudgeModelConfig).where(
            models.JudgeModelConfig.id == judge_model_id,
            models.JudgeModelConfig.user_id == current_user.id,
        )
    )
    jm = result.scalar_one_or_none()
    if not jm:
        raise HTTPException(status_code=404, detail="Judge model not found")

    if data.name is not None:
        jm.name = data.name
    if data.provider is not None:
        jm.provider = data.provider
    if data.api_key is not None:
        jm.api_key_encrypted = encrypt_api_key(data.api_key)
    if data.base_url is not None:
        jm.base_url = data.base_url
    if data.model_name is not None:
        jm.model_name = data.model_name
    if data.params is not None:
        jm.params = data.params
    if data.is_active is not None:
        jm.is_active = data.is_active

    # Handle is_default: unset others if setting this one
    if data.is_default is not None:
        if data.is_default:
            existing = await db.execute(
                select(models.JudgeModelConfig).where(
                    models.JudgeModelConfig.user_id == current_user.id,
                    models.JudgeModelConfig.is_default == True,
                    models.JudgeModelConfig.id != judge_model_id,
                )
            )
            for other in existing.scalars().all():
                other.is_default = False
        jm.is_default = data.is_default

    await db.flush()
    await db.refresh(jm)
    return {
        "id": jm.id,
        "user_id": jm.user_id,
        "name": jm.name,
        "provider": jm.provider,
        "base_url": jm.base_url,
        "model_name": jm.model_name,
        "params": jm.params or {},
        "is_default": jm.is_default,
        "is_active": jm.is_active,
        "created_at": jm.created_at.isoformat() if jm.created_at else "",
    }


@router.delete("/{judge_model_id}", status_code=204)
async def delete_judge_model(
    judge_model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.JudgeModelConfig).where(
            models.JudgeModelConfig.id == judge_model_id,
            models.JudgeModelConfig.user_id == current_user.id,
        )
    )
    jm = result.scalar_one_or_none()
    if not jm:
        raise HTTPException(status_code=404, detail="Judge model not found")
    await db.delete(jm)


@router.post("/{judge_model_id}/test")
async def test_judge_model(
    judge_model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Test a saved judge model's connection."""
    result = await db.execute(
        select(models.JudgeModelConfig).where(
            models.JudgeModelConfig.id == judge_model_id,
            models.JudgeModelConfig.user_id == current_user.id,
        )
    )
    jm = result.scalar_one_or_none()
    if not jm:
        raise HTTPException(status_code=404, detail="Judge model not found")

    api_key = decrypt_api_key(jm.api_key_encrypted) if jm.api_key_encrypted else ""
    from app.api.v1.models import _test_connection_sync
    return await asyncio.to_thread(
        _test_connection_sync,
        jm.provider, api_key, jm.base_url, jm.model_name,
    )
