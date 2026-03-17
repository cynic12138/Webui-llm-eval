from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.comparison import ComparisonRequest, DiffRequest

router = APIRouter(prefix="/comparison", tags=["comparison"])


@router.post("/tasks")
async def compare_tasks(
    req: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Compare multiple evaluation tasks side-by-side."""
    tasks_data = []
    all_scores = {}  # model_name -> [{scores dict}, ...]

    for tid in req.task_ids:
        task_result = await db.execute(
            select(models.EvaluationTask).where(
                models.EvaluationTask.id == tid,
                models.EvaluationTask.user_id == current_user.id,
            )
        )
        task = task_result.scalar_one_or_none()
        if not task:
            continue
        tasks_data.append({
            "id": task.id, "name": task.name,
            "model_ids": task.model_ids,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
        })

        summary = task.results_summary or {}
        for mid, mdata in summary.get("by_model", {}).items():
            model_name = mdata.get("model_name", f"Model {mid}")
            if model_name not in all_scores:
                all_scores[model_name] = {
                    "scores_sum": {},
                    "count": 0,
                    "latency_sum": 0,
                    "sample_count": 0,
                }
            entry = all_scores[model_name]
            entry["count"] += 1
            entry["sample_count"] += mdata.get("sample_count", 0)
            entry["latency_sum"] += mdata.get("avg_latency_ms", 0)
            for sk, sv in mdata.get("scores", {}).items():
                entry["scores_sum"][sk] = entry["scores_sum"].get(sk, 0) + sv

    # Average
    by_model = {}
    score_keys = set()
    for model_name, entry in all_scores.items():
        n = entry["count"] or 1
        avg_scores = {k: round(v / n, 4) for k, v in entry["scores_sum"].items()}
        score_keys.update(avg_scores.keys())
        by_model[model_name] = {
            "scores": avg_scores,
            "avg_latency_ms": round(entry["latency_sum"] / n, 1),
            "sample_count": entry["sample_count"],
        }

    return {
        "tasks": tasks_data,
        "by_model": by_model,
        "score_keys": sorted(score_keys),
    }


@router.post("/diff")
async def diff_tasks(
    req: DiffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Side-by-side output diff between two tasks."""
    # Verify ownership
    for tid in [req.task_a, req.task_b]:
        result = await db.execute(
            select(models.EvaluationTask).where(
                models.EvaluationTask.id == tid,
                models.EvaluationTask.user_id == current_user.id,
            )
        )
        if not result.scalar_one_or_none():
            return {"error": f"Task {tid} not found"}

    # Fetch results from task A
    query_a = select(models.EvaluationResult).where(
        models.EvaluationResult.task_id == req.task_a
    ).order_by(models.EvaluationResult.sample_index).limit(req.limit)
    if req.model_id:
        query_a = query_a.where(models.EvaluationResult.model_id == req.model_id)
    results_a = (await db.execute(query_a)).scalars().all()

    # Fetch results from task B
    query_b = select(models.EvaluationResult).where(
        models.EvaluationResult.task_id == req.task_b
    ).order_by(models.EvaluationResult.sample_index).limit(req.limit)
    if req.model_id:
        query_b = query_b.where(models.EvaluationResult.model_id == req.model_id)
    results_b = (await db.execute(query_b)).scalars().all()

    # Build index maps
    map_a = {r.sample_index: r for r in results_a}
    map_b = {r.sample_index: r for r in results_b}
    all_indices = sorted(set(map_a.keys()) | set(map_b.keys()))

    samples = []
    a_better = b_better = ties = 0
    for idx in all_indices[:req.limit]:
        ra = map_a.get(idx)
        rb = map_b.get(idx)
        scores_a = ra.scores if ra else {}
        scores_b = rb.scores if rb else {}
        avg_a = sum(scores_a.values()) / len(scores_a) if scores_a else 0
        avg_b = sum(scores_b.values()) / len(scores_b) if scores_b else 0
        if avg_a > avg_b + 0.01:
            a_better += 1
        elif avg_b > avg_a + 0.01:
            b_better += 1
        else:
            ties += 1
        samples.append({
            "index": idx,
            "input": (ra.input_text if ra else rb.input_text if rb else "")[:300],
            "output_a": (ra.output_text if ra else "")[:300],
            "output_b": (rb.output_text if rb else "")[:300],
            "scores_a": scores_a,
            "scores_b": scores_b,
        })

    return {
        "samples": samples,
        "summary": {
            "a_better_count": a_better,
            "b_better_count": b_better,
            "tie_count": ties,
            "task_a": req.task_a,
            "task_b": req.task_b,
        },
    }
