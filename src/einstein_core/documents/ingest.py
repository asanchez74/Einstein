"""Lot documentaire OpenAI explicite ; pas d'appel depuis la recherche HTTP."""

import argparse
import asyncio
import fcntl
import os
from pathlib import Path
import subprocess
import sys

from einstein_core.config import Settings
from einstein_core.documents.cache import cache_key, check_directory, read_cache, validate_transcript, write_cache
from einstein_core.documents.search import IndexBudgetExceeded, build_index


def pdf_pages(data: bytes) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "einstein_core.documents.worker", "--pdf-pages"],
        input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3, check=True,
    )
    return int(result.stdout)


def cached_extractor(root: Path, directory: Path, model: str):
    check_directory(directory)
    def extract(source: str, data: bytes, suffix: str) -> list[dict]:
        if len(data) > 1024 * 1024:
            raise ValueError("Document trop volumineux")
        pages = pdf_pages(data) if suffix == ".pdf" else None
        return read_cache(directory, cache_key(root, source, data, model), pages)
    return extract


def ingest(settings: Settings, provider, max_files: int) -> tuple[int, int, int, bool]:
    directory = settings.documents_cache_path
    if directory is None or not settings.ai_model:
        raise ValueError("Cache et modèle requis")
    check_directory(directory)
    calls = 0
    failures = 0

    def extract(source: str, data: bytes, suffix: str) -> list[dict]:
        nonlocal calls, failures
        if len(data) > 1024 * 1024:
            raise ValueError("Document trop volumineux")
        pages = pdf_pages(data) if suffix == ".pdf" else None
        key = cache_key(settings.documents_path, source, data, settings.ai_model)
        try:
            return read_cache(directory, key, pages)
        except (OSError, ValueError):
            pass
        if calls >= max_files:
            raise IndexBudgetExceeded
        calls += 1
        async def transcribe():
            from einstein_core.ai.provider import ProviderError
            try:
                answer = await provider.transcribe(data=data, suffix=suffix, pages=pages)
                return validate_transcript(answer.text, pages)
            except (ProviderError, ValueError):
                raise ValueError("Transcription indisponible") from None
        try:
            sections = asyncio.run(transcribe())
            write_cache(directory, key, sections)
            return sections
        except ValueError:
            failures += 1
            raise

    # Une seule ingestion pour ce cache ; aucun jeton n'est conservé ici.
    descriptor = os.open(directory / ".ingest.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        index = build_index(settings.documents_path, extractor=extract, budget_seconds=300)
    return calls, failures, index.indexed_files, index.partial


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-real", action="store_true")
    parser.add_argument("--max-files", type=int, default=1, choices=range(1, 11), metavar="1..10")
    args = parser.parse_args(argv)
    if not args.run_real:
        parser.error("--run-real requis : transmet les fichiers choisis à OpenAI")
    settings = Settings()
    if (not settings.documents_enabled or not settings.ai_enabled
            or settings.ai_provider != "chatgpt" or not settings.ai_model
            or not settings.ai_chatgpt_credentials_file):
        print("Traitement refusé : Documents et Plus doivent être configurés et activés.")
        return 1
    from einstein_core.ai.chatgpt_provider import ChatGPTProvider
    provider = ChatGPTProvider(credentials_file=settings.ai_chatgpt_credentials_file,
                               model=settings.ai_model, timeout=settings.ai_timeout_seconds,
                               max_output_chars=65_536)
    try:
        calls, failures, indexed, partial = ingest(settings, provider, args.max_files)
    except (OSError, ValueError):
        print("Traitement indisponible ; vérifier les dossiers, leurs permissions et le verrou.")
        return 1
    finally:
        asyncio.run(provider.close())
    print(f"Appels={calls} échecs_IA={failures} fichiers_exploitables={indexed} partiel={partial}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
