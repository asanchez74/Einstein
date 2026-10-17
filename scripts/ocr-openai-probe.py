#!/usr/bin/env python3
"""Essai vision Plus sur une image synthétique ; aucun document utilisateur lu."""

import argparse
import asyncio
import base64
import struct
import zlib

# Police matricielle minimale, suffisante pour une page synthétique reproductible.
FONT = {
    "0": "01110 10001 10011 10101 11001 10001 01110",
    "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111",
    "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010",
    "5": "11111 10000 10000 11110 00001 00001 11110",
    "6": "01110 10000 10000 11110 10001 10001 01110",
    "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110",
    "9": "01110 10001 10001 01111 00001 00001 01110",
    "A": "01110 10001 10001 11111 10001 10001 10001",
    "C": "01111 10000 10000 10000 10000 10000 01111",
    "E": "11111 10000 10000 11110 10000 10000 11111",
    "F": "11111 10000 10000 11110 10000 10000 10000",
    "H": "10001 10001 10001 11111 10001 10001 10001",
    "L": "10000 10000 10000 10000 10000 10000 11111",
    "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110",
    "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110",
    "T": "11111 00100 00100 00100 00100 00100 00100",
    ".": "00000 00000 00000 00000 00000 00110 00110",
    " ": "00000 00000 00000 00000 00000 00000 00000",
}
LINES = ("TEST OCR", "NAS 192.168.1.3", "TOTAL 123.45 CHF")


def synthetic_png() -> bytes:
    width, height, scale = 800, 300, 6
    pixels = bytearray(b"\xff" * width * height)
    for line_number, line in enumerate(LINES):
        for column, char in enumerate(line):
            for y, row in enumerate(FONT[char].split()):
                for x, value in enumerate(row):
                    if value == "1":
                        for dy in range(scale):
                            start = (30 + line_number * 80 + y * scale + dy) * width + 30 + column * 6 * scale + x * scale
                            pixels[start:start + scale] = b"\0" * scale
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"".join(b"\0" + pixels[y * width:(y + 1) * width] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


async def run() -> int:
    import httpx2 as httpx
    from openai import APIError, AsyncOpenAI
    from einstein_core.ai.chatgpt_session import access_token
    from einstein_core.ai.provider import ProviderError
    from einstein_core.config import Settings

    settings = Settings()
    if settings.ai_provider != "chatgpt" or not settings.ai_chatgpt_credentials_file or not settings.ai_model:
        print("Essai refusé : session Plus et modèle explicite requis.")
        return 1
    try:
        async with asyncio.timeout(60):
            token = await asyncio.to_thread(access_token, settings.ai_chatgpt_credentials_file)
            async with AsyncOpenAI(api_key=token, base_url="https://api.openai.com/v1",
                                   max_retries=0, timeout=60,
                                   http_client=httpx.AsyncClient(trust_env=False)) as client:
                stream = await client.responses.create(
                    model=settings.ai_model, store=False, stream=True,
                    instructions="Transcris fidèlement le texte de l'image, ligne par ligne. Ne résume pas et n'ajoute rien.",
                    input=[{"role": "user", "content": [
                        {"type": "input_text", "text": "Transcris cette page."},
                        {"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(synthetic_png()).decode(), "detail": "high"},
                    ]}],
                )
                parts, completed, size = [], False, 0
                async with stream:
                    async for event in stream:
                        if event.type == "response.output_text.delta":
                            size += len(event.delta)
                            if size > 2000:
                                raise ProviderError("Sortie trop longue")
                            parts.append(event.delta)
                        elif event.type in {"response.failed", "response.incomplete", "error", "response.refusal.delta", "response.refusal.done"}:
                            raise ProviderError("Flux refusé")
                        elif event.type == "response.completed":
                            completed = event.response.status == "completed"
                            if any(c.type == "refusal" for item in event.response.output if item.type == "message" for c in item.content):
                                raise ProviderError("Refus")
                text = "".join(parts).strip()
                if not completed or not text:
                    raise ProviderError("Flux incomplet")
        print(f"Fournisseur=chatgpt modèle={settings.ai_model}")
        print(text)
        print("Transcription exacte : " + ("oui" if text.splitlines() == list(LINES) else "non, à examiner"))
        return 0
    except (APIError, httpx.HTTPError, ProviderError, TimeoutError):
        print("Essai vision indisponible ou incomplet ; aucun repli par clé API.")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-real", action="store_true", help="Autoriser un appel utilisant le forfait Plus")
    parser.add_argument("--write-png", help="Écrire uniquement l'image synthétique à ce chemin, sans appel réseau")
    args = parser.parse_args()
    if args.write_png:
        from pathlib import Path
        with Path(args.write_png).open("xb") as file:
            file.write(synthetic_png())
        return 0
    if not args.run_real:
        parser.error("Utiliser --run-real pour déclencher l'essai")
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
