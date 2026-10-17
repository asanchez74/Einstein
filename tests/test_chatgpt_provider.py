"""Flux Plus simulés et renouvellement de session, sans réseau distant."""

import asyncio
import json
import time

import httpx2 as httpx
from openai import AsyncOpenAI
import pytest

from einstein_core.ai import chatgpt_provider, chatgpt_session
from einstein_core.ai.chatgpt_login import ISSUER, save_record, read_record
from einstein_core.ai.provider import ProviderError, ProviderQuotaExceeded


def completed():
    return {"type": "response.completed", "response": {
        "id": "resp_test", "object": "response", "created_at": 0, "status": "completed",
        "model": "test-model", "output": [],
    }}


def run_stream(monkeypatch, events, *, max_chars=1000, status=200):
    def handler(request):
        body = json.loads(request.content)
        assert body["store"] is False and body["stream"] is True
        assert "max_output_tokens" not in body and "previous_response_id" not in body
        assert request.headers["Authorization"] == "Bearer fake-token"
        data = "".join("data: " + json.dumps(event) + "\n\n" for event in events)
        return httpx.Response(status, text=data, headers={"content-type": "text/event-stream"})

    def factory(**kwargs):
        kwargs["http_client"] = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return AsyncOpenAI(**kwargs)

    monkeypatch.setattr(chatgpt_provider, "AsyncOpenAI", factory)
    monkeypatch.setattr(chatgpt_provider, "access_token", lambda path: "fake-token")

    async def run():
        provider = chatgpt_provider.ChatGPTProvider(
            credentials_file=None, model="test-model", timeout=1, max_output_chars=max_chars,
        )
        return await provider.answer(instructions="Réponds en français", context="[]", question="NAS ?")
    return asyncio.run(run())


def test_plus_stream_requires_completed(monkeypatch):
    answer = run_stream(monkeypatch, [
        {"type": "response.output_text.delta", "delta": "Le NAS "},
        {"type": "response.output_text.delta", "delta": "est connu."}, completed(),
    ])
    assert answer.text == "Le NAS est connu."
    assert answer.provider == "chatgpt" and answer.model == "test-model"


@pytest.mark.parametrize("ending", [None, {"type": "response.failed"},
    {"type": "response.incomplete"}, {"type": "error", "message": "private"},
    {"type": "response.refusal.delta", "delta": "private"}])
def test_partial_or_failed_stream_rejected(monkeypatch, ending):
    events = [{"type": "response.output_text.delta", "delta": "partial"}]
    if ending:
        events.append(ending)
    with pytest.raises(ProviderError) as exc:
        run_stream(monkeypatch, events)
    assert "private" not in str(exc.value)


def test_usage_limit_is_distinct_and_private(monkeypatch):
    with pytest.raises(ProviderQuotaExceeded) as exc:
        run_stream(monkeypatch, [{"error": {"code": "subscription_sharing_usage_limit_exceeded",
                                            "type": "invalid_request_error", "message": "private"}}])
    assert "private" not in str(exc.value)
    with pytest.raises(ProviderError) as exc:
        run_stream(monkeypatch, [{"error": {"code": "server_error", "message": "private"}}])
    assert not isinstance(exc.value, ProviderQuotaExceeded)


def test_stream_limit(monkeypatch):
    with pytest.raises(ProviderError, match="trop longue"):
        run_stream(monkeypatch, [{"type": "response.output_text.delta", "delta": "1234"}, completed()], max_chars=3)


def test_empty_stream_rejected(monkeypatch):
    with pytest.raises(ProviderError):
        run_stream(monkeypatch, [completed()])


def session(tmp_path, *, expired=False):
    tmp_path.chmod(0o700)
    path = tmp_path / "credentials.json"
    save_record(path, {
        "issuer": ISSUER, "subject": "account", "client_id": "oaiapp_test",
        "scope": "resource.invoke chatgpt.tokens.use.direct", "access_token": "fake-old",
        "refresh_token": "fake-refresh", "saved_at": time.time() - (4000 if expired else 0),
        "expires_in": 3600,
    })
    return path


def test_fresh_token_no_network(tmp_path):
    assert chatgpt_session.access_token(session(tmp_path)) == "fake-old"


def test_refresh_is_atomic(tmp_path, monkeypatch):
    path = session(tmp_path, expired=True)
    original = httpx.Client
    calls = []

    def handler(request):
        calls.append(request)
        assert "scope=" not in request.content.decode()
        return httpx.Response(200, json={"access_token": "fake-new", "refresh_token": "fake-rotated",
                                        "token_type": "Bearer", "expires_in": 3600})

    monkeypatch.setattr(chatgpt_session.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    assert chatgpt_session.access_token(path) == "fake-new"
    assert read_record(path)["refresh_token"] == "fake-rotated"
    assert chatgpt_session.access_token(path) == "fake-new"
    assert len(calls) == 1 and path.stat().st_mode & 0o777 == 0o600


def test_refresh_failure_keeps_previous_record(tmp_path, monkeypatch):
    path = session(tmp_path, expired=True)
    before = path.read_bytes()
    original = httpx.Client
    monkeypatch.setattr(chatgpt_session.httpx, "Client", lambda **kw: original(
        transport=httpx.MockTransport(lambda req: httpx.Response(401, json={"error": "private"})), **kw))
    with pytest.raises(ProviderError) as exc:
        chatgpt_session.access_token(path)
    assert "private" not in str(exc.value)
    assert path.read_bytes() == before


def test_refresh_lock_prevents_racing_rotation(tmp_path):
    import fcntl
    path = session(tmp_path, expired=True)
    lock_path = tmp_path / ".session.lock"
    lock_path.touch(mode=0o600)
    with lock_path.open("w") as file:
        fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ProviderError):
            chatgpt_session.access_token(path)


def test_chatgpt_configuration_without_api_key(tmp_path):
    from einstein_core.ai.configuration import configure_provider
    from einstein_core.config import Settings
    path = session(tmp_path)
    configured = configure_provider(Settings(
        ai_enabled=True, ai_provider="chatgpt", ai_model="test-model",
        ai_chatgpt_credentials_file=path,
    ))
    assert isinstance(configured, chatgpt_provider.ChatGPTProvider)
    assert configure_provider(Settings(ai_enabled=True, ai_provider="chatgpt", ai_model="test-model")) is None


def test_host_import_preserves_destination_host(tmp_path):
    source_dir = tmp_path / "mac"
    source_dir.mkdir(mode=0o700)
    source = session(source_dir)
    target = tmp_path / "nas"
    chatgpt_session.prepare_host(target)
    host = read_record(target / "host.json")
    chatgpt_session.prepare_host(target, source)
    assert read_record(target / "host.json") == host
    assert read_record(target / "credentials.json")["ext_agent_host_id"] == host["ext_agent_host_id"]
    assert (target / "credentials.json").stat().st_mode & 0o777 == 0o600
    with pytest.raises(chatgpt_session.LoginError):
        chatgpt_session.prepare_host(target, source)


def test_status_reports_expiry_without_tokens(tmp_path, capsys):
    path = session(tmp_path)
    before = path.read_bytes()
    assert chatgpt_session.main(["--directory", str(tmp_path), "--status"]) == 0
    output = capsys.readouterr().out
    assert "valide encore 60 min" in output and "Renouvelable : oui" in output
    assert "fake" not in output and path.read_bytes() == before
    assert not (tmp_path / "host.json").exists()


def test_status_expired_and_missing(tmp_path):
    path = session(tmp_path, expired=True)
    assert "à renouveler (échéance dépassée de 7 min)" in chatgpt_session.session_status(path)
    path.unlink()
    assert chatgpt_session.session_status(path) == "Aucune session enregistrée."


def test_invalid_import_does_not_write_credentials(tmp_path):
    source = tmp_path / "invalid.json"
    save_record(source, {"issuer": ISSUER})
    target = tmp_path / "nas"
    with pytest.raises(chatgpt_session.LoginError):
        chatgpt_session.prepare_host(target, source)
    assert not (target / "credentials.json").exists()
