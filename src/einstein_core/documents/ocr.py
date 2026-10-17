"""OCR local explicite des PDF scannés ; aucun réseau, jamais depuis une requête HTTP."""

import argparse
from collections.abc import Callable, Iterator
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time

from pydantic import BaseModel, ConfigDict, Field

from einstein_core.config import Settings
from einstein_core.documents.cache import check_directory, read_private, write_private
from einstein_core.documents import worker
from einstein_core.documents.worker import page_text

VERSION = 1
LANGUAGE = "fra"
DPI = 300
MAX_BYTES = 50 * 1024 * 1024
MAX_PAGES = 80
MAX_CHARS = 400_000
MAX_CACHE_BYTES = 4 * 1024 * 1024
PAGE_TIMEOUT = 120


class OcrPage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    page: int = Field(ge=1, le=MAX_PAGES)
    text: str
    ocr: bool


class OcrDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    engine: str = Field(min_length=1, max_length=200)
    pages: list[OcrPage] = Field(min_length=1, max_length=MAX_PAGES)


def validate(raw: str) -> OcrDocument:
    document = OcrDocument.model_validate_json(raw)
    if [item.page for item in document.pages] != list(range(1, len(document.pages) + 1)):
        raise ValueError("Pages OCR invalides")
    if sum(len(item.text) for item in document.pages) > MAX_CHARS:
        raise ValueError("Texte OCR trop long")
    return document


def ocr_key(root: Path, source: str, digest: str) -> str:
    # La version du moteur est enregistrée dans l'entrée : le Core n'exécute pas Tesseract.
    identity = json.dumps(["ocr", VERSION, str(root.absolute()), source, digest, LANGUAGE, DPI])
    return hashlib.sha256(identity.encode()).hexdigest()


def file_digest(file) -> str:
    digest, total = hashlib.sha256(), 0
    while chunk := file.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_BYTES:
            raise ValueError("Fichier trop volumineux pour l'OCR")
        digest.update(chunk)
    return digest.hexdigest()


def cached_ocr(root: Path, directory: Path) -> Callable:
    """Lecture seule du cache pour le Core : aucun binaire OCR n'est lancé."""
    check_directory(directory)

    def lookup(source: str, file) -> list[dict] | None:
        try:
            file.seek(0)
            document = validate(read_private(directory, ocr_key(root, source, file_digest(file)), MAX_CACHE_BYTES))
            return [item.model_dump() for item in document.pages]
        except (OSError, ValueError):
            return None
    return lookup


def tesseract_version() -> str:
    result = subprocess.run(["tesseract", "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=10, check=True)
    return result.stdout.decode("utf-8", "replace").splitlines()[0].strip()


def ocr_page(descriptor: int, number: int, workdir: str) -> str:
    """Rendu d'une page puis reconnaissance ; sorties d'erreur ignorées (contenu possible)."""
    deadline = time.monotonic() + PAGE_TIMEOUT
    prefix = os.path.join(workdir, "page")
    subprocess.run(
        ["pdftoppm", "-f", str(number), "-l", str(number), "-r", str(DPI), "-gray", "-png",
         "-singlefile", f"/dev/fd/{descriptor}", prefix],
        pass_fds=(descriptor,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=PAGE_TIMEOUT, check=True,
    )
    try:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired("tesseract", PAGE_TIMEOUT)
        result = subprocess.run(["tesseract", prefix + ".png", "stdout", "-l", LANGUAGE],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=remaining, check=True)
    finally:
        if os.path.exists(prefix + ".png"):
            os.unlink(prefix + ".png")
    return result.stdout.decode("utf-8", "replace")


def scan_document(file, recognize: Callable[[int], str], *, oversized: bool = False) -> list[dict] | None:
    """Pages avec texte conservées ; pages sans texte reconnues.

    None si aucune page n'a besoin d'OCR et que l'extracteur ordinaire accepte le fichier.
    """
    from pypdf import PdfReader

    file.seek(0)
    reader = PdfReader(file, strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
        raise ValueError("PDF chiffré ou hors plafond de pages")
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = " ".join(page_text(page).split())
        pages.append({"page": number, "text": text, "ocr": not text})
    if not any(item["ocr"] for item in pages):
        # Trop grand pour l'extracteur ordinaire : le texte est mis en cache sans OCR.
        beyond = (oversized or len(pages) > worker.MAX_PAGES
                  or sum(len(item["text"]) for item in pages) > worker.MAX_CHARS)
        if not beyond or sum(len(item["text"]) for item in pages) > MAX_CHARS:
            return None
        return pages
    for item in pages:
        if item["ocr"]:
            item["text"] = " ".join(recognize(item["page"]).split())
    if sum(len(item["text"]) for item in pages) > MAX_CHARS:
        raise ValueError("Texte OCR trop long")
    return pages


def iter_pdfs(root: Path) -> Iterator[tuple[str, Path]]:
    """Mêmes règles de visibilité que l'index : ni caché, ni lien, profondeur 8, 1000 entrées."""
    visited = 0

    def walk(directory: Path, prefix: str, depth: int) -> Iterator[tuple[str, Path]]:
        nonlocal visited
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            if visited >= 1000:
                return
            visited += 1
            if entry.name.startswith(".") or entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                if depth < 8:
                    yield from walk(Path(entry.path), prefix + entry.name + "/", depth + 1)
            elif entry.name.lower().endswith(".pdf"):
                yield prefix + entry.name, Path(entry.path)

    yield from walk(root, "", 0)


def run(settings: Settings, max_files: int, max_seconds: int, *,
        page_ocr: Callable[[int, int, str], str] | None = None,
        engine: Callable[[], str] | None = None) -> dict[str, int | bool]:
    page_ocr = page_ocr or ocr_page
    engine = engine or tesseract_version
    directory = settings.documents_ocr_cache_path
    if directory is None:
        raise ValueError("Cache OCR requis")
    check_directory(directory)
    root = settings.documents_path
    version = engine()
    counts: dict[str, int | bool] = {"reconnus": 0, "pages_reconnues": 0, "deja_en_cache": 0,
                                     "texte_seul": 0, "sans_besoin": 0, "ecartes": 0, "echecs": 0,
                                     "partiel": False}
    deadline = time.monotonic() + max_seconds
    descriptor = os.open(directory / ".ocr.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for source, path in iter_pdfs(root):
            if counts["reconnus"] >= max_files or time.monotonic() >= deadline:
                counts["partiel"] = True
                break
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except OSError:
                counts["ecartes"] += 1
                continue
            with os.fdopen(fd, "rb") as file:
                info = os.fstat(file.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                    counts["ecartes"] += 1
                    continue
                key = ocr_key(root, source, file_digest(file))
                try:
                    if validate(read_private(directory, key, MAX_CACHE_BYTES)).engine == version:
                        counts["deja_en_cache"] += 1
                        continue
                except (OSError, ValueError):
                    pass
                try:
                    with tempfile.TemporaryDirectory(prefix="einstein-ocr-") as workdir:
                        pages = scan_document(file, lambda number: page_ocr(file.fileno(), number, workdir),
                                              oversized=info.st_size > worker.MAX_BYTES)
                except Exception:
                    # Parseurs et binaires sur fichiers non fiables : aucun message n'est affiché.
                    counts["echecs"] += 1
                    continue
                if pages is None:
                    counts["sans_besoin"] += 1
                    continue
                write_private(directory, key, {"engine": version, "pages": pages})
                recognized = sum(item["ocr"] for item in pages)
                counts["reconnus" if recognized else "texte_seul"] += 1
                counts["pages_reconnues"] += recognized
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-files", type=int, default=1, choices=range(1, 201), metavar="1..200")
    parser.add_argument("--max-minutes", type=int, default=60, choices=range(1, 601), metavar="1..600")
    args = parser.parse_args(argv)
    # Les avertissements des parseurs PDF peuvent citer des éléments des documents.
    logging.disable(logging.CRITICAL)
    try:
        counts = run(Settings(), args.max_files, args.max_minutes * 60)
    except (OSError, ValueError, subprocess.SubprocessError):
        print("OCR indisponible ; vérifier le cache, ses permissions, le verrou et les binaires.")
        return 1
    print(" ".join(f"{name}={value}" for name, value in counts.items()))
    return 1 if counts["echecs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
