import httpx

from app.core.config import get_settings
from app.services.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate_text(self, prompt: str) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        try:
            response = httpx.post(
                url,
                json={
                    "model": self.settings.llm_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.settings.ollama_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("LLM service unavailable") from exc

        payload = response.json()
        text = payload.get("response")
        if not text:
            raise RuntimeError("LLM returned empty response")
        return text
