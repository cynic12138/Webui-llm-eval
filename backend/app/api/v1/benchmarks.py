import json
import sys
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db, get_current_user
from app.db import models
from typing import List, Optional

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

# Path to benchmark data
BENCHMARK_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "eval_engine" / "benchmark_data"

AVAILABLE_BENCHMARKS = [
    {
        "id": "mmlu_pro",
        "name": "MMLU-Pro",
        "description": "Massive Multitask Language Understanding - Professional level",
        "metric": "accuracy",
        "categories": ["math", "physics", "chemistry", "biology", "computer_science", "law", "history"],
        "sample_size": 12032,
        "data_source": "TIGER-Lab/MMLU-Pro",
    },
    {
        "id": "gsm8k",
        "name": "GSM8K",
        "description": "Grade School Math 8K - arithmetic reasoning",
        "metric": "accuracy",
        "categories": ["math"],
        "sample_size": 1319,
        "data_source": "openai/gsm8k",
    },
    {
        "id": "humaneval",
        "name": "HumanEval",
        "description": "Python code generation benchmark",
        "metric": "pass@1",
        "categories": ["code"],
        "sample_size": 164,
        "data_source": "openai/openai_humaneval",
    },
    {
        "id": "ceval",
        "name": "C-Eval",
        "description": "Chinese evaluation benchmark",
        "metric": "accuracy",
        "categories": ["stem", "social_science", "humanities", "other"],
        "sample_size": 1268,
        "data_source": "ceval/ceval-exam",
    },
    {
        "id": "hellaswag",
        "name": "HellaSwag",
        "description": "Commonsense NLI benchmark",
        "metric": "accuracy",
        "categories": ["reasoning"],
        "sample_size": 10042,
        "data_source": "Rowan/hellaswag",
    },
    {
        "id": "truthfulqa",
        "name": "TruthfulQA",
        "description": "Truthfulness evaluation benchmark",
        "metric": "truthfulness",
        "categories": ["truthfulness"],
        "sample_size": 817,
        "data_source": "truthfulqa/truthful_qa",
    },
    {
        "id": "math",
        "name": "MATH",
        "description": "Competition-level mathematics benchmark",
        "metric": "accuracy",
        "categories": ["math", "reasoning"],
        "sample_size": 5000,
        "data_source": "DigitalLearningGmbH/MATH-lighteval",
    },
    {
        "id": "arc",
        "name": "ARC-Challenge",
        "description": "AI2 Reasoning Challenge - science questions",
        "metric": "accuracy",
        "categories": ["reasoning", "science"],
        "sample_size": 1172,
        "data_source": "allenai/ai2_arc",
    },
    {
        "id": "mt_bench",
        "name": "MT-Bench",
        "description": "Multi-turn conversation benchmark with LLM judge scoring",
        "metric": "judge_score",
        "categories": ["conversation", "multi_turn"],
        "sample_size": 80,
        "data_source": "lmsys/mt_bench",
    },
    {
        "id": "alpaca_eval",
        "name": "AlpacaEval",
        "description": "Instruction-following evaluation based on AlpacaFarm",
        "metric": "win_rate",
        "categories": ["instruction_following"],
        "sample_size": 805,
        "data_source": "tatsu-lab/alpaca_eval",
    },
    {
        "id": "ifeval",
        "name": "IFEval",
        "description": "Instruction-Following Evaluation with verifiable constraints",
        "metric": "strict_accuracy",
        "categories": ["instruction_following"],
        "sample_size": 541,
        "data_source": "google/IFEval",
    },
    {
        "id": "swe_bench",
        "name": "SWE-Bench",
        "description": "Software engineering task resolution benchmark",
        "metric": "resolve_rate",
        "categories": ["code", "engineering"],
        "sample_size": 300,
        "data_source": "princeton-nlp/SWE-bench_Lite",
    },
    {
        "id": "bigcodebench",
        "name": "BigCodeBench",
        "description": "Large-scale code generation and understanding benchmark",
        "metric": "pass@1",
        "categories": ["code"],
        "sample_size": 1140,
        "data_source": "bigcode/bigcodebench",
    },
    {
        "id": "livebench",
        "name": "LiveBench",
        "description": "Contamination-free benchmark with regularly updated questions",
        "metric": "accuracy",
        "categories": ["reasoning", "math", "coding", "language"],
        "sample_size": 200,
        "data_source": "livebench/reasoning",
    },
    {
        "id": "healthbench",
        "name": "HealthBench",
        "description": "OpenAI医疗健康LLM评测基准 — 基于262位医生标注的多轮对话，涵盖7大主题5个评测维度",
        "metric": "healthbench_score",
        "categories": ["medical", "health", "safety", "multi_turn"],
        "sample_size": 5000,
        "data_source": "openai/healthbench",
    },
    {
        "id": "healthbench_hard",
        "name": "HealthBench-Hard",
        "description": "HealthBench困难子集 — 前沿模型仍难以解决的医疗场景",
        "metric": "healthbench_score",
        "categories": ["medical", "health", "hard"],
        "sample_size": 29511,
        "data_source": "openai/healthbench",
    },
]


def _check_data_available(benchmark_id: str) -> bool:
    """Check if JSONL data file exists for this benchmark."""
    return (BENCHMARK_DATA_DIR / f"{benchmark_id}.jsonl").exists()


def _get_actual_sample_count(benchmark_id: str) -> Optional[int]:
    """Get real sample count from meta file if available."""
    meta_path = BENCHMARK_DATA_DIR / f"{benchmark_id}.meta.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("sample_count")
        except Exception:
            pass
    return None


def _enrich_benchmark(b: dict) -> dict:
    """Add dynamic data_available and actual_sample_count fields."""
    enriched = dict(b)
    enriched["data_available"] = _check_data_available(b["id"])
    actual_count = _get_actual_sample_count(b["id"])
    if actual_count is not None:
        enriched["actual_sample_count"] = actual_count
    return enriched


@router.get("/")
async def list_benchmarks(
    current_user: models.User = Depends(get_current_user),
):
    return [_enrich_benchmark(b) for b in AVAILABLE_BENCHMARKS]


@router.get("/{benchmark_id}")
async def get_benchmark(
    benchmark_id: str,
    current_user: models.User = Depends(get_current_user),
):
    for b in AVAILABLE_BENCHMARKS:
        if b["id"] == benchmark_id:
            return _enrich_benchmark(b)
    raise HTTPException(status_code=404, detail="Benchmark not found")


@router.get("/{benchmark_id}/preview")
async def preview_benchmark_data(
    benchmark_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
):
    """Preview first N samples of a benchmark dataset."""
    # Validate benchmark exists
    found = False
    for b in AVAILABLE_BENCHMARKS:
        if b["id"] == benchmark_id:
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    jsonl_path = BENCHMARK_DATA_DIR / f"{benchmark_id}.jsonl"
    records = []
    total = 0

    if jsonl_path.exists():
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                if len(records) < limit and line.strip():
                    records.append(json.loads(line))
    else:
        # Fallback: use built-in demo samples from eval_engine
        eval_engine_path = str(BENCHMARK_DATA_DIR.parent)
        if eval_engine_path not in sys.path:
            sys.path.insert(0, eval_engine_path)
        try:
            from evaluators.benchmark import BenchmarkEvaluator
            demo = BenchmarkEvaluator(benchmark_id).get_builtin_samples()
            records = demo[:limit]
            total = len(demo)
        except Exception:
            pass

    return {"records": records, "total": total, "data_available": jsonl_path.exists()}


@router.get("/{benchmark_id}/data-info")
async def benchmark_data_info(
    benchmark_id: str,
    current_user: models.User = Depends(get_current_user),
):
    """Return metadata about a benchmark dataset."""
    found = False
    for b in AVAILABLE_BENCHMARKS:
        if b["id"] == benchmark_id:
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    meta_path = BENCHMARK_DATA_DIR / f"{benchmark_id}.meta.json"
    jsonl_path = BENCHMARK_DATA_DIR / f"{benchmark_id}.jsonl"

    info = {
        "benchmark_id": benchmark_id,
        "data_available": jsonl_path.exists(),
        "sample_count": 0,
        "source": "",
        "downloaded_at": None,
    }

    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            info.update({
                "sample_count": meta.get("sample_count", 0),
                "source": meta.get("source", ""),
                "downloaded_at": meta.get("downloaded_at"),
            })
        except Exception:
            pass
    elif jsonl_path.exists():
        info["sample_count"] = sum(1 for line in open(jsonl_path) if line.strip())

    return info
