from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.evaluation import (
    EvaluationTaskCreate, EvaluationTaskRead, EvaluationResultRead
)
from app.services.evaluation import run_evaluation_task
from app.services.audit import log_action
from typing import List, Optional
import json
import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/", response_model=List[EvaluationTaskRead])
async def list_evaluations(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.EvaluationTask)
        .where(models.EvaluationTask.user_id == current_user.id)
        .order_by(models.EvaluationTask.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.post("/", response_model=EvaluationTaskRead, status_code=201)
async def create_evaluation(
    task_data: EvaluationTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Validate model IDs belong to user
    for model_id in task_data.model_ids:
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == model_id,
                models.ModelConfig.user_id == current_user.id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    task = models.EvaluationTask(
        user_id=current_user.id,
        name=task_data.name,
        description=task_data.description,
        model_ids=task_data.model_ids,
        dataset_id=task_data.dataset_id,
        evaluator_config=task_data.evaluator_config.model_dump(),
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Write to association table (dual-write with JSON model_ids for compatibility)
    for mid in task_data.model_ids:
        db.add(models.TaskModelAssociation(task_id=task.id, model_id=mid))

    await log_action(db, current_user.id, "evaluation.create", "evaluation_task", task.id, {"name": task.name})

    # Commit BEFORE dispatching Celery task to avoid race condition
    await db.commit()

    celery_result = run_evaluation_task.delay(task.id)
    task.celery_task_id = celery_result.id
    await db.commit()
    await db.refresh(task)

    return task


@router.get("/{task_id}", response_model=EvaluationTaskRead)
async def get_evaluation(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Evaluation task not found")
    return task


@router.get("/{task_id}/live-progress")
async def get_live_progress(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Lightweight progress endpoint that counts actual result rows in DB.
    This is the authoritative progress source — it doesn't depend on
    the Celery worker writing the progress field.
    """
    # Get task basic info
    task_result = await db.execute(
        select(
            models.EvaluationTask.status,
            models.EvaluationTask.total_samples,
            models.EvaluationTask.progress,
            models.EvaluationTask.processed_samples,
            models.EvaluationTask.error_message,
        ).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task_row = task_result.one_or_none()
    if not task_row:
        raise HTTPException(status_code=404, detail="Task not found")

    status, total_samples, db_progress, db_processed, error_message = task_row

    # Count actual result rows from evaluation_results table
    count_result = await db.execute(
        select(func.count(models.EvaluationResult.id)).where(
            models.EvaluationResult.task_id == task_id,
        )
    )
    actual_count = count_result.scalar() or 0

    # Per-model counts with model names
    per_model_result = await db.execute(
        select(
            models.EvaluationResult.model_id,
            func.count(models.EvaluationResult.id),
        ).where(
            models.EvaluationResult.task_id == task_id,
        ).group_by(models.EvaluationResult.model_id)
    )
    per_model_rows = per_model_result.all()

    # Fetch model names for all model IDs in one query
    model_ids = [row[0] for row in per_model_rows]
    model_names = {}
    if model_ids:
        name_result = await db.execute(
            select(models.ModelConfig.id, models.ModelConfig.name).where(
                models.ModelConfig.id.in_(model_ids)
            )
        )
        model_names = {row[0]: row[1] for row in name_result.all()}

    per_model = {
        str(row[0]): {"count": row[1], "name": model_names.get(row[0], f"模型 {row[0]}")}
        for row in per_model_rows
    }

    # Compute progress from actual count
    # Cap at 99% while still running (100% is reserved for completed status)
    progress = int(actual_count / total_samples * 100) if total_samples > 0 else db_progress
    if status == "running" and progress >= 100:
        progress = 99

    return {
        "status": status,
        "total_samples": total_samples,
        "processed_samples": actual_count,
        "progress": min(progress, 100),
        "per_model": per_model,
        "error_message": error_message,
    }


@router.delete("/{task_id}", status_code=204)
async def cancel_evaluation(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Evaluation task not found")

    if task.celery_task_id:
        from app.core.celery_app import celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True)

    task.status = "cancelled"
    await db.flush()


@router.delete("/{task_id}/delete", status_code=204)
async def delete_evaluation(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Permanently delete an evaluation task and all its results."""
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Evaluation task not found")

    # Cancel if still running
    if task.status in ("pending", "running") and task.celery_task_id:
        from app.core.celery_app import celery_app
        try:
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        except Exception:
            pass

    # Delete all associated records (order matters for FK constraints)
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(models.EvaluationResult).where(models.EvaluationResult.task_id == task_id)
    )
    try:
        await db.execute(
            sql_delete(models.GeneratedTrainingData).where(models.GeneratedTrainingData.task_id == task_id)
        )
    except Exception:
        pass
    await db.execute(
        sql_delete(models.Report).where(models.Report.task_id == task_id)
    )
    await db.execute(
        sql_delete(models.TaskModelAssociation).where(models.TaskModelAssociation.task_id == task_id)
    )

    await db.delete(task)
    await db.commit()
    await log_action(db, current_user.id, "delete_evaluation", "evaluation", task_id)


@router.post("/{task_id}/retry", response_model=EvaluationTaskRead)
async def retry_evaluation(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Evaluation task not found")
    if task.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Only failed/cancelled tasks can be retried (current: {task.status})")

    task.status = "pending"
    task.error_message = None
    task.retry_count = (task.retry_count or 0) + 1
    await db.flush()
    await log_action(db, current_user.id, "evaluation.retry", "evaluation_task", task.id, {"retry_count": task.retry_count})

    # Commit BEFORE dispatching Celery task to avoid race condition
    await db.commit()

    celery_result = run_evaluation_task.delay(task.id)
    task.celery_task_id = celery_result.id
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}/results", response_model=List[EvaluationResultRead])
async def get_evaluation_results(
    task_id: int,
    model_id: int = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify task ownership
    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    if not task_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    query = select(models.EvaluationResult).where(
        models.EvaluationResult.task_id == task_id
    )
    if model_id:
        query = query.where(models.EvaluationResult.model_id == model_id)
    query = query.order_by(
        models.EvaluationResult.sample_index,
        models.EvaluationResult.model_id,
    ).offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/trends/daily")
async def evaluation_trends(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get evaluation task counts grouped by day for trend charts."""
    from datetime import datetime, timezone, timedelta
    start = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(models.EvaluationTask.created_at).label("day"),
            models.EvaluationTask.status,
            func.count(models.EvaluationTask.id).label("count"),
        )
        .where(
            models.EvaluationTask.user_id == current_user.id,
            models.EvaluationTask.created_at >= start,
        )
        .group_by(func.date(models.EvaluationTask.created_at), models.EvaluationTask.status)
        .order_by(func.date(models.EvaluationTask.created_at))
    )
    rows = result.all()
    trends = {}
    for day, status, count in rows:
        d = str(day)
        if d not in trends:
            trends[d] = {"date": d, "total": 0, "completed": 0, "failed": 0, "running": 0}
        trends[d]["total"] += count
        if status in trends[d]:
            trends[d][status] += count
    return list(trends.values())


class BatchIdsRequest(BaseModel):
    ids: List[int]


@router.post("/batch/delete", status_code=200)
async def batch_delete_evaluations(
    req: BatchIdsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Batch delete evaluation tasks and their results."""
    from sqlalchemy import delete as sql_delete

    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id.in_(req.ids),
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    tasks = result.scalars().all()
    if not tasks:
        raise HTTPException(status_code=404, detail="No matching tasks found")

    deleted_ids = []
    for task in tasks:
        # Cancel if running
        if task.status in ("pending", "running") and task.celery_task_id:
            from app.core.celery_app import celery_app
            try:
                celery_app.control.revoke(task.celery_task_id, terminate=True)
            except Exception:
                pass
        # Delete all associated records (order matters for FK constraints)
        await db.execute(
            sql_delete(models.EvaluationResult).where(models.EvaluationResult.task_id == task.id)
        )
        try:
            await db.execute(
                sql_delete(models.GeneratedTrainingData).where(models.GeneratedTrainingData.task_id == task.id)
            )
        except Exception:
            pass
        await db.execute(
            sql_delete(models.Report).where(models.Report.task_id == task.id)
        )
        await db.execute(
            sql_delete(models.TaskModelAssociation).where(models.TaskModelAssociation.task_id == task.id)
        )
        await db.delete(task)
        deleted_ids.append(task.id)

    await db.commit()
    await log_action(db, current_user.id, "batch_delete_evaluation", "evaluation", None, {"ids": deleted_ids})
    return {"deleted": len(deleted_ids), "ids": deleted_ids}


@router.post("/batch/cancel", status_code=200)
async def batch_cancel_evaluations(
    req: BatchIdsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Batch cancel running/pending evaluation tasks."""
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id.in_(req.ids),
            models.EvaluationTask.user_id == current_user.id,
            models.EvaluationTask.status.in_(["pending", "running"]),
        )
    )
    tasks = result.scalars().all()
    cancelled_ids = []
    for task in tasks:
        if task.celery_task_id:
            from app.core.celery_app import celery_app
            try:
                celery_app.control.revoke(task.celery_task_id, terminate=True)
            except Exception:
                pass
        task.status = "cancelled"
        cancelled_ids.append(task.id)
    await db.flush()
    return {"cancelled": len(cancelled_ids), "ids": cancelled_ids}


@router.post("/batch/retry", status_code=200)
async def batch_retry_evaluations(
    req: BatchIdsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Batch retry failed/cancelled evaluation tasks."""
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id.in_(req.ids),
            models.EvaluationTask.user_id == current_user.id,
            models.EvaluationTask.status.in_(["failed", "cancelled"]),
        )
    )
    tasks = result.scalars().all()
    retried_ids = []
    for task in tasks:
        task.status = "pending"
        task.error_message = None
        task.retry_count = (task.retry_count or 0) + 1
        retried_ids.append(task.id)
    await db.commit()

    for task in tasks:
        celery_result = run_evaluation_task.delay(task.id)
        task.celery_task_id = celery_result.id
    await db.commit()
    return {"retried": len(retried_ids), "ids": retried_ids}


class DiagnoseRequest(BaseModel):
    threshold: float = 0.6


class GenerateDataRequest(BaseModel):
    pass


class ExportDatasetRequest(BaseModel):
    selected_ids: list[int]
    name: str


class UpdateGeneratedDataRequest(BaseModel):
    corrected_output: Optional[str] = None
    is_approved: Optional[bool] = None
    is_edited: Optional[bool] = None


@router.post("/{task_id}/diagnose")
async def diagnose_evaluation(
    task_id: int,
    req: DiagnoseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Diagnose low-scoring samples using the judge model."""
    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Task must be completed first")

    # Get low-scoring results
    results_q = await db.execute(
        select(models.EvaluationResult).where(
            models.EvaluationResult.task_id == task_id
        )
    )
    all_results = results_q.scalars().all()
    low_results = []
    for r in all_results:
        overall = r.scores.get("domain_overall", None)
        if overall is not None and overall < req.threshold:
            low_results.append(r)

    if not low_results:
        return {"message": "No low-scoring samples found", "count": 0}

    # Call judge model for detailed diagnosis
    config = task.evaluator_config
    judge_model_id = config.get("judge_model_id")
    if not judge_model_id:
        raise HTTPException(status_code=400, detail="No judge model configured")

    from app.core.security import decrypt_api_key
    # Try JudgeModelConfig first, then fallback to ModelConfig
    judge_mc = await db.execute(
        select(models.JudgeModelConfig).where(models.JudgeModelConfig.id == judge_model_id)
    )
    judge_model = judge_mc.scalar_one_or_none()
    if not judge_model:
        judge_mc = await db.execute(
            select(models.ModelConfig).where(models.ModelConfig.id == judge_model_id)
        )
        judge_model = judge_mc.scalar_one_or_none()
    if not judge_model:
        raise HTTPException(status_code=404, detail="Judge model not found")

    api_key = decrypt_api_key(judge_model.api_key_encrypted) if judge_model.api_key_encrypted else None
    from app.core.http import make_async_httpx_client
    base_url = judge_model.base_url or "https://api.openai.com/v1"
    url = f"{base_url}/chat/completions"

    diagnosed_count = 0
    for r in low_results:
        diagnosis_prompt = f"""你是一个专业的AI评测诊断专家。请详细分析以下模型回答的问题。

## 原始输入
{r.input_text or ''}

## 模型回答
{r.output_text or ''}

## 当前评分
{json.dumps(r.scores, ensure_ascii=False)}

请以JSON格式输出诊断结果：
{{
  "problems": [
    {{"segment": "有问题的原文片段", "issue": "问题描述", "suggestion": "改进建议"}}
  ],
  "reasoning": "整体诊断说明",
  "severity": "high/medium/low"
}}

请直接输出JSON。"""

        try:
            async with make_async_httpx_client(timeout=60.0) as client:
                resp = await client.post(url, headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }, json={
                    "model": judge_model.model_name,
                    "messages": [{"role": "user", "content": diagnosis_prompt}],
                    "max_tokens": 1024,
                })
            if resp.status_code == 200:
                import re
                raw = resp.json()["choices"][0]["message"]["content"]
                text = raw.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)
                try:
                    diagnosis = json.loads(text)
                except json.JSONDecodeError:
                    match = re.search(r"\{[\s\S]*\}", text)
                    diagnosis = json.loads(match.group()) if match else {"reasoning": text}

                # Update result metadata
                meta = dict(r.result_metadata) if r.result_metadata else {}
                meta["diagnosis"] = diagnosis
                meta["problems"] = diagnosis.get("problems", meta.get("problems", []))
                r.result_metadata = meta
                diagnosed_count += 1
            else:
                logger.warning(f"Diagnose API returned HTTP {resp.status_code} for result {r.id}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Failed to diagnose result {r.id}: {e}")

    await db.flush()
    return {"message": f"Diagnosed {diagnosed_count} samples", "count": diagnosed_count}


@router.post("/{task_id}/generate-data")
async def generate_training_data(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Generate corrected training data for low-scoring samples."""
    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == current_user.id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    config = task.evaluator_config
    judge_model_id = config.get("judge_model_id")
    if not judge_model_id:
        raise HTTPException(status_code=400, detail="No judge model configured")

    from app.core.security import decrypt_api_key
    # Try JudgeModelConfig first, then fallback to ModelConfig
    judge_mc = await db.execute(
        select(models.JudgeModelConfig).where(models.JudgeModelConfig.id == judge_model_id)
    )
    judge_model = judge_mc.scalar_one_or_none()
    if not judge_model:
        judge_mc = await db.execute(
            select(models.ModelConfig).where(models.ModelConfig.id == judge_model_id)
        )
        judge_model = judge_mc.scalar_one_or_none()
    if not judge_model:
        raise HTTPException(status_code=404, detail="Judge model not found")

    api_key = decrypt_api_key(judge_model.api_key_encrypted) if judge_model.api_key_encrypted else None
    from app.core.http import make_async_httpx_client
    base_url = judge_model.base_url or "https://api.openai.com/v1"
    url = f"{base_url}/chat/completions"

    # Get diagnosed low-scoring results
    results_q = await db.execute(
        select(models.EvaluationResult).where(
            models.EvaluationResult.task_id == task_id
        )
    )
    all_results = results_q.scalars().all()
    low_results = [r for r in all_results
                   if r.scores.get("domain_overall", 1.0) < 0.6
                   or (r.result_metadata and r.result_metadata.get("diagnosis"))]

    generated_count = 0
    for r in low_results:
        diagnosis = (r.result_metadata or {}).get("diagnosis", {})
        problems_desc = json.dumps(diagnosis.get("problems", []), ensure_ascii=False) if diagnosis else "未诊断"

        gen_prompt = f"""你是一个专业的AI训练数据优化专家。请基于以下诊断结果，生成一个高质量的修正版回答。

## 原始输入
{r.input_text or ''}

## 原始（有问题的）回答
{r.output_text or ''}

## 诊断发现的问题
{problems_desc}

## 诊断说明
{diagnosis.get('reasoning', '无')}

请直接生成修正后的高质量回答，不要包含解释说明，只输出修正后的回答内容。"""

        try:
            async with make_async_httpx_client(timeout=60.0) as client:
                resp = await client.post(url, headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }, json={
                    "model": judge_model.model_name,
                    "messages": [{"role": "user", "content": gen_prompt}],
                    "max_tokens": 2048,
                })
            if resp.status_code == 200:
                corrected = resp.json()["choices"][0]["message"]["content"]
                gtd = models.GeneratedTrainingData(
                    task_id=task_id,
                    result_id=r.id,
                    user_id=current_user.id,
                    original_input=r.input_text,
                    original_output=r.output_text,
                    corrected_output=corrected,
                    diagnosis=diagnosis,
                    improvement_notes=diagnosis.get("reasoning", ""),
                    is_approved=False,
                    is_edited=False,
                )
                db.add(gtd)
                generated_count += 1
            else:
                logger.warning(f"Generate data API returned HTTP {resp.status_code} for result {r.id}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Failed to generate training data for result {r.id}: {e}")

    await db.flush()
    return {"message": f"Generated {generated_count} training samples", "count": generated_count}


@router.get("/{task_id}/generated-data")
async def get_generated_data(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all generated training data for a task."""
    result = await db.execute(
        select(models.GeneratedTrainingData).where(
            models.GeneratedTrainingData.task_id == task_id,
            models.GeneratedTrainingData.user_id == current_user.id,
        ).order_by(models.GeneratedTrainingData.id)
    )
    return result.scalars().all()


@router.put("/{task_id}/generated-data/{data_id}")
async def update_generated_data(
    task_id: int,
    data_id: int,
    req: UpdateGeneratedDataRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a generated training data item (approve, edit)."""
    result = await db.execute(
        select(models.GeneratedTrainingData).where(
            models.GeneratedTrainingData.id == data_id,
            models.GeneratedTrainingData.task_id == task_id,
            models.GeneratedTrainingData.user_id == current_user.id,
        )
    )
    gtd = result.scalar_one_or_none()
    if not gtd:
        raise HTTPException(status_code=404, detail="Generated data not found")
    if req.corrected_output is not None:
        gtd.corrected_output = req.corrected_output
        gtd.is_edited = True
    if req.is_approved is not None:
        gtd.is_approved = req.is_approved
    if req.is_edited is not None:
        gtd.is_edited = req.is_edited
    await db.flush()
    await db.refresh(gtd)
    return gtd


@router.post("/{task_id}/export-dataset")
async def export_dataset(
    task_id: int,
    req: ExportDatasetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Export selected generated data as a new JSONL dataset."""
    result = await db.execute(
        select(models.GeneratedTrainingData).where(
            models.GeneratedTrainingData.id.in_(req.selected_ids),
            models.GeneratedTrainingData.task_id == task_id,
            models.GeneratedTrainingData.user_id == current_user.id,
        )
    )
    items = result.scalars().all()
    if not items:
        raise HTTPException(status_code=400, detail="No valid data selected")

    # Build JSONL content
    records = []
    for item in items:
        records.append({
            "input": item.original_input or "",
            "output": item.corrected_output or "",
            "original_output": item.original_output or "",
            "improvement_notes": item.improvement_notes or "",
        })

    jsonl_content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    content_bytes = jsonl_content.encode("utf-8")

    # Upload to MinIO
    from app.services.storage import StorageService
    storage = StorageService()
    file_path = f"datasets/{current_user.id}/generated_{task_id}_{req.name}.jsonl"
    await storage.upload_bytes(file_path, content_bytes, "application/jsonl")

    # Create dataset record
    dataset = models.Dataset(
        user_id=current_user.id,
        name=req.name,
        description=f"Auto-generated from evaluation task #{task_id} optimization",
        category="training",
        format="jsonl",
        size=len(records),
        file_path=file_path,
        schema_meta={"fields": ["input", "output", "original_output", "improvement_notes"], "sample": records[0] if records else {}},
        status="ready",
    )
    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)
    return dataset


@router.websocket("/{task_id}/progress")
async def evaluation_progress_ws(
    task_id: int,
    websocket: WebSocket,
):
    await websocket.accept()
    r = aioredis.from_url(settings.REDIS_URL)
    channel = f"eval_progress:{task_id}"
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode())
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await r.aclose()
