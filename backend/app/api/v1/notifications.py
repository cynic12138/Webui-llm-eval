from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.core.deps import get_db, get_current_user
from app.db import models

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications(
    is_read: bool = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = (
        select(models.Notification)
        .where(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if is_read is not None:
        query = query.where(models.Notification.is_read == is_read)
    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        {
            "id": n.id, "type": n.type, "title": n.title,
            "message": n.message, "data": n.data,
            "is_read": n.is_read, "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(func.count(models.Notification.id)).where(
            models.Notification.user_id == current_user.id,
            models.Notification.is_read == False,
        )
    )
    return {"count": result.scalar() or 0}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Notification).where(
            models.Notification.id == notification_id,
            models.Notification.user_id == current_user.id,
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        return {"error": "Not found"}
    n.is_read = True
    await db.flush()
    return {"ok": True}


@router.put("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    await db.execute(
        update(models.Notification)
        .where(
            models.Notification.user_id == current_user.id,
            models.Notification.is_read == False,
        )
        .values(is_read=True)
    )
    await db.flush()
    return {"ok": True}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Notification).where(
            models.Notification.id == notification_id,
            models.Notification.user_id == current_user.id,
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        return {"error": "Not found"}
    await db.delete(n)
    await db.flush()
    return {"ok": True}
