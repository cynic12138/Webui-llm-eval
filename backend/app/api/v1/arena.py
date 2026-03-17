from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.arena import ArenaMatchCreate, ArenaVote, ArenaMatchRead
from typing import List
from app.core.http import make_async_httpx_client

router = APIRouter(prefix="/arena", tags=["arena"])


@router.post("/matches", response_model=ArenaMatchRead)
async def create_match(
    data: ArenaMatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a blind arena match: sends prompt to both models and returns outputs."""
    from app.core.security import decrypt_api_key
    import httpx
    import time
    import asyncio

    # Load both models
    async def get_model(mid):
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == mid,
                models.ModelConfig.user_id == current_user.id,
            )
        )
        m = result.scalar_one_or_none()
        if not m:
            raise HTTPException(status_code=404, detail=f"Model {mid} not found")
        return m

    model_a = await get_model(data.model_a_id)
    model_b = await get_model(data.model_b_id)

    async def call_model(model):
        api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else None
        base_url = model.base_url or "https://api.openai.com/v1"
        start = time.time()
        try:
            async with make_async_httpx_client(timeout=60.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model.model_name, "messages": [{"role": "user", "content": data.prompt}], "max_tokens": 1024},
                )
            latency = round((time.time() - start) * 1000, 1)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"], latency
            return f"Error: HTTP {resp.status_code}", latency
        except Exception as e:
            return f"Error: {str(e)}", round((time.time() - start) * 1000, 1)

    (out_a, lat_a), (out_b, lat_b) = await asyncio.gather(call_model(model_a), call_model(model_b))

    match = models.ArenaMatch(
        user_id=current_user.id,
        prompt=data.prompt,
        model_a_id=data.model_a_id,
        model_b_id=data.model_b_id,
        output_a=out_a,
        output_b=out_b,
        latency_a_ms=lat_a,
        latency_b_ms=lat_b,
    )
    db.add(match)
    await db.flush()
    await db.refresh(match)
    return match


@router.post("/matches/{match_id}/vote", response_model=ArenaMatchRead)
async def vote_match(
    match_id: int,
    vote: ArenaVote,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Vote on a match winner and update ELO scores."""
    result = await db.execute(
        select(models.ArenaMatch).where(
            models.ArenaMatch.id == match_id,
            models.ArenaMatch.user_id == current_user.id,
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.winner:
        raise HTTPException(status_code=400, detail="Already voted")

    match.winner = vote.winner
    await db.flush()

    # Update ELO scores
    elo_a_result = await db.execute(
        select(models.ModelEloScore).where(models.ModelEloScore.model_config_id == match.model_a_id)
    )
    elo_b_result = await db.execute(
        select(models.ModelEloScore).where(models.ModelEloScore.model_config_id == match.model_b_id)
    )
    elo_a = elo_a_result.scalar_one_or_none()
    elo_b = elo_b_result.scalar_one_or_none()

    if elo_a and elo_b:
        K = 32
        ea = 1.0 / (1 + 10 ** ((elo_b.elo_score - elo_a.elo_score) / 400))
        eb = 1.0 - ea
        if vote.winner == "a":
            sa, sb = 1.0, 0.0
            elo_a.wins += 1; elo_b.losses += 1
        elif vote.winner == "b":
            sa, sb = 0.0, 1.0
            elo_b.wins += 1; elo_a.losses += 1
        else:
            sa, sb = 0.5, 0.5
            elo_a.draws += 1; elo_b.draws += 1
        elo_a.elo_score += K * (sa - ea)
        elo_b.elo_score += K * (sb - eb)
        elo_a.total_matches += 1
        elo_b.total_matches += 1
        await db.flush()

    await db.refresh(match)
    return match


@router.get("/matches", response_model=List[ArenaMatchRead])
async def list_matches(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.ArenaMatch)
        .where(models.ArenaMatch.user_id == current_user.id)
        .order_by(models.ArenaMatch.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
