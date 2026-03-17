import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.db import models
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class APIKeyCreate(BaseModel):
    name: str
    permissions: list[str] = ["read"]
    expires_in_days: Optional[int] = None


class APIKeyRead(BaseModel):
    id: int
    name: str
    key_prefix: str
    permissions: list[str]
    is_active: bool
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str


@router.post("/")
async def create_api_key(
    req: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Generate a secure random key
    raw_key = f"llmeval-{secrets.token_hex(24)}"
    key_prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    expires_at = None
    if req.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(days=req.expires_in_days)

    api_key = models.APIKey(
        user_id=current_user.id,
        name=req.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        permissions=req.permissions,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": raw_key,  # Only shown once!
        "key_prefix": key_prefix,
        "permissions": api_key.permissions,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "message": "API Key \u521b\u5efa\u6210\u529f\uff0c\u8bf7\u59a5\u5584\u4fdd\u7ba1\uff0c\u6b64\u5bc6\u94a5\u4ec5\u663e\u793a\u4e00\u6b21\uff01",
    }


@router.get("/")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.APIKey)
        .where(models.APIKey.user_id == current_user.id)
        .order_by(models.APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "permissions": k.permissions or [],
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.APIKey).where(
            models.APIKey.id == key_id,
            models.APIKey.user_id == current_user.id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    key.is_active = False
    await db.flush()
    return {"message": f"API Key '{key.name}' \u5df2\u64a4\u9500"}


@router.put("/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.APIKey).where(
            models.APIKey.id == key_id,
            models.APIKey.user_id == current_user.id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API Key not found")
    key.is_active = not key.is_active
    await db.flush()
    status = "\u5df2\u542f\u7528" if key.is_active else "\u5df2\u7981\u7528"
    return {"message": f"API Key '{key.name}' {status}", "is_active": key.is_active}
