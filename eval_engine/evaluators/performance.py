"""
Performance metrics: latency, throughput, cost estimation.
"""

# Cost per 1M tokens (as of 2024 public pricing)
PRICING_TABLE = {
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "default": {"input": 2.0, "output": 6.0},
}


class PerformanceEvaluator:
    def evaluate(self, model_name: str, result: dict) -> dict:
        latency_ms = result.get("latency_ms", 0)
        prompt_tokens = result.get("prompt_tokens", 0)
        completion_tokens = result.get("completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        # Cost estimation
        pricing = PRICING_TABLE.get(model_name, PRICING_TABLE["default"])
        cost_usd = (
            (prompt_tokens / 1_000_000) * pricing["input"] +
            (completion_tokens / 1_000_000) * pricing["output"]
        )

        # Tokens per second
        tps = (completion_tokens / (latency_ms / 1000)) if latency_ms > 0 else 0

        return {
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "tokens_per_second": tps,
        }
