"""OCR local : faux moteur pour la logique, vrais binaires seulement s'ils sont installés."""

from io import BytesIO
import shutil
import subprocess
import zlib

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject, StreamObject
import pytest

from einstein_core.config import Settings
from einstein_core.documents import ocr
from einstein_core.documents.search import build_index
from tests.test_documents import pdf_bytes


def blank_pdf(pages=2):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=200)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def corpus(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    cache = tmp_path / "ocr-cache"
    cache.mkdir(mode=0o700)
    (docs / "scan.pdf").write_bytes(blank_pdf())
    (docs / "texte.pdf").write_bytes(pdf_bytes("Contrat assurance maison"))
    return Settings(documents_path=docs, documents_ocr_cache_path=cache)


def fake_ocr(calls):
    def page_ocr(descriptor, number, workdir):
        calls.append(number)
        return f"Directive  secret\nbancaire page {number}"
    return page_ocr


def test_scanned_pages_are_recognized_cached_and_searchable(corpus):
    calls = []
    counts = ocr.run(corpus, 5, 60, page_ocr=fake_ocr(calls), engine=lambda: "tesseract test")
    assert counts["reconnus"] == 1 and counts["pages_reconnues"] == 2 and counts["sans_besoin"] == 1
    assert calls == [1, 2]
    entries = list(corpus.documents_ocr_cache_path.glob("*.json"))
    assert len(entries) == 1 and entries[0].stat().st_mode & 0o777 == 0o600

    lookup = ocr.cached_ocr(corpus.documents_path, corpus.documents_ocr_cache_path)
    index = build_index(corpus.documents_path, ocr=lookup)
    assert index.indexed_files == 2 and index.skipped_files == 0
    hit = index.search("secret bancaire", 5).results[0]
    assert hit.source == "scan.pdf" and hit.ocr and hit.page == 1
    assert not index.search("assurance", 5).results[0].ocr

    without_cache = build_index(corpus.documents_path)
    assert without_cache.indexed_files == 1 and without_cache.skipped_files == 1


def test_cache_reused_until_file_or_engine_changes(corpus):
    calls = []
    ocr.run(corpus, 5, 60, page_ocr=fake_ocr(calls), engine=lambda: "v1")
    assert ocr.run(corpus, 5, 60, page_ocr=fake_ocr(calls), engine=lambda: "v1")["deja_en_cache"] == 1
    assert calls == [1, 2]
    ocr.run(corpus, 5, 60, page_ocr=fake_ocr(calls), engine=lambda: "v2")
    assert calls == [1, 2, 1, 2]
    (corpus.documents_path / "scan.pdf").write_bytes(blank_pdf(pages=1))
    lookup = ocr.cached_ocr(corpus.documents_path, corpus.documents_ocr_cache_path)
    assert build_index(corpus.documents_path, ocr=lookup).skipped_files == 1


def test_file_budget_failures_and_private_cache(corpus):
    (corpus.documents_path / "autre.pdf").write_bytes(blank_pdf(pages=1))
    counts = ocr.run(corpus, 1, 60, page_ocr=fake_ocr([]), engine=lambda: "v1")
    assert counts["reconnus"] == 1 and counts["partiel"]

    def broken(descriptor, number, workdir):
        raise subprocess.CalledProcessError(1, "tesseract", output=b"private")
    counts = ocr.run(corpus, 5, 60, page_ocr=broken, engine=lambda: "v1")
    assert counts["echecs"] == 1 and counts["deja_en_cache"] == 1

    corpus.documents_ocr_cache_path.chmod(0o755)
    with pytest.raises(ValueError):
        ocr.run(corpus, 1, 60, page_ocr=fake_ocr([]), engine=lambda: "v1")


def test_invalid_cache_entries_are_ignored(corpus):
    ocr.run(corpus, 5, 60, page_ocr=fake_ocr([]), engine=lambda: "v1")
    entry = next(corpus.documents_ocr_cache_path.glob("*.json"))
    entry.write_text('{"engine": "v1", "pages": [{"page": 2, "text": "x", "ocr": true}]}')
    lookup = ocr.cached_ocr(corpus.documents_path, corpus.documents_ocr_cache_path)
    assert build_index(corpus.documents_path, ocr=lookup).skipped_files == 1


def image_only_pdf(text):
    """PDF dont l'unique page est une image : rendu d'un PDF texte par pdftoppm."""
    pgm = subprocess.run(["pdftoppm", "-r", "150", "-gray", "-singlefile", "-", "-"],
                         input=pdf_bytes(text), stdout=subprocess.PIPE, check=True).stdout
    magic, width, height, maxval, pixels = pgm.split(maxsplit=4)
    assert magic == b"P5" and maxval == b"255"
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    image = StreamObject()
    image._data = zlib.compress(pixels)
    image.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                  NameObject("/Width"): NumberObject(int(width)), NameObject("/Height"): NumberObject(int(height)),
                  NameObject("/ColorSpace"): NameObject("/DeviceGray"),
                  NameObject("/BitsPerComponent"): NumberObject(8), NameObject("/Filter"): NameObject("/FlateDecode")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject(
        {NameObject("/Im1"): writer._add_object(image)})})
    content = DecodedStreamObject()
    content.set_data(b"q 300 0 0 200 0 0 cm /Im1 Do Q")
    page[NameObject("/Contents")] = writer._add_object(content)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.skipif(not (shutil.which("pdftoppm") and shutil.which("tesseract")), reason="binaires OCR absents")
def test_real_tesseract_reads_image_only_pdf(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir(mode=0o700)
    (docs / "scan.pdf").write_bytes(image_only_pdf("CONTRAT ASSURANCE HABITATION"))
    assert build_index(docs).skipped_files == 1
    counts = ocr.run(Settings(documents_path=docs, documents_ocr_cache_path=cache), 1, 300)
    assert counts["reconnus"] == 1, counts
    index = build_index(docs, ocr=ocr.cached_ocr(docs, cache))
    assert index.search("assurance habitation", 5).results[0].ocr
