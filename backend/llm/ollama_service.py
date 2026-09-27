"""Minimal local Ollama generation; no retrieval or HTTP API routes."""

import httpx

from config.settings import settings


class OllamaError(RuntimeError):
    """An actionable failure contacting Ollama or reading its response."""


class OllamaService:
    def __init__(self):
        self.url = settings.OLLAMA_URL.rstrip("/")
        self.model = settings.LLM_MODEL

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")
        try:
            response = httpx.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "think": False},
                timeout=httpx.Timeout(120.0, connect=5.0),
                trust_env=False,
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise OllamaError("Ollama generation timed out. Try again with a shorter prompt.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise OllamaError(f"Ollama model '{self.model}' was not found. Check LLM_MODEL and installed models.") from error
            raise OllamaError(f"Ollama returned HTTP {error.response.status_code}. Check the local Ollama service.") from error
        except httpx.RequestError as error:
            raise OllamaError(f"Cannot reach Ollama at {self.url}. Check that Ollama is running.") from error
        try:
            data = response.json()
            answer = data.get("response") if isinstance(data, dict) else None
            if not isinstance(answer, str) or not answer.strip() or data.get("error") or data.get("done") is not True:
                raise ValueError("Missing or incomplete generated answer")
            return answer.strip()
        except ValueError as error:
            raise OllamaError("Ollama returned an invalid or empty generation response.") from error
