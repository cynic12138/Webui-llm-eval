from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ComparisonRequest(BaseModel):
    task_ids: List[int]


class ComparisonResult(BaseModel):
    tasks: List[dict]  # [{id, name, model_ids, created_at}]
    by_model: Dict[str, dict]  # model_name -> {scores, avg_latency, sample_count}
    score_keys: List[str]  # all unique score keys


class DiffRequest(BaseModel):
    task_a: int
    task_b: int
    model_id: Optional[int] = None
    limit: int = 20


class DiffResult(BaseModel):
    samples: List[dict]  # [{index, input, output_a, output_b, scores_a, scores_b}]
    summary: dict  # {a_better_count, b_better_count, tie_count}
