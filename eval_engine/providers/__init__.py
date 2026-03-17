from providers.base import BaseProvider
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider


def get_provider(config: dict, enable_thinking: bool = False) -> BaseProvider:
    provider = config.get("provider", "openai").lower()
    if provider in ("openai", "azure", "custom"):
        return OpenAIProvider(config, enable_thinking=enable_thinking)
    elif provider == "anthropic":
        return AnthropicProvider(config)
    else:
        # Default to OpenAI-compatible
        return OpenAIProvider(config, enable_thinking=enable_thinking)
