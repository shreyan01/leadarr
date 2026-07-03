from __future__ import annotations

import base64
import json

import httpx

from app.ai.interfaces import VisionResult
from app.core.exceptions import ProviderError


class QwenVLProvider:
    """Talks to a locally hosted Qwen2.5-VL server exposing an
    OpenAI-compatible ``/v1/chat/completions`` endpoint with image input."""

    def __init__(self, base_url: str, timeout_s: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    async def analyze_image(
        self, image_bytes: bytes, prompt: str, *, model: str, media_type: str = "image/png"
    ) -> VisionResult:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                    ],
                }
            ],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(f"{self._base_url}/v1/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Qwen2.5-VL request failed: {exc}") from exc

        content = data["choices"][0]["message"]["content"]
        try:
            structured = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError("Qwen2.5-VL did not return valid JSON for the vision prompt.") from exc

        usage = data.get("usage", {})
        return VisionResult(
            structured=structured,
            model=data.get("model", model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            raw=data,
        )
