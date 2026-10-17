"""Extraction isolée ; entrée binaire bornée, sortie JSON sans journal documentaire."""

from io import BytesIO
import json
import logging
import sys
from xml.etree import ElementTree
from zipfile import ZipFile

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 100_000


def extract(data: bytes, suffix: str) -> list[dict]:
    if suffix in {".txt", ".md"}:
        return [{"text": data.decode("utf-8-sig"), "page": None}]
    if suffix == ".docx":
        with ZipFile(BytesIO(data)) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > 2 * 1024 * 1024:
                raise ValueError
            xml = archive.read(info)
        # Refuser les déclarations DTD, y compris les encodages XML non UTF-8.
        text = xml.decode("utf-8-sig")
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise ValueError
        root = ElementTree.fromstring(text)
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = ["".join(p.itertext()) for p in root.iter(ns + "p")]
        return [{"text": "\n".join(paragraphs), "page": None}]
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted or len(reader.pages) > 50:
            raise ValueError
        sections, length = [], 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            length += len(text)
            if length > MAX_CHARS:
                raise ValueError
            sections.append({"text": text, "page": number})
        return sections
    raise ValueError


def main() -> int:
    # DSM/Linux : plafond virtuel du seul extracteur, pas du serveur HTTP.
    if sys.platform.startswith("linux"):
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024,) * 2)
    logging.disable(logging.CRITICAL)
    try:
        data = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError
        if sys.argv[1] == "--pdf-pages":
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted or not 1 <= len(reader.pages) <= 10:
                raise ValueError
            print(len(reader.pages))
            return 0
        sections = extract(data, sys.argv[1])
        if sum(len(s["text"]) for s in sections) > MAX_CHARS:
            raise ValueError
        print(json.dumps(sections, ensure_ascii=True))
    except Exception:
        # Les messages des parseurs peuvent contenir des extraits privés.
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
