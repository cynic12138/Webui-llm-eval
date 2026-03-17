"""
Cost-effectiveness evaluator.
Combines quality scores with token cost to calculate score-per-dollar metrics.
Uses a built-in pricing table for common models.
"""
from typing import Optional


# Pricing per 1M tokens (USD) as of early 2025
PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    # Google
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # DeepSeek
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # Meta (via providers)
    "llama-3.1-405b": {"input": 3.00, "output": 3.00},
    "llama-3.1-70b": {"input": 0.70, "output": 0.80},
    "llama-3.1-8b": {"input": 0.10, "output": 0.10},
    # Mistral
    "mistral-large": {"input": 2.00, "output": 6.00},
    "mistral-small": {"input": 0.20, "output": 0.60},
    # Default fallback
    "default": {"input": 2.00, "output": 6.00},
}


class CostEffectivenessEvaluator:
    def __init__(self, custom_pricing: Optional[dict] = None):
        self.pricing = dict(PRICING)
        if custom_pricing:
            self.pricing.update(custom_pricing)

    def evaluate(self, provider, sample: dict) -> dict:
        """
        Evaluate cost-effectiveness by running an evaluation task and computing
        the cost and score-per-dollar ratio.

        sample:
            prompt: str - the prompt to send
            model_name: str (optional) - model identifier for pricing lookup
            quality_score: float (optional) - pre-computed quality score (0-1);
                if not provided, a simple quality heuristic is used
        """
        prompt = sample.get("prompt", "Explain the concept of opportunity cost in economics.")
        model_name = sample.get("model_name", "")
        precomputed_score = sample.get("quality_score")

        # If no model_name, try to get it from provider
        if not model_name:
            model_name = getattr(provider, "model", "") or getattr(provider, "model_name", "default")

        result = provider.complete(prompt)
        output = result["output"].strip()
        prompt_tokens = result.get("prompt_tokens", 0)
        completion_tokens = result.get("completion_tokens", 0)
        latency_ms = result.get("latency_ms", 0)

        # Calculate cost
        cost_usd = self._calculate_cost(model_name, prompt_tokens, completion_tokens)

        # Quality score
        if precomputed_score is not None:
            quality = float(precomputed_score)
        else:
            quality = self._estimate_quality(output)

        # Score per dollar (higher is better)
        score_per_dollar = quality / cost_usd if cost_usd > 0 else 0.0

        # Tokens per second
        tps = (completion_tokens / (latency_ms / 1000.0)) if latency_ms > 0 else 0.0

        return {
            "output": output,
            "scores": {
                "cost_usd": cost_usd,
                "score_per_dollar": score_per_dollar,
            },
            "metadata": {
                "model_name": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "latency_ms": latency_ms,
                "tokens_per_second": round(tps, 1),
                "quality_score": quality,
                "pricing_used": self._get_pricing(model_name),
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def calculate_batch_cost(self, model_name: str, results: list) -> dict:
        """
        Calculate aggregate cost metrics for a batch of evaluation results.

        results: list of dicts, each with prompt_tokens / completion_tokens / quality_score
        """
        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        quality_scores = []

        for r in results:
            pt = r.get("prompt_tokens", 0)
            ct = r.get("completion_tokens", 0)
            total_prompt_tokens += pt
            total_completion_tokens += ct
            total_cost += self._calculate_cost(model_name, pt, ct)
            qs = r.get("quality_score")
            if qs is not None:
                quality_scores.append(float(qs))

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        score_per_dollar = avg_quality / total_cost if total_cost > 0 else 0.0

        return {
            "total_cost_usd": total_cost,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "avg_quality_score": avg_quality,
            "score_per_dollar": score_per_dollar,
            "num_samples": len(results),
        }

    def _calculate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate USD cost for given token counts."""
        pricing = self._get_pricing(model_name)
        cost = (
            (prompt_tokens / 1_000_000) * pricing["input"]
            + (completion_tokens / 1_000_000) * pricing["output"]
        )
        return cost

    def _get_pricing(self, model_name: str) -> dict:
        """Look up pricing for a model, falling back to default."""
        # Try exact match
        if model_name in self.pricing:
            return self.pricing[model_name]

        # Try partial match (model name may have version suffixes)
        model_lower = model_name.lower()
        for key in self.pricing:
            if key != "default" and key.lower() in model_lower:
                return self.pricing[key]

        return self.pricing["default"]

    def _estimate_quality(self, output: str) -> float:
        """
        Simple quality heuristic when no external score is provided.
        Based on response length and structure.
        """
        if not output:
            return 0.0

        words = output.split()
        word_count = len(words)

        # Length component: ideal range is 30-200 words
        if word_count < 5:
            length_score = 0.1
        elif word_count < 30:
            length_score = 0.3 + 0.4 * (word_count / 30.0)
        elif word_count <= 200:
            length_score = 0.8
        else:
            length_score = max(0.5, 0.8 - (word_count - 200) / 1000.0)

        # Structure component: presence of sentences
        sentence_count = output.count(".") + output.count("!") + output.count("?")
        structure_score = min(sentence_count / 3.0, 1.0)

        return (length_score * 0.6 + structure_score * 0.4)
