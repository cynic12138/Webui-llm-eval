"""Notification service for sending in-app notifications."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Notification


async def send_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    message: str = "",
    data: dict = None,
):
    """Create an in-app notification."""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )
    db.add(notification)
    await db.flush()
    return notification
