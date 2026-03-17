from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_user
from app.db import models
from app.schemas.agent import (
    AgentChatRequest, AgentConversationRead, AgentConversationDetail,
    AgentToolDefinition,
)
from app.services.agent.agent_service import AgentService
from app.services.agent.tools import registry
from typing import List

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
async def agent_chat(
    req: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Load user's agent model config from DB
    from app.core.security import decrypt_api_key
    agent_config = None
    result = await db.execute(
        select(models.AgentModelConfig)
        .where(
            models.AgentModelConfig.user_id == current_user.id,
            models.AgentModelConfig.is_active == True,
        )
        .order_by(models.AgentModelConfig.updated_at.desc())
        .limit(1)
    )
    am = result.scalar_one_or_none()
    if am:
        agent_config = {
            "api_key": decrypt_api_key(am.api_key_encrypted) if am.api_key_encrypted else None,
            "base_url": am.base_url,
            "model_name": am.model_name,
            "max_tokens": am.max_tokens,
            "temperature": am.temperature,
            "params": am.params or {},
        }

    service = AgentService(db, current_user, agent_config=agent_config)
    return StreamingResponse(
        service.chat_stream(req.message, req.conversation_id, req.context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tools", response_model=List[AgentToolDefinition])
async def list_tools(
    current_user: models.User = Depends(get_current_user),
):
    return registry.list_tools()


@router.get("/conversations", response_model=List[AgentConversationRead])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.AgentConversation)
        .where(models.AgentConversation.user_id == current_user.id)
        .order_by(models.AgentConversation.updated_at.desc())
    )
    return result.scalars().all()


@router.get("/conversations/{conv_id}", response_model=AgentConversationDetail)
async def get_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.AgentConversation).where(
            models.AgentConversation.id == conv_id,
            models.AgentConversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Eagerly load messages
    msg_result = await db.execute(
        select(models.AgentMessage)
        .where(models.AgentMessage.conversation_id == conv.id)
        .order_by(models.AgentMessage.created_at)
    )
    messages = msg_result.scalars().all()

    return AgentConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages,
    )


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.AgentConversation).where(
            models.AgentConversation.id == conv_id,
            models.AgentConversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)


# ────────────── Agent Memory ──────────────

@router.get("/memories")
async def list_memories(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.AgentMemory)
        .where(models.AgentMemory.user_id == current_user.id)
        .order_by(models.AgentMemory.updated_at.desc())
    )
    memories = result.scalars().all()
    return [
        {
            "id": m.id,
            "memory_type": m.memory_type,
            "key": m.key,
            "value": m.value,
            "confidence": m.confidence,
            "access_count": m.access_count,
            "created_at": m.created_at.isoformat(),
        }
        for m in memories
    ]


@router.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.AgentMemory).where(
            models.AgentMemory.id == memory_id,
            models.AgentMemory.user_id == current_user.id,
        )
    )
    mem = result.scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    await db.delete(mem)


@router.delete("/memories", status_code=204)
async def clear_all_memories(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(models.AgentMemory).where(
            models.AgentMemory.user_id == current_user.id
        )
    )
