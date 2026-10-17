"""Cache documentaire privé ; identité du corpus, du fichier et du modèle."""

import hashlib
import json
import os
from pathlib import Path
import tempfile

from pydantic import BaseModel, ConfigDict, Field

VERSION = 1


class PageText(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    page: int | None
    text: str = Field(max_length=65_536)


class Transcript(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    pages: list[PageText] = Field(min_length=1, max_length=10)


def validate_transcript(raw: str, pages: int | None) -> list[dict]:
    result = Transcript.model_validate_json(raw)
    numbers = [item.page for item in result.pages]
    if numbers != (list(range(1, pages + 1)) if pages is not None else [None]):
        raise ValueError("Références de pages invalides")
    if sum(len(item.text) for item in result.pages) > 65_536:
        raise ValueError("Transcription trop longue")
    if not any(item.text.strip() for item in result.pages):
        raise ValueError("Transcription vide")
    return [item.model_dump() for item in result.pages]


def cache_key(root: Path, source: str, data: bytes, model: str) -> str:
    identity = json.dumps([VERSION, str(root.absolute()), source, model, hashlib.sha256(data).hexdigest()])
    return hashlib.sha256(identity.encode()).hexdigest()


def check_directory(directory: Path) -> None:
    # Même politique que le corpus : aucun composant symbolique.
    absolute = directory.absolute()
    if absolute.resolve() != absolute:
        raise ValueError("Dossier cache invalide")
    info = directory.stat()
    if not directory.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Cache privé requis (0700)")


def read_cache(directory: Path, key: str, pages: int | None) -> list[dict]:
    check_directory(directory)
    descriptor = os.open(directory / (key + ".json"), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as file:
        import stat
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Cache non privé")
        raw = file.read(512 * 1024 + 1)
    if len(raw) > 512 * 1024:
        raise ValueError("Cache trop volumineux")
    return validate_transcript(raw.decode("utf-8"), pages)


def write_cache(directory: Path, key: str, sections: list[dict]) -> None:
    check_directory(directory)
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".pending-")
    try:
        with os.fdopen(descriptor, "w") as file:
            json.dump({"pages": sections}, file, ensure_ascii=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, directory / (key + ".json"))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
