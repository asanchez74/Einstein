"""L'essai OCR ne contacte jamais OpenAI sans activation explicite."""

from pathlib import Path
import runpy
import struct
import sys
import zlib

import pytest


@pytest.fixture
def probe():
    return runpy.run_path(str(Path(__file__).parents[1] / "scripts/ocr-openai-probe.py"))


def test_synthetic_image_dimensions_and_pixels(probe):
    data = probe["synthetic_png"]()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (800, 300)
    pos, compressed = 8, b""
    while pos < len(data):
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        kind, payload = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + size]
        assert struct.unpack(">I", data[pos + 8 + size:pos + 12 + size])[0] == zlib.crc32(kind + payload)
        if kind == b"IDAT":
            compressed += payload
        pos += 12 + size
    pixels = zlib.decompress(compressed)
    assert len(pixels) == 801 * 300
    assert b"\0" in pixels and b"\xff" in pixels


def test_real_call_requires_explicit_flag(probe, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["ocr-openai-probe.py"])
    with pytest.raises(SystemExit) as exc:
        probe["main"]()
    assert exc.value.code == 2


def test_image_only_does_not_load_session(probe, monkeypatch, tmp_path):
    path = tmp_path / "sample.png"
    monkeypatch.setattr(sys, "argv", ["ocr-openai-probe.py", "--write-png", str(path)])
    assert probe["main"]() == 0
    assert path.read_bytes() == probe["synthetic_png"]()
    with pytest.raises(FileExistsError):
        probe["main"]()
