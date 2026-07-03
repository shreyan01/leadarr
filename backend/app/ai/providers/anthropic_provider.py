from __future__ import annotations

from anthropic import AsyncAnthropic

from app.ai.interfaces import ChatResult, Message
from app.core.exceptions import ProviderError


class AnthropicChatProvider:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self, messages: list[Message], *, model: str, temperature: float = 0.3, max_tokens: int = 2000
    ) -> ChatResult:
        system = "\n".join(m.content for m in messages if m.role == "system") or None
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        try:
            response = await self._client.messages.create(
                model=model,
                system=system,
                messages=turns,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # SDK raises various anthropic.* exceptions
            raise ProviderError(f"Anthropic completion failed: {exc}") from exc

        text = "".join(block.text for block in response.content if block.type == "text")
        return ChatResult(
            text=text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            raw=response.model_dump(),
        )
