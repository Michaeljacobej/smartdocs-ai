import httpx
import time

from app.core.config import get_settings
from app.services.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = httpx.Client()

    def generate_text(self, prompt: str) -> str:
        return self._generate(
            prompt=prompt,
            model=self.settings.llm_model,
            num_predict=self.settings.ollama_num_predict,
            num_ctx=self.settings.ollama_num_ctx,
            temperature=self.settings.ollama_temperature,
            timeout_seconds=self.settings.ollama_timeout_seconds,
        )

    def generate_summary_text(self, prompt: str) -> str:
        primary_model = self.settings.llm_summary_model or self.settings.llm_model
        try:
            return self._generate(
                prompt=prompt,
                model=primary_model,
                num_predict=self.settings.ollama_summary_num_predict,
                num_ctx=self.settings.ollama_summary_num_ctx,
                temperature=self.settings.ollama_summary_temperature,
                timeout_seconds=self.settings.ollama_summary_timeout_seconds,
            )
        except RuntimeError:
            fallback_model = self.settings.llm_summary_fallback_model
            if not fallback_model or fallback_model == primary_model:
                raise

            return self._generate(
                prompt=prompt,
                model=fallback_model,
                num_predict=self.settings.ollama_summary_num_predict,
                num_ctx=self.settings.ollama_summary_num_ctx,
                temperature=self.settings.ollama_summary_temperature,
                timeout_seconds=self.settings.ollama_summary_timeout_seconds,
            )

    def _generate(
        self,
        prompt: str,
        model: str,
        num_predict: int,
        num_ctx: int,
        temperature: float,
        timeout_seconds: float,
    ) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": self.settings.ollama_think,
            "keep_alive": self.settings.ollama_keep_alive,
            "options": {
                "num_predict": num_predict,
                "num_ctx": num_ctx,
                "temperature": temperature,
            },
        }

        attempts = max(self.settings.ollama_retry_attempts, 1)
        backoff = max(self.settings.ollama_retry_backoff_seconds, 0.0)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self.client.post(url, json=payload, timeout=timeout_seconds)
                response.raise_for_status()
                payload_json = response.json()
                text = payload_json.get("response")
                if not text:
                    raise RuntimeError("LLM returned empty response")
                return text
            except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt < attempts and backoff > 0:
                    time.sleep(backoff * attempt)

        raise RuntimeError("LLM service unavailable") from last_error
