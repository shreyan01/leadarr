from __future__ import annotations

from functools import lru_cache

from app.ai.interfaces import ChatProvider, VisionProvider
from app.ai.providers.anthropic_provider import AnthropicChatProvider
from app.ai.providers.openai_provider import OpenAIChatProvider
from app.ai.providers.qwen_vl_provider import QwenVLProvider
from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderError


def get_chat_provider(settings: Settings | None = None) -> ChatProvider:
    settings = settings or get_settings()
    match settings.AI_CHAT_PROVIDER:
        case "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ProviderError("ANTHROPIC_API_KEY is not configured.")
            return AnthropicChatProvider(settings.ANTHROPIC_API_KEY.get_secret_value())
        case "openai":
            if not settings.OPENAI_API_KEY:
                raise ProviderError("OPENAI_API_KEY is not configured.")
            return OpenAIChatProvider(settings.OPENAI_API_KEY.get_secret_value())
        case "openrouter":
            if not settings.OPENROUTER_API_KEY:
                raise ProviderError("OPENROUTER_API_KEY is not configured.")
            return OpenAIChatProvider(
                settings.OPENROUTER_API_KEY.get_secret_value(), base_url="https://openrouter.ai/api/v1"
            )
        case "ollama":
            return OpenAIChatProvider("ollama", base_url=f"{settings.OLLAMA_BASE_URL}/v1")
        case "gemini" | "qwen":
            # Gemini and self-hosted Qwen-chat both speak an OpenAI-compatible
            # surface once fronted appropriately; wire the real adapter here
            # in Phase 2 without touching any call site.
            raise ProviderError(f"Chat provider '{settings.AI_CHAT_PROVIDER}' adapter not yet implemented.")
        case _:
            raise ProviderError(f"Unknown chat provider '{settings.AI_CHAT_PROVIDER}'.")


def get_vision_provider(settings: Settings | None = None) -> VisionProvider:
    settings = settings or get_settings()
    match settings.AI_VISION_PROVIDER:
        case "qwen_vl":
            return QwenVLProvider(settings.QWEN_VL_BASE_URL)
        case "anthropic" | "openai" | "gemini" | "ollama":
            raise ProviderError(f"Vision provider '{settings.AI_VISION_PROVIDER}' adapter not yet implemented.")
        case _:
            raise ProviderError(f"Unknown vision provider '{settings.AI_VISION_PROVIDER}'.")


@lru_cache
def cached_chat_provider() -> ChatProvider:
    return get_chat_provider()


@lru_cache
def cached_vision_provider() -> VisionProvider:
    return get_vision_provider()
