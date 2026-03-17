"""Base LLM provider interface."""
import time
from abc import ABC, abstractmethod
from typing import Optional


class BaseProvider(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.model_name = config.get("model_name", "")
        self.params = config.get("params", {})

    @abstractmethod
    def complete(self, prompt: str, system: Optional[str] = None, **kwargs) -> dict:
        """
        Returns: {
            "output": str,
            "prompt_tokens": int,
            "completion_tokens": int,
            "latency_ms": float
        }
        """
        pass

    def complete_with_timing(self, prompt: str, system: Optional[str] = None, **kwargs) -> dict:
        start = time.time()
        result = self.complete(prompt, system, **kwargs)
        if "latency_ms" not in result:
            result["latency_ms"] = (time.time() - start) * 1000
        return result
