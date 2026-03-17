"""Anthropic provider."""
import time
from typing import Optional
from providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        import anthropic
        import httpx
        http_client = httpx.Client(
            transport=httpx.HTTPTransport(),
            timeout=300.0,
        )
        self.client = anthropic.Anthropic(
            api_key=config.get("api_key") or "not-needed",
            timeout=300.0,
            http_client=http_client,
        )

    def complete(self, prompt: str, system: Optional[str] = None, **kwargs) -> dict:
        messages = [{"role": "user", "content": prompt}]
        return self._call(messages, system=system, **kwargs)

    def complete_messages(self, messages: list, **kwargs) -> dict:
        """Complete with pre-formed messages list."""
        # Extract system message if present
        system = None
        chat_messages = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            else:
                chat_messages.append(m)
        return self._call(chat_messages, system=system, **kwargs)

    def _call(self, messages: list, system: Optional[str] = None, **kwargs) -> dict:
        params = {**self.params, **kwargs}
        max_tokens = params.pop("max_tokens", 2048)

        start = time.time()
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            system=system or "You are a helpful assistant.",
            messages=messages,
        )
        latency_ms = (time.time() - start) * 1000

        return {
            "output": response.content[0].text,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "latency_ms": latency_ms,
        }
