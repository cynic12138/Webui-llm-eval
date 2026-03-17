from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class EvaluatorConfig(BaseModel):
    # LLM-as-Judge
    llm_judge: bool = False
    judge_model_id: Optional[int] = None
    judge_dimensions: list[str] = ["accuracy", "fluency", "relevance"]

    # Standard Benchmarks
    benchmarks: list[str] = []  # mmlu_pro, gsm8k, humaneval, ceval

    # Hallucination
    hallucination: bool = False
    hallucination_n_samples: int = 5

    # Code Execution
    code_execution: bool = False

    # Robustness
    robustness: bool = False
    robustness_perturbations: list[str] = ["synonym", "typo", "shuffle"]

    # Consistency
    consistency: bool = False
    consistency_n_runs: int = 3

    # Safety
    safety: bool = False

    # RAG evaluation
    rag_eval: bool = False

    # Performance metrics
    performance: bool = True

    # Multi-turn
    multiturn: bool = False

    # Sampling
    max_samples: Optional[int] = None  # None = use all

    # Domain evaluation
    domain_eval: bool = False
    domain: Optional[str] = None
    generation_prompt_ids: list[int] = []
    evaluation_prompt_ids: list[int] = []
    eval_mode: str = "evaluate"  # "evaluate" | "evaluate_optimize"

    # New evaluation dimensions
    instruction_following: bool = False
    cot_reasoning: bool = False
    long_context: bool = False
    long_context_length: int = 8000
    structured_output: bool = False
    output_schema: Optional[dict] = None
    multilingual: bool = False
    multilingual_languages: list[str] = ["en", "zh"]
    tool_calling: bool = False
    multimodal: bool = False
    cost_analysis: bool = False

    # Thinking mode (for models that support it, e.g. Qwen3, DeepSeek-R1)
    enable_thinking: bool = False

    # Objective evaluation metrics
    objective_metrics: bool = False
    selected_metrics: list[str] = []


class EvaluationTaskCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    description: Optional[str] = None
    model_ids: list[int]
    dataset_id: Optional[int] = None
    evaluator_config: EvaluatorConfig = EvaluatorConfig()


class EvaluationTaskRead(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    user_id: int
    name: str
    description: Optional[str]
    status: str
    model_ids: list
    dataset_id: Optional[int]
    evaluator_config: dict
    results_summary: Optional[dict]
    progress: int
    total_samples: int
    processed_samples: int
    error_message: Optional[str]
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class EvaluationTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class EvaluationResultRead(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    task_id: int
    sample_index: int
    model_id: int
    input_text: Optional[str]
    output_text: Optional[str]
    reference_text: Optional[str]
    scores: dict
    result_metadata: dict
    latency_ms: Optional[float]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    created_at: datetime
