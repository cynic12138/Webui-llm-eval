"""
Main evaluation engine orchestrator.
Called from the Celery worker for each sample.
"""
import sys
import os

# Add eval_engine to path
sys.path.insert(0, os.path.dirname(__file__))

from providers import get_provider
from evaluators.llm_judge import LLMJudgeEvaluator
from evaluators.benchmark import BenchmarkEvaluator
from evaluators.hallucination import HallucinationEvaluator
from evaluators.robustness import RobustnessEvaluator
from evaluators.consistency import ConsistencyEvaluator
from evaluators.safety import SafetyEvaluator
from evaluators.rag import RAGEvaluator
from evaluators.performance import PerformanceEvaluator
from evaluators.code_executor import CodeExecutionEvaluator
from evaluators.multiturn import MultiturnEvaluator
from evaluators.instruction_following import InstructionFollowingEvaluator
from evaluators.cot_reasoning import ChainOfThoughtEvaluator
from evaluators.long_context import LongContextEvaluator
from evaluators.structured_output import StructuredOutputEvaluator
from evaluators.multilingual import MultilingualEvaluator
from evaluators.tool_calling import ToolCallingEvaluator
from evaluators.multimodal import MultimodalEvaluator
from evaluators.cost_effectiveness import CostEffectivenessEvaluator
from evaluators.domain_eval import DomainEvaluator
from typing import Optional


class EvaluationEngine:
    def __init__(self, config: dict):
        self.config = config
        self._perf_evaluator = PerformanceEvaluator()
        self._safety_evaluator = SafetyEvaluator() if config.get("safety") else None
        self._metrics_evaluator = None  # lazy init for ObjectiveMetricsEvaluator
        self._provider_cache = {}  # model_id -> provider (reuse across samples)
        self._judge_provider = None  # cached judge provider
        self._judge_config_cache = {}  # judge_model_id -> config dict
        self._db_session = None  # cached DB session for judge lookups

    def _get_or_create_provider(self, model_config: dict):
        """Reuse provider across samples for the same model."""
        mid = model_config.get("id", id(model_config))
        if mid not in self._provider_cache:
            self._provider_cache[mid] = get_provider(
                model_config, enable_thinking=self.config.get("enable_thinking", False)
            )
        return self._provider_cache[mid]

    def _get_or_create_judge_provider(self):
        """Get cached judge provider (created once per engine lifetime)."""
        judge_model_id = self.config.get("judge_model_id")
        if not judge_model_id:
            return None
        if self._judge_provider is None:
            judge_config = self._get_judge_config(judge_model_id)
            if judge_config:
                self._judge_provider = get_provider(judge_config)
        return self._judge_provider

    def evaluate_sample(self, model_config: dict, sample: dict, sample_index: int) -> dict:
        """
        Evaluate a single sample for one model.
        Returns: {output, scores, metadata, latency_ms, prompt_tokens, completion_tokens}
        """
        config = self.config
        provider = self._get_or_create_provider(model_config)

        # Determine input
        # Handle Alpaca-style datasets: instruction + input are combined
        instruction = sample.get("instruction", "")
        supplementary_input = sample.get("input", "")
        if instruction and supplementary_input:
            # Both present: combine as "instruction\n\ninput"
            raw_input = f"{instruction}\n\n{supplementary_input}"
        elif instruction:
            # Only instruction (no supplementary input)
            raw_input = instruction
        else:
            # Fallback: try other common field names
            raw_input = (
                supplementary_input or
                sample.get("question") or
                sample.get("prompt") or
                sample.get("problem") or
                sample.get("text", "")
            )
        reference = (
            sample.get("output") or
            sample.get("answer") or
            sample.get("reference") or
            sample.get("expected", "")
        )

        # Handle message-list format (e.g., healthbench: [{"role": "user", "content": "..."}])
        input_is_messages = isinstance(raw_input, list) and raw_input and isinstance(raw_input[0], dict)
        if input_is_messages:
            # Extract text for evaluators that need a string
            input_text = " ".join(m.get("content", "") for m in raw_input if m.get("role") == "user")
        else:
            input_text = str(raw_input) if raw_input else ""

        if isinstance(reference, (list, dict)):
            import json as _json
            reference = _json.dumps(reference, ensure_ascii=False)

        scores = {}
        metadata = {}
        output_text = ""
        latency_ms = 0
        prompt_tokens = 0
        completion_tokens = 0

        # --- Standard LLM inference ---
        # Skip standard inference for benchmark-tagged or evaluator-type-tagged samples
        # (these evaluators call the provider themselves with their own prompts)
        tagged_benchmark = sample.get("_benchmark_id")
        tagged_evaluator = sample.get("_evaluator_type")
        if input_text and not config.get("code_execution") and not tagged_benchmark and not tagged_evaluator:
            try:
                if input_is_messages:
                    # For message-list inputs, pass messages directly via provider
                    result = provider.complete_messages(raw_input) if hasattr(provider, 'complete_messages') else provider.complete(input_text)
                else:
                    result = provider.complete(input_text)
                output_text = result.get("output", "")
                latency_ms = result.get("latency_ms", 0)
                prompt_tokens = result.get("prompt_tokens", 0)
                completion_tokens = result.get("completion_tokens", 0)
            except Exception as e:
                output_text = f"ERROR: {e}"
                metadata["inference_error"] = str(e)

        # --- Performance metrics ---
        if config.get("performance", True):
            perf = self._perf_evaluator.evaluate(
                model_config.get("model_name", ""),
                {"latency_ms": latency_ms, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
            )
            metadata.update(perf)

        # --- LLM-as-Judge ---
        if config.get("llm_judge") and config.get("judge_model_id") and output_text:
            try:
                jp = self._get_or_create_judge_provider()
                if jp:
                    judge = LLMJudgeEvaluator(
                        jp,
                        dimensions=config.get("judge_dimensions", ["accuracy", "fluency", "relevance"])
                    )
                    judge_scores = judge.evaluate(input_text, output_text, reference or None)
                    scores.update(judge_scores)
            except Exception as e:
                metadata["judge_error"] = str(e)

        # --- Standard Benchmarks ---
        judge_provider = self._get_or_create_judge_provider()

        if tagged_benchmark:
            # Sample loaded from benchmark dataset: only run its own evaluator
            try:
                bm_evaluator = BenchmarkEvaluator(tagged_benchmark)
                bm_result = bm_evaluator.evaluate(provider, sample, judge_provider=judge_provider)
                scores.update(bm_result.get("scores", {}))
                if not output_text:
                    output_text = bm_result.get("output", "")
                latency_ms = bm_result.get("latency_ms", latency_ms)
                prompt_tokens = bm_result.get("prompt_tokens", prompt_tokens)
                completion_tokens = bm_result.get("completion_tokens", completion_tokens)
            except Exception as e:
                metadata[f"benchmark_{tagged_benchmark}_error"] = str(e)
        else:
            # User dataset: run all selected benchmark evaluators
            for benchmark_id in config.get("benchmarks", []):
                try:
                    bm_evaluator = BenchmarkEvaluator(benchmark_id)
                    bm_result = bm_evaluator.evaluate(provider, sample, judge_provider=judge_provider)
                    scores.update(bm_result.get("scores", {}))
                    if not output_text:
                        output_text = bm_result.get("output", "")
                except Exception as e:
                    metadata[f"benchmark_{benchmark_id}_error"] = str(e)

        # --- Code Execution ---
        if config.get("code_execution"):
            try:
                code_eval = CodeExecutionEvaluator()
                code_result = code_eval.evaluate_completion(provider, sample)
                output_text = code_result.get("output", "")
                scores.update(code_result.get("scores", {}))
                latency_ms = code_result.get("latency_ms", 0)
                prompt_tokens = code_result.get("prompt_tokens", 0)
                completion_tokens = code_result.get("completion_tokens", 0)
            except Exception as e:
                metadata["code_exec_error"] = str(e)

        # --- Hallucination / Robustness / Consistency ---
        # Skip these for benchmark-tagged or evaluator-type-tagged samples
        evaluator_type_tag = sample.get("_evaluator_type")
        if not tagged_benchmark and not evaluator_type_tag:
            if config.get("hallucination") and input_text:
                try:
                    hal = HallucinationEvaluator(n_samples=config.get("hallucination_n_samples", 5))
                    hal_result = hal.evaluate(provider, input_text)
                    scores["hallucination_consistency"] = hal_result.get("hallucination_consistency", 0.5)
                    scores["hallucination_risk"] = hal_result.get("hallucination_risk", 0.5)
                except Exception as e:
                    metadata["hallucination_error"] = str(e)

            if config.get("robustness") and input_text:
                try:
                    rob = RobustnessEvaluator(perturbations=config.get("robustness_perturbations", ["synonym", "typo", "case"]))
                    rob_result = rob.evaluate(provider, input_text, reference or None)
                    scores["robustness_score"] = rob_result.get("robustness_score", 0.5)
                except Exception as e:
                    metadata["robustness_error"] = str(e)

            if config.get("consistency") and input_text:
                try:
                    con = ConsistencyEvaluator(n_runs=config.get("consistency_n_runs", 3))
                    con_result = con.evaluate(provider, input_text)
                    scores["consistency_score"] = con_result.get("consistency_score", 0.5)
                except Exception as e:
                    metadata["consistency_error"] = str(e)

        # --- Safety ---
        if config.get("safety") and output_text:
            try:
                safety_scores = self._safety_evaluator.evaluate(output_text)
                scores.update(safety_scores)
            except Exception as e:
                metadata["safety_error"] = str(e)

        # --- Additional evaluators (only for user datasets, not benchmark samples) ---
        # Benchmark-tagged samples already have their own scoring; running these
        # would add N extra API calls per sample for no benefit.
        if not tagged_benchmark:
            # If sample is tagged with _evaluator_type (builtin sample), only run that evaluator
            evaluator_type = sample.get("_evaluator_type")

            # --- RAG ---
            if config.get("rag_eval") and input_text and output_text and not evaluator_type:
                try:
                    context = sample.get("context") or sample.get("passages", "")
                    rag = RAGEvaluator(judge_provider=self._get_or_create_judge_provider())
                    rag_scores = rag.evaluate(input_text, output_text, context if isinstance(context, str) else str(context))
                    scores.update(rag_scores)
                except Exception as e:
                    metadata["rag_error"] = str(e)

            # --- Multi-turn ---
            if config.get("multiturn") and sample.get("conversation") and not evaluator_type:
                try:
                    mt = MultiturnEvaluator()
                    mt_result = mt.evaluate(provider, sample["conversation"])
                    scores["multiturn_coherence"] = mt_result.get("multiturn_coherence", 0.5)
                except Exception as e:
                    metadata["multiturn_error"] = str(e)

            # --- Instruction Following ---
            if config.get("instruction_following") and (
                sample.get("instruction") or sample.get("constraints")
                or evaluator_type == "instruction_following"
            ):
                try:
                    ife = InstructionFollowingEvaluator()
                    ife_result = ife.evaluate(provider, sample)
                    scores.update(ife_result.get("scores", {}))
                    if not output_text:
                        output_text = ife_result.get("output", "")
                except Exception as e:
                    metadata["instruction_following_error"] = str(e)

            # --- Chain-of-Thought Reasoning ---
            if config.get("cot_reasoning") and (
                input_text or sample.get("problem")
                or evaluator_type == "cot_reasoning"
            ):
                try:
                    cot = ChainOfThoughtEvaluator()
                    cot_result = cot.evaluate(provider, sample)
                    scores.update(cot_result.get("scores", {}))
                    if not output_text:
                        output_text = cot_result.get("output", "")
                except Exception as e:
                    metadata["cot_reasoning_error"] = str(e)

            # --- Long Context ---
            if config.get("long_context") and (not evaluator_type or evaluator_type == "long_context"):
                try:
                    lc = LongContextEvaluator(context_length=config.get("long_context_length", 4000))
                    lc_result = lc.evaluate(provider, sample)
                    scores.update(lc_result.get("scores", {}))
                    if not output_text:
                        output_text = lc_result.get("output", "")
                except Exception as e:
                    metadata["long_context_error"] = str(e)

            # --- Structured Output ---
            if config.get("structured_output") and (
                input_text or sample.get("instruction")
                or evaluator_type == "structured_output"
            ):
                try:
                    so = StructuredOutputEvaluator(schema=config.get("output_schema"))
                    so_result = so.evaluate(provider, sample)
                    scores.update(so_result.get("scores", {}))
                    if not output_text:
                        output_text = so_result.get("output", "")
                except Exception as e:
                    metadata["structured_output_error"] = str(e)

            # --- Multilingual ---
            if config.get("multilingual") and (
                input_text or sample.get("prompts")
                or evaluator_type == "multilingual"
            ):
                try:
                    ml = MultilingualEvaluator(languages=config.get("multilingual_languages"))
                    ml_result = ml.evaluate(provider, sample)
                    scores.update(ml_result.get("scores", {}))
                    if not output_text and ml_result.get("output"):
                        output_text = ml_result["output"]
                    if not input_text and ml_result.get("input_display"):
                        input_text = ml_result["input_display"]
                    metadata["multilingual_details"] = ml_result.get("metadata", {})
                except Exception as e:
                    metadata["multilingual_error"] = str(e)

            # --- Tool Calling ---
            if config.get("tool_calling") and (not evaluator_type or evaluator_type == "tool_calling"):
                try:
                    tc = ToolCallingEvaluator()
                    tc_result = tc.evaluate(provider, sample)
                    scores.update(tc_result.get("scores", {}))
                    if not output_text:
                        output_text = tc_result.get("output", "")
                except Exception as e:
                    metadata["tool_calling_error"] = str(e)

            # --- Multimodal ---
            if config.get("multimodal") and (not evaluator_type or evaluator_type == "multimodal"):
                try:
                    mm = MultimodalEvaluator()
                    mm_result = mm.evaluate(provider, sample)
                    scores.update(mm_result.get("scores", {}))
                    if not output_text:
                        output_text = mm_result.get("output", "")
                except Exception as e:
                    metadata["multimodal_error"] = str(e)

            # --- Cost Effectiveness ---
            if config.get("cost_analysis") and (output_text or scores) and not evaluator_type:
                try:
                    ce = CostEffectivenessEvaluator()
                    ce_result = ce.evaluate(provider, sample)
                    scores.update(ce_result.get("scores", {}))
                    metadata.update(ce_result.get("metadata", {}))
                    if not output_text:
                        output_text = ce_result.get("output", "")
                except Exception as e:
                    metadata["cost_analysis_error"] = str(e)

        # --- Objective Metrics (algorithmic, no judge needed) ---
        if config.get("objective_metrics") and output_text:
            try:
                selected = config.get("selected_metrics", [])
                if self._metrics_evaluator is None:
                    from evaluators.metrics import ObjectiveMetricsEvaluator
                    self._metrics_evaluator = ObjectiveMetricsEvaluator(selected or None)
                metric_scores = self._metrics_evaluator.evaluate(output_text, reference or None)
                scores.update(metric_scores)
            except Exception as e:
                metadata["objective_metrics_error"] = str(e)

        # --- Domain Evaluation (dual-prompt) ---
        if (config.get("domain_eval")
                and config.get("generation_prompts")
                and config.get("evaluation_prompts")):
            try:
                jp = self._get_or_create_judge_provider()
                if jp:
                    domain_evaluator = DomainEvaluator(
                        config["generation_prompts"],
                        config["evaluation_prompts"],
                    )
                    domain_result = domain_evaluator.evaluate(provider, jp, sample)
                    # Override output if domain eval produced one
                    if domain_result.get("output"):
                        output_text = domain_result["output"]
                    scores.update(domain_result.get("scores", {}))
                    metadata.update(domain_result.get("metadata", {}))
                    if domain_result.get("latency_ms"):
                        latency_ms = domain_result["latency_ms"]
                    if domain_result.get("prompt_tokens"):
                        prompt_tokens = domain_result["prompt_tokens"]
                    if domain_result.get("completion_tokens"):
                        completion_tokens = domain_result["completion_tokens"]
            except Exception as e:
                metadata["domain_eval_error"] = str(e)
                scores["domain_overall"] = -1  # Mark as evaluation failed
                scores["domain_eval_failed"] = True

        return {
            "output": output_text,
            "scores": scores,
            "metadata": metadata,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def _get_judge_config(self, judge_model_id: int) -> Optional[dict]:
        """Fetch judge model config from DB synchronously (cached)."""
        if judge_model_id in self._judge_config_cache:
            return self._judge_config_cache[judge_model_id]

        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            import os

            db_url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
            if not db_url:
                return None

            if self._db_session is None:
                engine = create_engine(db_url)
                Session = sessionmaker(bind=engine)
                self._db_session = Session()

            session = self._db_session
            sys.path.insert(0, "/app")
            from app.core.security import decrypt_api_key

            # Try JudgeModelConfig first
            try:
                from app.db.models import JudgeModelConfig
                jmc = session.get(JudgeModelConfig, judge_model_id)
                if jmc:
                    api_key = decrypt_api_key(jmc.api_key_encrypted) if jmc.api_key_encrypted else None
                    result = {
                        "id": jmc.id,
                        "name": jmc.name,
                        "provider": jmc.provider,
                        "api_key": api_key,
                        "base_url": jmc.base_url,
                        "model_name": jmc.model_name,
                        "params": jmc.params or {},
                    }
                    self._judge_config_cache[judge_model_id] = result
                    return result
            except Exception:
                pass

            # Fallback to ModelConfig for backward compatibility
            from app.db.models import ModelConfig
            mc = session.get(ModelConfig, judge_model_id)
            if not mc:
                self._judge_config_cache[judge_model_id] = None
                return None
            api_key = decrypt_api_key(mc.api_key_encrypted) if mc.api_key_encrypted else None
            result = {
                "id": mc.id,
                "name": mc.name,
                "provider": mc.provider,
                "api_key": api_key,
                "base_url": mc.base_url,
                "model_name": mc.model_name,
                "params": mc.params or {},
            }
            self._judge_config_cache[judge_model_id] = result
            return result
        except Exception:
            return None
