from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.deps import get_db, get_current_user
from app.db import models
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/eval-templates", tags=["eval-templates"])


class EvalTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    model_ids: list[int] = []
    dataset_id: Optional[int] = None
    evaluator_config: dict = {}


class EvalTemplateRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    model_ids: list[int]
    dataset_id: Optional[int]
    evaluator_config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvalTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_ids: Optional[list[int]] = None
    dataset_id: Optional[int] = None
    evaluator_config: Optional[dict] = None


@router.get("/", response_model=List[EvalTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.EvaluationTemplate)
        .where(models.EvaluationTemplate.user_id == current_user.id)
        .order_by(models.EvaluationTemplate.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=EvalTemplateRead, status_code=201)
async def create_template(
    data: EvalTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    template = models.EvaluationTemplate(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        model_ids=data.model_ids,
        dataset_id=data.dataset_id,
        evaluator_config=data.evaluator_config,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.put("/{template_id}", response_model=EvalTemplateRead)
async def update_template(
    template_id: int,
    data: EvalTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.EvaluationTemplate).where(
            models.EvaluationTemplate.id == template_id,
            models.EvaluationTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if data.name is not None:
        template.name = data.name
    if data.description is not None:
        template.description = data.description
    if data.model_ids is not None:
        template.model_ids = data.model_ids
    if data.dataset_id is not None:
        template.dataset_id = data.dataset_id
    if data.evaluator_config is not None:
        template.evaluator_config = data.evaluator_config
    await db.flush()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.EvaluationTemplate).where(
            models.EvaluationTemplate.id == template_id,
            models.EvaluationTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(template)
