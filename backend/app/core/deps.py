import hashlib
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import async_session_maker
from app.core.security import decode_access_token
from app.db import models

security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    result = await db.execute(
        select(models.User).where(models.User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def get_api_key_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[models.User]:
    """Authenticate via X-API-Key header. Returns user or None."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(
        select(models.APIKey).where(
            models.APIKey.key_hash == key_hash,
            models.APIKey.is_active == True,
        )
    )
    key_obj = result.scalar_one_or_none()
    if not key_obj:
        return None

    # Check expiry
    if key_obj.expires_at and key_obj.expires_at < datetime.now(timezone.utc):
        return None

    # Update last used
    key_obj.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    # Get user
    user_result = await db.execute(
        select(models.User).where(models.User.id == key_obj.user_id)
    )
    return user_result.scalar_one_or_none()
