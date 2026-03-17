"""OpenAI provider."""
import time
from typing import Optional
from providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, config: dict, enable_thinking: bool = False):
        super().__init__(config)
        self.enable_thinking = enable_thinking
        import openai
        import httpx
        api_key = config.get("api_key") or "not-needed"
        # Use HTTPTransport to bypass ALL_PROXY (socks5 not supported by httpx)
        http_client = httpx.Client(
            transport=httpx.HTTPTransport(),
            timeout=300.0,
        )
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=config.get("base_url"),
            timeout=300.0,
            http_client=http_client,
        )

    def complete(self, prompt: str, system: Optional[str] = None, **kwargs) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._call(messages, **kwargs)

    def complete_messages(self, messages: list, **kwargs) -> dict:
        """Complete with pre-formed messages list (e.g., multi-turn or healthbench format)."""
        return self._call(messages, **kwargs)

    def _call(self, messages: list, **kwargs) -> dict:
        params = {**self.params, **kwargs}
        temperature = params.pop("temperature", 0.0)
        max_tokens = params.pop("max_tokens", 2048)
        top_p = params.pop("top_p", None)
        top_k = params.pop("top_k", None)
        repetition_penalty = params.pop("repetition_penalty", None)
        presence_penalty = params.pop("presence_penalty", None)

        # Build extra_body only when needed (vLLM-compatible params)
        extra_body: dict = {}
        if self.enable_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": True}
        if top_k is not None:
            extra_body["top_k"] = top_k
        if repetition_penalty is not None:
            extra_body["repetition_penalty"] = repetition_penalty

        create_kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body
        if top_p is not None:
            create_kwargs["top_p"] = top_p
        if presence_penalty is not None:
            create_kwargs["presence_penalty"] = presence_penalty

        start = time.time()
        response = self.client.chat.completions.create(**create_kwargs)
        latency_ms = (time.time() - start) * 1000

        return {
            "output": response.choices[0].message.content,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "latency_ms": latency_ms,
        }
