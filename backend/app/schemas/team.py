from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class OrgCreate(BaseModel):
    name: str
    description: Optional[str] = None


class OrgRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    owner_id: int
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class OrgMemberRead(BaseModel):
    id: int
    user_id: int
    username: str
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class OrgDetailRead(OrgRead):
    members: List[OrgMemberRead] = []


class AddMemberRequest(BaseModel):
    username: str
    role: Optional[str] = "member"


class ResourceShareCreate(BaseModel):
    resource_type: str  # evaluation, dataset, model
    resource_id: int


class ResourceShareRead(BaseModel):
    id: int
    org_id: int
    resource_type: str
    resource_id: int
    shared_by: int
    created_at: datetime

    model_config = {"from_attributes": True}
