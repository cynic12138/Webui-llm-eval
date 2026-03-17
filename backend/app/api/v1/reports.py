from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.report import ReportCreate, ReportRead
from app.services.report import ReportService
from app.services.storage import StorageService
from typing import List
import io

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/", response_model=List[ReportRead])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Report)
        .where(models.Report.user_id == current_user.id)
        .order_by(models.Report.generated_at.desc())
    )
    return result.scalars().all()


@router.post("/generate", response_model=ReportRead, status_code=201)
async def generate_report(
    report_data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify task belongs to user
    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == report_data.task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Evaluation task not found")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Evaluation task not completed yet")

    service = ReportService(db)
    report = await service.generate(task, current_user, report_data.format)
    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Report).where(
            models.Report.id == report_id,
            models.Report.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    storage = StorageService()
    content = await storage.download_bytes(report.file_path)

    content_types = {"pdf": "application/pdf", "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "json": "application/json"}
    ct = content_types.get(report.format, "application/octet-stream")
    ext = {"pdf": "pdf", "excel": "xlsx", "json": "json"}.get(report.format, "bin")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}.{ext}"'},
    )
