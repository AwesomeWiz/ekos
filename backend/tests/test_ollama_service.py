from unittest.mock import patch

import httpx
import pytest

from config.settings import settings
from llm.ollama_service import OllamaError, OllamaService


def test_generation_uses_config_and_returns_only_answer(monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_URL", "http://localhost:11434/")
    monkeypatch.setattr(settings, "LLM_MODEL", "qwen3:1.7b")
    response = httpx.Response(200, json={"response": "  Hello!  ", "thinking": "internal", "done": True}, request=httpx.Request("POST", "http://localhost:11434/api/generate"))
    with patch("llm.ollama_service.httpx.post", return_value=response) as post:
        assert OllamaService().generate("Say hello") == "Hello!"
    assert post.call_args.args == ("http://localhost:11434/api/generate",)
    assert post.call_args.kwargs["json"] == {"model": "qwen3:1.7b", "prompt": "Say hello", "stream": False, "think": False}


@pytest.mark.parametrize("prompt", ["", "  ", None])
def test_empty_prompt_is_rejected_without_contacting_ollama(prompt):
    with patch("llm.ollama_service.httpx.post") as post:
        with pytest.raises(ValueError):
            OllamaService().generate(prompt)
        post.assert_not_called()


@pytest.mark.parametrize("error,message", [(httpx.ConnectError("offline"), "Cannot reach Ollama"), (httpx.ReadTimeout("slow"), "timed out")])
def test_connection_errors_are_actionable(error, message):
    with patch("llm.ollama_service.httpx.post", side_effect=error):
        with pytest.raises(OllamaError, match=message):
            OllamaService().generate("Hello")


@pytest.mark.parametrize("code,message", [(404, "was not found"), (500, "HTTP 500")])
def test_http_errors_are_actionable(code, message):
    response = httpx.Response(code, request=httpx.Request("POST", "http://localhost:11434/api/generate"))
    with patch("llm.ollama_service.httpx.post", return_value=response):
        with pytest.raises(OllamaError, match=message):
            OllamaService().generate("Hello")


@pytest.mark.parametrize("payload", [{}, {"response": ""}, {"response": 123}, {"response": "partial", "done": False}, {"response": "answer", "done": True, "error": "failed"}, []])
def test_invalid_responses_are_rejected(payload):
    response = httpx.Response(200, json=payload, request=httpx.Request("POST", "http://localhost:11434/api/generate"))
    with patch("llm.ollama_service.httpx.post", return_value=response):
        with pytest.raises(OllamaError, match="invalid or empty"):
            OllamaService().generate("Hello")


def test_invalid_json_is_rejected():
    response = httpx.Response(200, text="not json", request=httpx.Request("POST", "http://localhost:11434/api/generate"))
    with patch("llm.ollama_service.httpx.post", return_value=response):
        with pytest.raises(OllamaError, match="invalid or empty"):
            OllamaService().generate("Hello")
