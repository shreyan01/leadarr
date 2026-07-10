from app.ai.providers.openai_provider import OpenAIChatProvider


def test_openai_provider_initializes_with_compatible_httpx() -> None:
    provider = OpenAIChatProvider("test-key", base_url="http://localhost:11434/v1")

    assert provider is not None
