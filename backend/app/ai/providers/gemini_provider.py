"""Gemini chat provider.

Uses the current `google-genai` SDK (the older `google-generativeai`
package was deprecated and reached end-of-life in November 2025 — this
adapter deliberately does not use it). Targets Google AI Studio's free
tier (Flash / Flash-Lite models) — no credit card required, rate-limited
rather than billed. Worth knowing before sending anything sensitive
through it: free-tier prompts/responses may be used by Google to improve
their models, unlike the paid tier. Fine for audit findings from public
websites; avoid it if that matters for your use case.
"""
from __future__ import annotations

import asyncio

from google import genai
from google.genai import types as genai_types

from app.ai.interfaces import ChatResult, Message
from app.core.exceptions import ProviderError


class GeminiChatProvider:
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def complete(
        self, messages: list[Message], *, model: str, temperature: float = 0.3, max_tokens: int = 2000
    ) -> ChatResult:
        system_instruction = "\n".join(m.content for m in messages if m.role == "system") or None
        contents = [
            genai_types.Content(
                role="model" if m.role == "assistant" else "user", parts=[genai_types.Part(text=m.content)]
            )
            for m in messages
            if m.role != "system"
        ]

        def _call() -> ChatResult:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )
            except Exception as exc:  # SDK raises various google.genai.errors.*
                raise ProviderError(f"Gemini completion failed: {exc}") from exc

            usage = response.usage_metadata
            return ChatResult(
                text=response.text or "",
                model=model,
                input_tokens=usage.prompt_token_count if usage else 0,
                output_tokens=usage.candidates_token_count if usage else 0,
                raw=response.model_dump() if hasattr(response, "model_dump") else {},
            )

        return await asyncio.to_thread(_call)