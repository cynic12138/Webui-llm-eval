from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class AgentChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    context: Optional[dict] = None  # {current_route, current_page_data}


class AgentToolDefinition(BaseModel):
    name: str
    description: str
    category: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False


class AgentMessageRead(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentConversationRead(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentConversationDetail(AgentConversationRead):
    messages: list[AgentMessageRead] = []
