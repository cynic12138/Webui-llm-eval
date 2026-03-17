"""
Objective evaluation metrics registry endpoint.
"""
import sys
import os
from fastapi import APIRouter

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Add eval_engine to path so we can import the registry
_eval_engine_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "eval_engine")
if _eval_engine_path not in sys.path:
    sys.path.insert(0, os.path.abspath(_eval_engine_path))


@router.get("/registry")
def get_metrics_registry():
    """Return the full metric registry for the frontend selector."""
    from evaluators.metrics import METRIC_REGISTRY
    return METRIC_REGISTRY


# Comprehensive score key definitions covering ALL evaluator output keys.
# Used by the frontend to look up display names, descriptions, and categories.
SCORE_DEFINITIONS: dict[str, dict] = {
    # LLM-as-Judge
    "judge_accuracy": {"name": "准确性 (Judge)", "category": "llm_judge", "normalized": True},
    "judge_fluency": {"name": "流畅性 (Judge)", "category": "llm_judge", "normalized": True},
    "judge_relevance": {"name": "相关性 (Judge)", "category": "llm_judge", "normalized": True},
    # Hallucination
    "hallucination_consistency": {"name": "幻觉一致性", "category": "hallucination", "normalized": True},
    "hallucination_risk": {"name": "幻觉风险", "category": "hallucination", "normalized": True},
    # Robustness & Consistency
    "robustness_score": {"name": "鲁棒性", "category": "robustness", "normalized": True},
    "consistency_score": {"name": "一致性", "category": "consistency", "normalized": True},
    # Safety
    "toxicity": {"name": "无毒性", "category": "safety", "normalized": True},
    "severe_toxicity": {"name": "无严重毒性", "category": "safety", "normalized": True},
    "obscene": {"name": "无低俗", "category": "safety", "normalized": True},
    "insult": {"name": "无侮辱", "category": "safety", "normalized": True},
    "threat": {"name": "无威胁", "category": "safety", "normalized": True},
    "identity_attack": {"name": "无身份攻击", "category": "safety", "normalized": True},
    "bias_score": {"name": "无偏见", "category": "safety", "normalized": True},
    "safety_overall": {"name": "安全总分", "category": "safety", "normalized": True},
    "safety_keyword_based": {"name": "安全 (关键词)", "category": "safety", "normalized": True},
    # RAG
    "rag_faithfulness": {"name": "RAG 忠实性", "category": "rag", "normalized": True},
    "rag_relevance": {"name": "RAG 相关性", "category": "rag", "normalized": True},
    "rag_completeness": {"name": "RAG 完整性", "category": "rag", "normalized": True},
    # Benchmarks
    "mmlu_accuracy": {"name": "MMLU-Pro", "category": "benchmark", "normalized": True},
    "gsm8k_accuracy": {"name": "GSM8K", "category": "benchmark", "normalized": True},
    "humaneval_pass@1": {"name": "HumanEval", "category": "benchmark", "normalized": True},
    "ceval_accuracy": {"name": "C-Eval", "category": "benchmark", "normalized": True},
    "hellaswag_accuracy": {"name": "HellaSwag", "category": "benchmark", "normalized": True},
    "truthfulqa_accuracy": {"name": "TruthfulQA", "category": "benchmark", "normalized": True},
    "math_accuracy": {"name": "MATH", "category": "benchmark", "normalized": True},
    "arc_accuracy": {"name": "ARC", "category": "benchmark", "normalized": True},
    "ifeval_strict": {"name": "IFEval", "category": "benchmark", "normalized": True},
    "bigcodebench_pass@1": {"name": "BigCodeBench", "category": "benchmark", "normalized": True},
    # MT-Bench
    "mt_bench_score": {"name": "MT-Bench 总分", "category": "benchmark", "normalized": True},
    "mt_bench_helpfulness": {"name": "MT有用性", "category": "benchmark", "normalized": True},
    "mt_bench_relevance": {"name": "MT相关性", "category": "benchmark", "normalized": True},
    "mt_bench_coherence": {"name": "MT连贯性", "category": "benchmark", "normalized": True},
    "mt_bench_depth": {"name": "MT深度", "category": "benchmark", "normalized": True},
    "mt_bench_instruction_following": {"name": "MT指令遵循", "category": "benchmark", "normalized": True},
    # AlpacaEval
    "alpaca_quality": {"name": "AlpacaEval 总分", "category": "benchmark", "normalized": True},
    "alpaca_accuracy": {"name": "Alpaca准确性", "category": "benchmark", "normalized": True},
    "alpaca_helpfulness": {"name": "Alpaca有用性", "category": "benchmark", "normalized": True},
    "alpaca_clarity": {"name": "Alpaca清晰度", "category": "benchmark", "normalized": True},
    "alpaca_completeness": {"name": "Alpaca完整性", "category": "benchmark", "normalized": True},
    "alpaca_conciseness": {"name": "Alpaca简洁性", "category": "benchmark", "normalized": True},
    # SWE-Bench
    "swe_resolve_rate": {"name": "SWE-Bench 总分", "category": "benchmark", "normalized": True},
    "swe_correctness": {"name": "SWE正确性", "category": "benchmark", "normalized": True},
    "swe_code_quality": {"name": "SWE代码质量", "category": "benchmark", "normalized": True},
    "swe_completeness": {"name": "SWE完整性", "category": "benchmark", "normalized": True},
    "swe_explanation": {"name": "SWE解释质量", "category": "benchmark", "normalized": True},
    # HealthBench
    "healthbench_score": {"name": "HealthBench 总分", "category": "healthbench", "normalized": True},
    "healthbench_hard_score": {"name": "HealthBench-Hard", "category": "healthbench", "normalized": True},
    "healthbench_accuracy": {"name": "医学准确性", "category": "healthbench", "normalized": True},
    "healthbench_completeness": {"name": "医学完整性", "category": "healthbench", "normalized": True},
    "healthbench_context_awareness": {"name": "上下文感知", "category": "healthbench", "normalized": True},
    "healthbench_communication_quality": {"name": "沟通质量", "category": "healthbench", "normalized": True},
    "healthbench_instruction_following": {"name": "指令遵循 (HB)", "category": "healthbench", "normalized": True},
    # Domain
    "domain_overall": {"name": "领域总分", "category": "domain", "normalized": True},
    "domain_accuracy": {"name": "领域准确性", "category": "domain", "normalized": True},
    "domain_completeness": {"name": "领域完整性", "category": "domain", "normalized": True},
    "domain_professionalism": {"name": "领域专业性", "category": "domain", "normalized": True},
    "domain_safety": {"name": "领域安全性", "category": "domain", "normalized": True},
    # Chain-of-Thought
    "cot_step_count": {"name": "推理步数", "category": "cot", "normalized": False, "unit": "步"},
    "cot_has_reasoning": {"name": "包含推理", "category": "cot", "normalized": True},
    "cot_answer_correct": {"name": "答案正确", "category": "cot", "normalized": True},
    # Multi-turn
    "multiturn_coherence": {"name": "多轮连贯性", "category": "multiturn", "normalized": True},
    # Tool Calling
    "tool_selection_accuracy": {"name": "工具选择准确率", "category": "tool_calling", "normalized": True},
    "argument_accuracy": {"name": "参数准确率", "category": "tool_calling", "normalized": True},
    # Long Context
    "needle_retrieval": {"name": "长文本检索", "category": "long_context", "normalized": True},
    # Structured Output
    "json_valid": {"name": "JSON 有效性", "category": "structured_output", "normalized": True},
    "schema_compliant": {"name": "Schema 符合度", "category": "structured_output", "normalized": True},
    # Multimodal
    "vision_accuracy": {"name": "视觉理解", "category": "multimodal", "normalized": True},
    "text_accuracy": {"name": "文本准确率", "category": "multimodal", "normalized": True},
    "keyword_score": {"name": "关键词得分", "category": "multimodal", "normalized": True},
    "quality_score": {"name": "质量得分", "category": "cost", "normalized": True},
    # Cost
    "cost_usd": {"name": "成本 (USD)", "category": "cost", "normalized": False, "unit": "USD"},
    "score_per_dollar": {"name": "性价比", "category": "cost", "normalized": False},
    "avg_quality_score": {"name": "平均质量得分", "category": "cost", "normalized": True},
    # Multilingual
    "multilingual_avg": {"name": "多语言平均", "category": "multilingual", "normalized": True},
    # Objective Metrics
    "rouge_1": {"name": "ROUGE-1", "category": "objective", "normalized": True},
    "rouge_2": {"name": "ROUGE-2", "category": "objective", "normalized": True},
    "rouge_l": {"name": "ROUGE-L", "category": "objective", "normalized": True},
    "bleu": {"name": "BLEU", "category": "objective", "normalized": True},
    "meteor": {"name": "METEOR", "category": "objective", "normalized": True},
    "exact_match": {"name": "精确匹配", "category": "objective", "normalized": True},
    "token_f1": {"name": "Token F1", "category": "objective", "normalized": True},
    "embedding_cosine": {"name": "语义相似度", "category": "objective", "normalized": True},
    "bertscore_f1": {"name": "BERTScore", "category": "objective", "normalized": True},
    "distinct_1": {"name": "Distinct-1", "category": "objective", "normalized": True},
    "distinct_2": {"name": "Distinct-2", "category": "objective", "normalized": True},
    "response_length": {"name": "回复长度", "category": "objective", "normalized": False, "unit": "字符"},
    "entity_match_f1": {"name": "实体匹配 F1", "category": "objective", "normalized": True},
    "code_pass@1": {"name": "代码通过率", "category": "code", "normalized": True},
}


@router.get("/score-definitions")
def get_score_definitions():
    """Return definitions for ALL known score keys across all evaluators."""
    return SCORE_DEFINITIONS
