from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from app.ai.interfaces import ChatResult, Message
from app.core.exceptions import ProviderError


class OpenAIChatProvider:
    """Also usable for any OpenAI-compatible endpoint (OpenRouter, Ollama)
    by passing a different ``base_url`` at construction time."""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._http_client = httpx.AsyncClient()
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, http_client=self._http_client)

    async def complete(
        self, messages: list[Message], *, model: str, temperature: float = 0.3, max_tokens: int = 2000
    ) -> ChatResult:
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise ProviderError(f"OpenAI-compatible completion failed: {exc}") from exc

        choice = response.choices[0]
        usage = response.usage
        return ChatResult(
            text=choice.message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            raw=response.model_dump(),
        )
