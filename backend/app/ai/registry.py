from __future__ import annotations

from functools import lru_cache

from app.ai.interfaces import ChatProvider, EmbeddingProvider, VisionProvider
from app.ai.providers.anthropic_provider import AnthropicChatProvider
from app.ai.providers.gemini_provider import GeminiChatProvider
from app.ai.providers.openai_provider import OpenAIChatProvider
from app.ai.providers.qwen_embedding_provider import QwenEmbeddingProvider
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
        case "qwen":
            # Reuses the same local Qwen2.5-VL server already running for
            # vision (see docker-compose.yml's qwen-vl service) — it's a
            # general-purpose instruct model too, so this is free, fully
            # local chat/report/email generation with zero extra GPU
            # memory or infrastructure beyond what vision already needs.
            return OpenAIChatProvider("not-needed", base_url=f"{settings.QWEN_VL_BASE_URL}/v1")
        case "gemini":
            if not settings.GEMINI_API_KEY:
                raise ProviderError("GEMINI_API_KEY is not configured.")
            return GeminiChatProvider(settings.GEMINI_API_KEY.get_secret_value())
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


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    match settings.AI_EMBEDDING_PROVIDER:
        case "qwen":
            # Dedicated Qwen3-Embedding model (0.6B/4B/8B) — a different
            # architecture from Qwen2.5-VL, served on its own local
            # endpoint. See docker-compose.yml's qwen-embed service.
            return QwenEmbeddingProvider(settings.QWEN_EMBED_BASE_URL)
        case "openai":
            if not settings.OPENAI_API_KEY:
                raise ProviderError("OPENAI_API_KEY is not configured.")
            raise ProviderError("OpenAI embedding adapter not yet implemented — use AI_EMBEDDING_PROVIDER=qwen.")
        case "gemini" | "ollama":
            raise ProviderError(f"Embedding provider '{settings.AI_EMBEDDING_PROVIDER}' adapter not yet implemented.")
        case _:
            raise ProviderError(f"Unknown embedding provider '{settings.AI_EMBEDDING_PROVIDER}'.")


@lru_cache
def cached_chat_provider() -> ChatProvider:
    return get_chat_provider()


@lru_cache
def cached_vision_provider() -> VisionProvider:
    return get_vision_provider()


@lru_cache
def cached_embedding_provider() -> EmbeddingProvider:
    return get_embedding_provider()