from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.core.deps import get_db, get_current_user
from app.core.security import encrypt_api_key, decrypt_api_key
from app.db import models
from app.schemas.model_config import (
    ModelConfigCreate, ModelConfigRead, ModelConfigUpdate,
    TestConnectionRequest, TestConnectionResponse,
)
from typing import List
import time
import asyncio

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", response_model=List[ModelConfigRead])
async def list_models(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.ModelConfig).where(models.ModelConfig.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/", response_model=ModelConfigRead, status_code=201)
async def create_model(
    model_data: ModelConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    encrypted_key = None
    if model_data.api_key:
        encrypted_key = encrypt_api_key(model_data.api_key)

    model = models.ModelConfig(
        user_id=current_user.id,
        name=model_data.name,
        provider=model_data.provider,
        api_key_encrypted=encrypted_key,
        base_url=model_data.base_url,
        model_name=model_data.model_name,
        params=model_data.params or {},
        tags=model_data.tags or [],
    )
    db.add(model)
    await db.flush()

    # Create ELO score entry
    elo = models.ModelEloScore(
        model_config_id=model.id,
        model_name=model_data.name,
    )
    db.add(elo)
    await db.refresh(model)
    return model


@router.get("/{model_id}", response_model=ModelConfigRead)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == model_id,
            models.ModelConfig.user_id == current_user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/{model_id}", response_model=ModelConfigRead)
async def update_model(
    model_id: int,
    model_data: ModelConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == model_id,
            models.ModelConfig.user_id == current_user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if model_data.name is not None:
        model.name = model_data.name
    if model_data.provider is not None:
        model.provider = model_data.provider
    if model_data.api_key is not None:
        model.api_key_encrypted = encrypt_api_key(model_data.api_key)
    if model_data.base_url is not None:
        model.base_url = model_data.base_url
    if model_data.model_name is not None:
        model.model_name = model_data.model_name
    if model_data.params is not None:
        model.params = model_data.params
    if model_data.tags is not None:
        model.tags = model_data.tags
    if model_data.is_active is not None:
        model.is_active = model_data.is_active

    await db.flush()
    await db.refresh(model)
    return model


@router.delete("/{model_id}", status_code=204)
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == model_id,
            models.ModelConfig.user_id == current_user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Check for associated evaluation results and tasks
    result_count = (await db.execute(
        select(sa_func.count(models.EvaluationResult.id)).where(
            models.EvaluationResult.model_id == model_id
        )
    )).scalar() or 0
    task_count = (await db.execute(
        select(sa_func.count()).select_from(models.TaskModelAssociation).where(
            models.TaskModelAssociation.model_id == model_id
        )
    )).scalar() or 0

    if result_count > 0 or task_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"无法删除：该模型关联了 {task_count} 个评测任务和 {result_count} 条评测结果。请先删除相关评测任务。"
        )

    await db.delete(model)


def _test_connection_sync(provider: str, api_key: str, base_url: str, model_name: str) -> dict:
    """Synchronous test: send a tiny prompt to the model and measure latency."""
    test_prompt = "Hi, reply with just the word 'ok'."
    start = time.time()
    try:
        if provider == "anthropic":
            import anthropic
            from app.core.http import make_httpx_client
            _http_client = make_httpx_client(timeout=60.0)
            client = anthropic.Anthropic(api_key=api_key, http_client=_http_client)
            resp = client.messages.create(
                model=model_name,
                max_tokens=16,
                messages=[{"role": "user", "content": test_prompt}],
            )
            latency_ms = (time.time() - start) * 1000
            output = resp.content[0].text if resp.content else ""
            return {
                "success": True,
                "latency_ms": round(latency_ms, 1),
                "output": output[:200],
                "model": model_name,
            }
        else:
            # OpenAI-compatible (openai, azure, vllm, sglang, dashscope, deepseek, custom, etc.)
            import openai
            from app.core.http import make_httpx_client
            _http_client = make_httpx_client(timeout=60.0)
            client = openai.OpenAI(api_key=api_key or "EMPTY", base_url=base_url or None, http_client=_http_client)
            resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": test_prompt}],
                max_tokens=16,
                temperature=0,
            )
            latency_ms = (time.time() - start) * 1000
            output = resp.choices[0].message.content if resp.choices else ""
            return {
                "success": True,
                "latency_ms": round(latency_ms, 1),
                "output": (output or "")[:200],
                "model": resp.model or model_name,
            }
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        error_msg = str(e)
        # Extract a user-friendly message
        if "Connection refused" in error_msg or "Connection error" in error_msg:
            error_msg = f"无法连接到 {base_url}，请检查地址是否正确、服务是否启动"
        elif "authentication" in error_msg.lower() or "api key" in error_msg.lower() or "401" in error_msg:
            error_msg = "API Key 认证失败，请检查密钥是否正确"
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            error_msg = f"模型 {model_name} 未找到，请检查模型名称是否正确"
        elif "timeout" in error_msg.lower():
            error_msg = f"连接超时，请检查 {base_url} 是否可达"
        return {
            "success": False,
            "latency_ms": round(latency_ms, 1),
            "error": error_msg,
        }


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    req: TestConnectionRequest,
    current_user: models.User = Depends(get_current_user),
):
    """Test model connection without saving. Sends a tiny prompt and returns the result."""
    result = await asyncio.to_thread(
        _test_connection_sync,
        req.provider, req.api_key or "", req.base_url or "", req.model_name,
    )
    return result


@router.post("/{model_id}/test", response_model=TestConnectionResponse)
async def test_saved_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Test a saved model's connection."""
    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == model_id,
            models.ModelConfig.user_id == current_user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    test_result = await asyncio.to_thread(
        _test_connection_sync,
        model.provider, api_key, model.base_url or "", model.model_name,
    )
    return test_result
