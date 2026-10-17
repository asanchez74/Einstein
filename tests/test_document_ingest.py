"""Transcription simulée, cache privé et recherche sans appel fournisseur."""

import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
import httpx2 as httpx
from openai import AsyncOpenAI
from pypdf import PdfWriter
import pytest

from einstein_core.ai import chatgpt_provider
from einstein_core.ai.provider import Answer, ProviderError
from einstein_core.config import Settings
from einstein_core.documents.cache import cache_key, read_cache, validate_transcript
from einstein_core.documents.ingest import cached_extractor, ingest, main
from einstein_core.documents.search import build_index
from einstein_core.main import create_app


class FakeTranscriber:
    def __init__(self, raw=None):
        self.calls = []
        self.raw = raw

    async def transcribe(self, **kwargs):
        self.calls.append(kwargs)
        raw = self.raw if self.raw is not None else json.dumps({"pages": [{"page": number, "text": "Facture chaudière"} for number in (range(1, kwargs["pages"] + 1) if kwargs["pages"] else [None])]})
        return Answer(raw, "chatgpt", "test")


@pytest.fixture
def corpus(tmp_path):
    root, cache = tmp_path / "docs", tmp_path / "cache"
    root.mkdir()
    cache.mkdir(mode=0o700)
    return Settings(documents_enabled=True, documents_path=root, documents_mode="openai",
                    documents_cache_path=cache, ai_model="test")


def test_ingest_reuses_cache_and_invalidates_source_model(corpus):
    path = corpus.documents_path / "note.txt"
    path.write_text("Document test")
    provider = FakeTranscriber()
    assert ingest(corpus, provider, 1)[:3] == (1, 0, 1)
    assert ingest(corpus, provider, 1)[:3] == (0, 0, 1)
    key = cache_key(corpus.documents_path, "note.txt", path.read_bytes(), "test")
    assert (corpus.documents_cache_path / (key + ".json")).stat().st_mode & 0o777 == 0o600
    index = build_index(corpus.documents_path, extractor=cached_extractor(corpus.documents_path, corpus.documents_cache_path, "test"))
    assert index.search("chaudiere", 5).results[0].source == "note.txt"
    path.write_text("Version modifiée")
    assert ingest(corpus, provider, 1)[0] == 1
    assert ingest(corpus.model_copy(update={"ai_model": "other"}), provider, 1)[0] == 1
    path.unlink()
    index = build_index(corpus.documents_path, extractor=cached_extractor(corpus.documents_path, corpus.documents_cache_path, "test"))
    assert not index.passages
    assert len(provider.calls) == 3


def test_new_call_budget_progresses_through_cache(corpus):
    for name in ("a.txt", "b.txt", "c.txt"):
        (corpus.documents_path / name).write_text("test")
    provider = FakeTranscriber()
    assert ingest(corpus, provider, 1)[0] == 1
    assert ingest(corpus, provider, 1)[0] == 1
    assert ingest(corpus, provider, 1)[0] == 1
    assert ingest(corpus, provider, 1)[0] == 0
    assert len(provider.calls) == 3


def test_pdf_page_validation_and_size_before_call(corpus):
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(corpus.documents_path / "scan.pdf")
    (corpus.documents_path / "huge.txt").write_bytes(b"x" * (1024 * 1024 + 1))
    provider = FakeTranscriber()
    result = ingest(corpus, provider, 2)
    assert result[0] == 1 and result[3]
    assert provider.calls[0]["pages"] == 1


@pytest.mark.parametrize("raw", ['{}', 'not-json', '{"pages":[{"page":1,"text":"wrong"}]}', '{"pages":[{"page":null,"text":""}]}'])
def test_invalid_transcript_never_cached(corpus, raw):
    (corpus.documents_path / "note.txt").write_text("test")
    assert ingest(corpus, FakeTranscriber(raw), 1)[1] == 1
    assert not list(corpus.documents_cache_path.glob("*.json"))


def test_cache_only_api_never_calls_provider(corpus, tmp_path):
    (corpus.documents_path / "note.txt").write_text("test")
    inventory = tmp_path / "inventory.json"
    inventory.write_text("[]")
    settings = corpus.model_copy(update={"maison_inventory_path": inventory})
    with TestClient(create_app(settings)) as client:
        result = client.post("/api/v1/documents/recherche", json={"query": "test"})
        assert result.status_code == 200
        assert result.json()["partial"]
        assert result.json()["results"] == []
    ingest(corpus, FakeTranscriber(), 1)
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/documents/recherche", json={"query": "facture"}).json()["results"]


def test_private_cache_and_symlink_refused(corpus, tmp_path):
    corpus.documents_cache_path.chmod(0o755)
    with pytest.raises(ValueError):
        cached_extractor(corpus.documents_path, corpus.documents_cache_path, "test")
    corpus.documents_cache_path.chmod(0o700)
    path = corpus.documents_cache_path / ("a" * 64 + ".json")
    target = tmp_path / "outside"
    target.write_text("private")
    path.symlink_to(target)
    with pytest.raises(OSError):
        read_cache(corpus.documents_cache_path, "a" * 64, None)


def test_ingestion_lock_and_explicit_activation(corpus):
    import fcntl
    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2
    with (corpus.documents_cache_path / ".ingest.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(OSError):
            ingest(corpus, FakeTranscriber(), 1)


@pytest.mark.parametrize("suffix", [".pdf", ".docx", ".txt", ".md"])
def test_transcription_request_uses_streaming_without_upload(monkeypatch, suffix):
    captured = []
    def handler(request):
        assert request.url.path == "/v1/responses"
        body = json.loads(request.content)
        captured.append(body)
        assert body["store"] is False and body["stream"] is True
        assert "max_output_tokens" not in body
        content = body["input"][0]["content"][0]
        assert content["type"] == ("input_text" if suffix in {".txt", ".md"} else "input_file")
        events = [{"type": "response.output_text.delta", "delta": '{"pages":[{"page":null,"text":"test"}]}'},
                  {"type": "response.completed", "response": {"id": "resp_test", "object": "response", "created_at": 0, "status": "completed", "model": "test", "output": []}}]
        return httpx.Response(200, text="".join("data: " + json.dumps(event) + "\n\n" for event in events), headers={"content-type": "text/event-stream"})
    def factory(**kwargs):
        kwargs["http_client"] = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return AsyncOpenAI(**kwargs)
    monkeypatch.setattr(chatgpt_provider, "AsyncOpenAI", factory)
    monkeypatch.setattr(chatgpt_provider, "access_token", lambda _: "fake")
    provider = chatgpt_provider.ChatGPTProvider(credentials_file=Path("unused"), model="test", timeout=1, max_output_chars=1000)
    answer = asyncio.run(provider.transcribe(data=b"test", suffix=suffix, pages=None))
    assert answer.provider == "chatgpt" and len(captured) == 1


def test_pdf_transcript_requires_every_page_in_order():
    with pytest.raises(ValueError):
        validate_transcript('{"pages":[{"page":2,"text":"test"}]}', 2)
