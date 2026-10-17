"""Tests SDK sur transport simulé : aucun réseau, aucune vraie clé."""

import asyncio
import json

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI
from pydantic import SecretStr

from einstein_core.ai import openai_provider
from einstein_core.ai.provider import ProviderError, ProviderTimeout


def payload(status="completed", text="Le NAS est à 192.168.1.3."):
    return {
        "id": "resp_test", "object": "response", "created_at": 0,
        "status": status, "model": "test-model", "output": [{
            "id": "msg_test", "type": "message", "role": "assistant",
            "status": "completed", "content": [{
                "type": "output_text", "text": text, "annotations": [],
            }],
        }],
    }


def run_provider(monkeypatch, handler, timeout=1):
    def client_factory(**kwargs):
        return AsyncOpenAI(**kwargs, http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ))

    monkeypatch.setattr(openai_provider, "AsyncOpenAI", client_factory)

    async def run():
        provider = openai_provider.OpenAIProvider(
            api_key=SecretStr("fake-test-key"), model="test-model", timeout=timeout,
        )
        try:
            return await provider.answer(
                instructions="Réponds à partir du catalogue uniquement.",
                context='[{"id":"nas"}]', question="Adresse du NAS ?",
            )
        finally:
            await provider.close()

    return asyncio.run(run())


def test_request_is_stateless_and_bounded(monkeypatch):
    def handler(request):
        assert request.url.path == "/v1/responses"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["store"] is False
        assert body["max_output_tokens"] == 512
        assert "tools" not in body and "previous_response_id" not in body
        assert body["input"][0]["role"] == "user"
        assert body["input"][1]["content"] == "Adresse du NAS ?"
        assert '"id":"nas"' in body["input"][0]["content"]
        return httpx.Response(200, json=payload())

    answer = run_provider(monkeypatch, handler)
    assert answer.text == "Le NAS est à 192.168.1.3."
    assert answer.provider == "openai"
    assert answer.model == "test-model"


@pytest.mark.parametrize("status", [401, 429, 500])
def test_remote_errors_are_sanitized_without_retry(monkeypatch, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "private-value"}})

    with pytest.raises(ProviderError) as exc:
        run_provider(monkeypatch, handler)
    assert len(calls) == 1
    assert "private-value" not in str(exc.value)
    assert "fake-test-key" not in str(exc.value)


def test_timeout(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("private-value", request=request)

    with pytest.raises(ProviderTimeout, match="dépassé"):
        run_provider(monkeypatch, handler)


def test_total_deadline(monkeypatch):
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=payload())

    with pytest.raises(ProviderTimeout):
        run_provider(monkeypatch, handler, timeout=0.01)


@pytest.mark.parametrize("status,text", [("incomplete", "partiel"), ("completed", " ")])
def test_unusable_response(monkeypatch, status, text):
    with pytest.raises(ProviderError):
        run_provider(monkeypatch, lambda req: httpx.Response(200, json=payload(status, text)))


def test_refusal(monkeypatch):
    body = payload()
    body["output"][0]["content"] = [{"type": "refusal", "refusal": "private-value"}]
    with pytest.raises(ProviderError, match="inexploitable"):
        run_provider(monkeypatch, lambda req: httpx.Response(200, json=body))


@pytest.mark.parametrize("kwargs", [
    {"model": " "}, {"api_key": SecretStr("")}, {"timeout": 0},
    {"timeout": float("nan")}, {"max_output_tokens": 0},
])
def test_invalid_configuration(kwargs):
    config = {"model": "test-model", "api_key": SecretStr("fake-test-key"), **kwargs}
    with pytest.raises(ValueError):
        openai_provider.OpenAIProvider(**config)
