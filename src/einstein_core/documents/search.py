"""Instantané borné en mémoire, recherche lexicale avec références relatives."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import unicodedata

from pydantic import BaseModel

from einstein_core.documents.worker import max_bytes


class SearchHit(BaseModel):
    source: str
    page: int | None
    passage: int
    excerpt: str
    score: int
    ocr: bool = False


class SearchResult(BaseModel):
    indexed_at: str
    indexed_files: int
    skipped_files: int
    partial: bool
    results: list[SearchHit]


def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.casefold())
                   if not unicodedata.combining(c))


@dataclass(frozen=True)
class DocumentIndex:
    passages: tuple[SearchHit, ...]
    indexed_at: str
    indexed_files: int
    skipped_files: int
    partial: bool

    def search(self, query: str, limit: int) -> SearchResult:
        terms = set(re.findall(r"\w+", normalize(query)))
        hits = []
        if terms:
            for passage in self.passages:
                words = re.findall(r"\w+", normalize(passage.excerpt))
                vocabulary = set(words)
                if terms.issubset(vocabulary):
                    score = sum(words.count(term) for term in terms)
                    hits.append(passage.model_copy(update={"score": score}))
        hits.sort(key=lambda item: (-item.score, item.source, item.passage))
        # Un résultat par document : son meilleur passage, pour éviter qu'un long fichier occupe toute la liste.
        best, seen = [], set()
        for hit in hits:
            if hit.source not in seen:
                seen.add(hit.source)
                best.append(hit)
        return SearchResult(indexed_at=self.indexed_at, indexed_files=self.indexed_files,
                            skipped_files=self.skipped_files, partial=self.partial,
                            results=best[:limit])


class IndexBudgetExceeded(Exception):
    """Arrêt explicite d'un lot, sans traiter les fichiers suivants."""


def build_index(root: Path, *, extractor: Callable | None = None, budget_seconds: int = 30,
                stop: threading.Event | None = None, ocr: Callable | None = None) -> DocumentIndex:
    passages, indexed, skipped, visited, chars = [], 0, 0, 0, 0
    partial = False
    deadline = time.monotonic() + budget_seconds

    def visit(directory: int, prefix: str, depth: int) -> None:
        nonlocal indexed, skipped, visited, chars, partial
        with os.scandir(directory) as entries:
            for entry in entries:
                if (visited >= 1000 or indexed + skipped >= 100 or time.monotonic() >= deadline
                        or (stop is not None and stop.is_set())):
                    partial = True
                    return
                visited += 1
                name = entry.name
                if name.startswith(".") or entry.is_symlink():
                    continue
                source = prefix + name
                if entry.is_dir(follow_symlinks=False):
                    if depth >= 8:
                        partial = True
                        continue
                    try:
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                        try:
                            visit(child, source + "/", depth + 1)
                        finally:
                            os.close(child)
                    except OSError:
                        partial = True
                    continue
                suffix = Path(name).suffix.lower()
                if suffix not in {".pdf", ".docx", ".txt", ".md"}:
                    continue
                try:
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                    with os.fdopen(fd, "rb") as file:
                        info = os.fstat(file.fileno())
                        if not stat.S_ISREG(info.st_mode):
                            raise ValueError
                        sections = None
                        try:
                            limit = max_bytes(suffix)
                            if info.st_size > limit:
                                raise ValueError
                            data = file.read(limit + 1)
                            if len(data) > limit:
                                raise ValueError
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                raise ValueError
                            if extractor is None:
                                result = subprocess.run(
                                    [sys.executable, "-m", "einstein_core.documents.worker", suffix],
                                    input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    timeout=min(10, remaining), check=True,
                                )
                                sections = json.loads(result.stdout)
                            else:
                                sections = extractor(source, data, suffix)
                        except (ValueError, subprocess.SubprocessError):
                            if ocr is None or suffix != ".pdf":
                                raise
                        # PDF illisible, trop gros ou avec des pages sans texte : texte OCR en cache s'il existe.
                        if ocr is not None and suffix == ".pdf" and (
                                sections is None or any(not section["text"].strip() for section in sections)):
                            sections = ocr(source, file) or sections
                        if sections is None:
                            raise ValueError
                    new = []
                    for section in sections:
                        text = " ".join(section["text"].split())
                        for offset in range(0, len(text), 600):
                            new.append(SearchHit(source=source, page=section["page"],
                                                 passage=len(new) + 1, excerpt=text[offset:offset + 800],
                                                 score=0, ocr=bool(section.get("ocr", False))))
                    size = sum(len(item.excerpt) for item in new)
                    if not new or chars + size > 3_000_000:
                        raise ValueError
                    passages.extend(new)
                    chars += size
                    indexed += 1
                except (OSError, ValueError, subprocess.SubprocessError):
                    skipped += 1
                    partial = True

    # Refuser aussi un lien dans les composants du chemin configuré.
    absolute = root.absolute()
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        try:
            visit(descriptor, "", 0)
        except IndexBudgetExceeded:
            partial = True
    finally:
        os.close(descriptor)
    return DocumentIndex(tuple(passages), datetime.now(timezone.utc).isoformat(), indexed, skipped, partial)
