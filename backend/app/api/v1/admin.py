from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.deps import get_db, get_current_admin
from app.db import models
from app.schemas.user import UserRead
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserRead])
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    result = await db.execute(select(models.User))
    return result.scalars().all()


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    await db.flush()
    return {"id": user.id, "is_active": user.is_active}


@router.get("/stats")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    result = await db.execute(
        select(
            select(func.count(models.User.id)).correlate(None).scalar_subquery().label("total_users"),
            select(func.count(models.ModelConfig.id)).correlate(None).scalar_subquery().label("total_models"),
            select(func.count(models.Dataset.id)).correlate(None).scalar_subquery().label("total_datasets"),
            select(func.count(models.EvaluationTask.id)).correlate(None).scalar_subquery().label("total_evaluations"),
            select(func.count(models.EvaluationTask.id)).where(
                models.EvaluationTask.status == "completed"
            ).correlate(None).scalar_subquery().label("completed_evaluations"),
        )
    )
    row = result.one()

    return {
        "total_users": row.total_users,
        "total_models": row.total_models,
        "total_datasets": row.total_datasets,
        "total_evaluations": row.total_evaluations,
        "completed_evaluations": row.completed_evaluations,
    }
