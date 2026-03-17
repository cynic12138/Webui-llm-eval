from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    task_id: int
    format: str = "pdf"  # pdf, excel, json


class ReportRead(BaseModel):
    id: int
    task_id: int
    user_id: int
    format: str
    file_path: Optional[str]
    file_size: Optional[int]
    generated_at: datetime

    model_config = {"from_attributes": True}
