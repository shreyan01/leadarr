"""Provider-agnostic AI contracts.

Every service in ``app/services`` that needs AI depends on these Protocols,
never on a concrete SDK. Swapping OpenAI for Anthropic, or adding Ollama or
OpenRouter, means writing one adapter class in ``app/ai/providers`` and
registering it in ``registry.py`` — no other file changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class ChatResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class VisionResult:
    structured: dict
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict = field(default_factory=dict)


class ChatProvider(Protocol):
    async def complete(
        self, messages: list[Message], *, model: str, temperature: float = 0.3, max_tokens: int = 2000
    ) -> ChatResult: ...


class VisionProvider(Protocol):
    async def analyze_image(
        self, image_bytes: bytes, prompt: str, *, model: str, media_type: str = "image/png"
    ) -> VisionResult: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str], *, model: str) -> list[list[float]]: ...
