import json
import io
import zipfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.dataset import DatasetCreate, DatasetRead, DatasetUpdate
from app.services.storage import StorageService
from typing import List, Optional

router = APIRouter(prefix="/datasets", tags=["datasets"])

BENCHMARK_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "eval_engine" / "benchmark_data"


@router.get("/builtin-benchmarks")
async def list_builtin_benchmarks(
    current_user: models.User = Depends(get_current_user),
):
    """List benchmark datasets as built-in datasets for the datasets page."""
    from app.api.v1.benchmarks import AVAILABLE_BENCHMARKS, _check_data_available, _get_actual_sample_count

    result = []
    for b in AVAILABLE_BENCHMARKS:
        data_available = _check_data_available(b["id"])
        actual_count = _get_actual_sample_count(b["id"])
        result.append({
            "id": f"builtin_{b['id']}",
            "benchmark_id": b["id"],
            "name": b["name"],
            "description": b["description"],
            "category": "benchmark",
            "format": "jsonl",
            "size": actual_count if actual_count is not None else b["sample_size"],
            "metric": b["metric"],
            "categories": b["categories"],
            "data_available": data_available,
            "data_source": b.get("data_source", ""),
            "status": "ready" if data_available else "demo",
            "is_builtin": True,
        })
    return result


@router.get("/", response_model=List[DatasetRead])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Dataset).where(models.Dataset.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/", response_model=DatasetRead, status_code=201)
async def create_dataset(
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    format: str = Form("jsonl"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    content = await file.read()
    records = []

    if format == "jsonl":
        for line in content.decode("utf-8").strip().split("\n"):
            if line.strip():
                records.append(json.loads(line))
    elif format == "json":
        records = json.loads(content)
    elif format == "csv":
        import csv
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        records = list(reader)
    elif format == "txt":
        lines = content.decode("utf-8").strip().split("\n")
        records = [{"text": line.strip()} for line in lines if line.strip()]
    elif format == "zip":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for zname in zf.namelist():
                    if zname.startswith("__MACOSX") or zname.startswith("."):
                        continue
                    sub_content = zf.read(zname)
                    if not sub_content.strip():
                        continue
                    text = sub_content.decode("utf-8")
                    if zname.endswith(".jsonl"):
                        for line in text.strip().split("\n"):
                            if line.strip():
                                records.append(json.loads(line))
                    elif zname.endswith(".json"):
                        data = json.loads(text)
                        if isinstance(data, list):
                            records.extend(data)
                        else:
                            records.append(data)
                    elif zname.endswith(".csv"):
                        import csv
                        reader = csv.DictReader(io.StringIO(text))
                        records.extend(list(reader))
                    elif zname.endswith(".txt"):
                        lines = text.strip().split("\n")
                        records.extend([{"text": l.strip()} for l in lines if l.strip()])
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="无效的 ZIP 文件")

    # Upload to MinIO
    storage = StorageService()
    file_path = f"datasets/{current_user.id}/{name}_{file.filename}"
    await storage.upload_bytes(file_path, content, file.content_type or "application/octet-stream")

    # Detect schema
    schema_meta = {}
    if records:
        schema_meta = {"fields": list(records[0].keys()), "sample": records[0]}

    dataset = models.Dataset(
        user_id=current_user.id,
        name=name,
        description=description,
        category=category,
        format=format,
        size=len(records),
        file_path=file_path,
        schema_meta=schema_meta,
        status="ready",
    )
    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)
    return dataset


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Dataset).where(
            models.Dataset.id == dataset_id,
            models.Dataset.user_id == current_user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Dataset).where(
            models.Dataset.id == dataset_id,
            models.Dataset.user_id == current_user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check for associated evaluation tasks
    task_count = (await db.execute(
        select(sa_func.count(models.EvaluationTask.id)).where(
            models.EvaluationTask.dataset_id == dataset_id
        )
    )).scalar() or 0
    if task_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"无法删除：该数据集被 {task_count} 个评测任务引用。请先删除相关评测任务。"
        )

    await db.delete(dataset)


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Dataset).where(
            models.Dataset.id == dataset_id,
            models.Dataset.user_id == current_user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    storage = StorageService()
    content = await storage.download_bytes(dataset.file_path)
    records = []
    if dataset.format == "jsonl":
        for i, line in enumerate(content.decode("utf-8").strip().split("\n")):
            if i >= limit:
                break
            if line.strip():
                records.append(json.loads(line))
    return {"records": records, "total": dataset.size}
