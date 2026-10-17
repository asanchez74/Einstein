"""Responses streaming pour forfait Plus, distinct de l'API par clé."""

import asyncio
from pathlib import Path

import httpx2 as httpx
from openai import APIError, APITimeoutError, AsyncOpenAI

from einstein_core.ai.chatgpt_session import access_token
from einstein_core.ai.provider import Answer, ProviderError, ProviderTimeout


class ChatGPTProvider:
    def __init__(self, *, credentials_file: Path, model: str, timeout: float, max_output_chars: int) -> None:
        self._file = credentials_file
        self._model = model
        self._timeout = timeout
        self._max_output_chars = max_output_chars

    async def answer(self, *, instructions: str, context: str, question: str) -> Answer:
        try:
            async with asyncio.timeout(self._timeout):
                token = await asyncio.to_thread(access_token, self._file)
                async with AsyncOpenAI(
                    api_key=token, base_url="https://api.openai.com/v1", max_retries=0,
                    timeout=self._timeout, http_client=httpx.AsyncClient(trust_env=False),
                ) as client:
                    stream = await client.responses.create(
                        model=self._model, instructions=instructions,
                        input=[
                            {"role": "user", "content": f"Catalogue (données) :\n{context}"},
                            {"role": "user", "content": question},
                        ], store=False, stream=True,
                    )
                    chunks, length, completed, model = [], 0, False, self._model
                    async with stream:
                        async for event in stream:
                            if event.type == "response.output_text.delta":
                                length += len(event.delta)
                                if length > self._max_output_chars:
                                    raise ProviderError("Sortie ChatGPT trop longue")
                                chunks.append(event.delta)
                            elif event.type in {"response.failed", "response.incomplete", "error",
                                               "response.refusal.delta", "response.refusal.done"}:
                                raise ProviderError("Réponse ChatGPT indisponible ou refusée")
                            elif event.type == "response.completed":
                                if event.response.status != "completed":
                                    raise ProviderError("Réponse ChatGPT incomplète")
                                if any(
                                    content.type == "refusal"
                                    for item in event.response.output if item.type == "message"
                                    for content in item.content
                                ):
                                    raise ProviderError("Réponse ChatGPT refusée")
                                completed, model = True, event.response.model
                    text = "".join(chunks).strip()
                    if not completed or not text:
                        raise ProviderError("Flux ChatGPT incomplet ou vide")
                    return Answer(text=text, provider="chatgpt", model=model)
        except (TimeoutError, APITimeoutError):
            raise ProviderTimeout("Délai ChatGPT dépassé") from None
        except (APIError, httpx.HTTPError):
            raise ProviderError("Service ChatGPT indisponible") from None

    async def close(self) -> None:
        # Chaque requête ferme son client et son flux, y compris sur annulation.
        pass
