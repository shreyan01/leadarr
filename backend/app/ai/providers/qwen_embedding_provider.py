"""Local embedding provider backed by a Qwen3-Embedding model (a dedicated
embedding architecture — distinct from Qwen2.5-VL, which handles chat and
vision but doesn't expose an embeddings endpoint). Served locally via vLLM
or Ollama with an OpenAI-compatible /v1/embeddings route, so this adapter
is a thin HTTP client, same shape as the chat/vision adapters.
"""
from __future__ import annotations

import httpx

from app.core.exceptions import ProviderError


class QwenEmbeddingProvider:
    def __init__(self, base_url: str, timeout_s: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    async def embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        payload = {"model": model, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(f"{self._base_url}/v1/embeddings", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Qwen embedding request failed: {exc}") from exc

        # OpenAI-compatible /v1/embeddings returns `data` sorted by `index`;
        # sort explicitly rather than trusting response order.
        items = sorted(data["data"], key=lambda item: item["index"])
        return [item["embedding"] for item in items]