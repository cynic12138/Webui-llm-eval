from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.db import models
from typing import List

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/elo")
async def get_elo_leaderboard(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.ModelEloScore)
        .join(models.ModelConfig, models.ModelEloScore.model_config_id == models.ModelConfig.id)
        .where(models.ModelConfig.user_id == current_user.id)
        .order_by(models.ModelEloScore.elo_score.desc())
    )
    scores = result.scalars().all()
    return [
        {
            "rank": i + 1,
            "model_id": s.model_config_id,
            "model_name": s.model_name,
            "elo_score": s.elo_score,
            "wins": s.wins,
            "losses": s.losses,
            "draws": s.draws,
            "total_matches": s.total_matches,
            "win_rate": s.wins / s.total_matches if s.total_matches > 0 else 0,
        }
        for i, s in enumerate(scores)
    ]


@router.get("/benchmarks")
async def get_benchmark_leaderboard(
    benchmark: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get benchmark scores across all completed evaluations."""
    # Only load the results_summary column, not the full ORM objects
    result = await db.execute(
        select(models.EvaluationTask.results_summary).where(
            models.EvaluationTask.user_id == current_user.id,
            models.EvaluationTask.status == "completed",
            models.EvaluationTask.results_summary.isnot(None),
        )
    )
    summaries = result.scalars().all()

    model_scores: dict[str, dict[str, list]] = {}
    for results_summary in summaries:
        for model_id, summary in results_summary.get("by_model", {}).items():
            if model_id not in model_scores:
                model_scores[model_id] = {}
            for key, val in summary.get("scores", {}).items():
                if benchmark and not key.startswith(benchmark):
                    continue
                if key not in model_scores[model_id]:
                    model_scores[model_id][key] = []
                model_scores[model_id][key].append(val)

    # Compute averages
    leaderboard = []
    for model_id, scores in model_scores.items():
        avg_scores = {k: sum(v) / len(v) for k, v in scores.items()}
        leaderboard.append({"model_id": int(model_id), "scores": avg_scores})

    return leaderboard
