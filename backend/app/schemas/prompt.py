from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class PromptTemplateCreate(BaseModel):
    name: str
    content: str
    variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []
    parent_id: Optional[int] = None
    prompt_type: str = "generation"  # generation | evaluation
    domain: Optional[str] = None  # medical, finance, industrial, legal, education, general


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    prompt_type: Optional[str] = None
    domain: Optional[str] = None


class PromptTemplateRead(BaseModel):
    id: int
    user_id: int
    name: str
    content: str
    variables: Optional[List[str]] = []
    version: int
    parent_id: Optional[int] = None
    tags: Optional[List[str]] = []
    is_active: bool
    prompt_type: str = "generation"
    domain: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptExperimentCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    template_ids: List[int]
    model_ids: List[int]
    test_inputs: List[dict] = []


class PromptExperimentRead(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    user_id: int
    name: str
    template_ids: List[int]
    model_ids: List[int]
    test_inputs: List[dict]
    results: Optional[dict] = None
    status: str
    created_at: datetime
