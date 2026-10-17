"""Recherche réelle sur fichiers synthétiques, sans réseau ni documents privés."""

from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
import pytest

from einstein_core.config import Settings
from einstein_core.documents.search import build_index
from einstein_core.main import create_app


def pdf_bytes(text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_three_formats_and_relative_references(tmp_path):
    (tmp_path / "notes.md").write_text("Le réseau protège les documents.")
    (tmp_path / "contrat.pdf").write_bytes(pdf_bytes("Contrat assurance maison"))
    with ZipFile(tmp_path / "lettre.docx", "w") as archive:
        archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Assurance habitation</w:t></w:r></w:p></w:body></w:document>')
    index = build_index(tmp_path)
    assert index.indexed_files == 3
    assert not index.partial
    assert index.search("RESEAU", 5).results[0].source == "notes.md"
    hits = index.search("assurance", 5).results
    assert {hit.source for hit in hits} == {"contrat.pdf", "lettre.docx"}
    assert next(hit for hit in hits if hit.source.endswith(".pdf")).page == 1
    assert not index.search("terme absent", 5).results
    assert len(index.search("assurance", 1).results) == 1


def test_links_hidden_files_and_invalid_files(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("secret")
    (root / "link.txt").symlink_to(outside)
    (root / "linked-dir").symlink_to(tmp_path, target_is_directory=True)
    (root / ".hidden.txt").write_text("secret")
    (root / "bad.pdf").write_bytes(b"invalid")
    (root / "binary.txt").write_bytes(b"\xff")
    (root / "good.txt").write_text("public")
    index = build_index(root)
    assert index.indexed_files == 1
    assert index.skipped_files == 2
    assert index.partial
    assert not index.search("secret", 5).results
    linked = tmp_path / "alias"
    linked.symlink_to(root, target_is_directory=True)
    with pytest.raises(OSError):
        build_index(linked)


def test_rejects_oversized_encrypted_and_empty(tmp_path):
    (tmp_path / "large.txt").write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    (tmp_path / "empty.md").write_text("")
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("private")
    writer.write(tmp_path / "encrypted.pdf")
    index = build_index(tmp_path)
    assert index.skipped_files == 3
    assert index.indexed_files == 0


def test_extractor_timeout_is_partial(tmp_path, monkeypatch):
    import subprocess
    from einstein_core.documents import search
    (tmp_path / "slow.txt").write_text("hello")
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("extractor", 3)
    monkeypatch.setattr(search.subprocess, "run", timeout)
    index = build_index(tmp_path)
    assert index.partial and index.skipped_files == 1


def test_document_api_independent_and_snapshot(tmp_path):
    inventory = tmp_path / "inventory.json"
    inventory.write_text("[]")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "test.txt").write_text("Facture chaudière")
    settings = Settings(maison_inventory_path=inventory, documents_enabled=True, documents_path=docs)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/documents/recherche", json={"query": "chaudiere"})
        assert response.status_code == 200
        assert response.json()["results"][0]["source"] == "test.txt"
        (docs / "test.txt").unlink()
        assert client.post("/api/v1/documents/recherche", json={"query": "facture"}).json()["results"]
        assert client.get("/health/ready").status_code == 200
        assert client.post("/api/v1/maison/questions", json={"question": "test"}).status_code == 503
        for payload in ({"query": " "}, {"query": "x", "limit": 21}, {"query": "x", "path": "/etc"}):
            assert client.post("/api/v1/documents/recherche", json=payload).status_code == 422


@pytest.mark.parametrize("enabled", [False, True])
def test_unavailable_documents_preserve_core(tmp_path, enabled):
    inventory = tmp_path / "inventory.json"
    inventory.write_text("[]")
    with TestClient(create_app(Settings(maison_inventory_path=inventory, documents_enabled=enabled,
                                       documents_path=tmp_path / "missing-private-path"))) as client:
        response = client.post("/api/v1/documents/recherche", json={"query": "test"})
        assert response.status_code == 503
        assert "private" not in response.text
        assert client.get("/health/ready").status_code == 200


def test_scan_budget_and_docx_dtd(tmp_path):
    root = tmp_path / "many"
    root.mkdir()
    for number in range(1001):
        (root / f"{number}.unsupported").touch()
    assert build_index(root).partial
    docs = tmp_path / "xml"
    docs.mkdir()
    with ZipFile(docs / "entity.docx", "w") as archive:
        archive.writestr("word/document.xml", '<!DOCTYPE root [<!ENTITY x "private">]><root>&x;</root>')
    index = build_index(docs)
    assert index.skipped_files == 1
    assert not index.passages


def test_pdf_page_limit_and_blank_scan(tmp_path):
    writer = PdfWriter()
    for _ in range(51):
        writer.add_blank_page(width=100, height=100)
    writer.write(tmp_path / "too-many.pdf")
    blank = PdfWriter()
    blank.add_blank_page(width=100, height=100)
    blank.write(tmp_path / "scan.pdf")
    index = build_index(tmp_path)
    assert index.skipped_files == 2
    assert not index.passages
