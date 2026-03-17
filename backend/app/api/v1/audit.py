from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.deps import get_db, get_current_admin
from app.db import models
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogRead])
async def list_audit_logs(
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    query = select(models.AuditLog).order_by(models.AuditLog.created_at.desc())

    if action:
        query = query.where(models.AuditLog.action == action)
    if resource_type:
        query = query.where(models.AuditLog.resource_type == resource_type)
    if user_id:
        query = query.where(models.AuditLog.user_id == user_id)
    if start_date:
        query = query.where(models.AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(models.AuditLog.created_at <= end_date)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/logs/count")
async def audit_log_count(
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    result = await db.execute(select(func.count(models.AuditLog.id)))
    return {"total": result.scalar()}
