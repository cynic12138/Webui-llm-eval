from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.prompt import (
    PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateRead,
    PromptExperimentCreate, PromptExperimentRead,
)
from typing import List
import httpx
from app.core.http import make_async_httpx_client
import time

router = APIRouter(prefix="/prompts", tags=["prompts"])


# ── Templates ──────────────────────────────────────────────

@router.get("/", response_model=List[PromptTemplateRead])
async def list_templates(
    limit: int = 100,
    offset: int = 0,
    prompt_type: str = None,
    domain: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = (
        select(models.PromptTemplate)
        .where(models.PromptTemplate.user_id == current_user.id)
        .order_by(models.PromptTemplate.created_at.desc())
    )
    if prompt_type:
        query = query.where(models.PromptTemplate.prompt_type == prompt_type)
    if domain:
        query = query.where(models.PromptTemplate.domain == domain)
    result = await db.execute(query.limit(limit).offset(offset))
    return result.scalars().all()


@router.post("/", response_model=PromptTemplateRead, status_code=201)
async def create_template(
    data: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    template = models.PromptTemplate(
        user_id=current_user.id,
        name=data.name,
        content=data.content,
        variables=data.variables or [],
        tags=data.tags or [],
        parent_id=data.parent_id,
        version=1,
        prompt_type=data.prompt_type or "generation",
        domain=data.domain,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


# ── Experiments (MUST be before /{template_id} to avoid route conflict) ──

@router.get("/experiments", response_model=List[PromptExperimentRead])
async def list_experiments(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.PromptExperiment)
        .where(models.PromptExperiment.user_id == current_user.id)
        .order_by(models.PromptExperiment.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.post("/experiments", response_model=PromptExperimentRead, status_code=201)
async def create_experiment(
    data: PromptExperimentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Validate template IDs
    for tid in data.template_ids:
        result = await db.execute(
            select(models.PromptTemplate).where(
                models.PromptTemplate.id == tid,
                models.PromptTemplate.user_id == current_user.id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Template {tid} not found")

    # Validate model IDs
    for mid in data.model_ids:
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == mid,
                models.ModelConfig.user_id == current_user.id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Model {mid} not found")

    experiment = models.PromptExperiment(
        user_id=current_user.id,
        name=data.name,
        template_ids=data.template_ids,
        model_ids=data.model_ids,
        test_inputs=data.test_inputs,
        status="pending",
    )
    db.add(experiment)
    await db.flush()
    await db.refresh(experiment)
    return experiment


@router.get("/experiments/{experiment_id}", response_model=PromptExperimentRead)
async def get_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.PromptExperiment).where(
            models.PromptExperiment.id == experiment_id,
            models.PromptExperiment.user_id == current_user.id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.post("/experiments/{experiment_id}/run", response_model=PromptExperimentRead)
async def run_experiment(
    experiment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from app.core.security import decrypt_api_key

    result = await db.execute(
        select(models.PromptExperiment).where(
            models.PromptExperiment.id == experiment_id,
            models.PromptExperiment.user_id == current_user.id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    experiment.status = "running"
    await db.flush()

    # Load templates
    templates = {}
    for tid in experiment.template_ids:
        t_result = await db.execute(
            select(models.PromptTemplate).where(models.PromptTemplate.id == tid)
        )
        t = t_result.scalar_one_or_none()
        if t:
            templates[tid] = t

    # Load models
    model_configs = {}
    for mid in experiment.model_ids:
        m_result = await db.execute(
            select(models.ModelConfig).where(models.ModelConfig.id == mid)
        )
        m = m_result.scalar_one_or_none()
        if m:
            model_configs[mid] = m

    results = {}
    test_inputs = experiment.test_inputs or [{}]

    for tid, template in templates.items():
        results[str(tid)] = {}
        for mid, model_cfg in model_configs.items():
            results[str(tid)][str(mid)] = []

            api_key = decrypt_api_key(model_cfg.api_key_encrypted) if model_cfg.api_key_encrypted else None
            if not api_key:
                for inp in test_inputs:
                    results[str(tid)][str(mid)].append({
                        "input": inp,
                        "output": None,
                        "error": "No API key configured",
                        "latency_ms": 0,
                    })
                continue

            base_url = model_cfg.base_url or "https://api.openai.com/v1"
            url = f"{base_url}/chat/completions"

            for inp in test_inputs:
                # Render template with variables
                rendered = template.content
                for var_name, var_val in inp.items():
                    rendered = rendered.replace(f"{{{{{var_name}}}}}", str(var_val))

                try:
                    start = time.time()
                    async with make_async_httpx_client(timeout=60.0) as client:
                        resp = await client.post(
                            url,
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model_cfg.model_name,
                                "messages": [{"role": "user", "content": rendered}],
                                "max_tokens": 512,
                            },
                        )
                    latency = round((time.time() - start) * 1000)

                    if resp.status_code == 200:
                        data = resp.json()
                        reply = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        results[str(tid)][str(mid)].append({
                            "input": inp,
                            "rendered_prompt": rendered,
                            "output": reply,
                            "latency_ms": latency,
                            "prompt_tokens": usage.get("prompt_tokens"),
                            "completion_tokens": usage.get("completion_tokens"),
                        })
                    else:
                        results[str(tid)][str(mid)].append({
                            "input": inp,
                            "rendered_prompt": rendered,
                            "output": None,
                            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                            "latency_ms": latency,
                        })
                except Exception as e:
                    results[str(tid)][str(mid)].append({
                        "input": inp,
                        "rendered_prompt": rendered,
                        "output": None,
                        "error": str(e),
                        "latency_ms": 0,
                    })

    experiment.results = results
    experiment.status = "completed"
    await db.flush()
    await db.refresh(experiment)
    return experiment


@router.get("/{template_id}", response_model=PromptTemplateRead)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.PromptTemplate).where(
            models.PromptTemplate.id == template_id,
            models.PromptTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return template


@router.put("/{template_id}", response_model=PromptTemplateRead)
async def update_template(
    template_id: int,
    data: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.PromptTemplate).where(
            models.PromptTemplate.id == template_id,
            models.PromptTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")

    # If content changed, create a new version
    if data.content is not None and data.content != template.content:
        new_template = models.PromptTemplate(
            user_id=current_user.id,
            name=data.name or template.name,
            content=data.content,
            variables=data.variables if data.variables is not None else template.variables,
            tags=data.tags if data.tags is not None else template.tags,
            is_active=data.is_active if data.is_active is not None else template.is_active,
            parent_id=template.id,
            version=template.version + 1,
            prompt_type=data.prompt_type if data.prompt_type is not None else template.prompt_type,
            domain=data.domain if data.domain is not None else template.domain,
        )
        db.add(new_template)
        await db.flush()
        await db.refresh(new_template)
        return new_template

    # Otherwise update in place
    if data.name is not None:
        template.name = data.name
    if data.variables is not None:
        template.variables = data.variables
    if data.tags is not None:
        template.tags = data.tags
    if data.is_active is not None:
        template.is_active = data.is_active
    if data.prompt_type is not None:
        template.prompt_type = data.prompt_type
    if data.domain is not None:
        template.domain = data.domain
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
        select(models.PromptTemplate).where(
            models.PromptTemplate.id == template_id,
            models.PromptTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    # Detach child versions that reference this template
    await db.execute(
        update(models.PromptTemplate)
        .where(models.PromptTemplate.parent_id == template_id)
        .values(parent_id=template.parent_id)  # re-point to grandparent or None
    )
    await db.delete(template)
    await db.flush()
