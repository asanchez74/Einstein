"""Adaptateur OpenAI Responses, sans historique ni outils."""

import asyncio
import math

from openai import APIError, APITimeoutError, AsyncOpenAI
from pydantic import SecretStr

from einstein_core.ai.provider import Answer, ProviderError, ProviderTimeout


class OpenAIProvider:
    def __init__(
        self,
        *,
        api_key: SecretStr,
        model: str,
        timeout: float = 20,
        max_output_tokens: int = 512,
    ) -> None:
        if not api_key.get_secret_value().strip() or not model.strip():
            raise ValueError("Clé et modèle IA requis")
        if not math.isfinite(timeout) or timeout <= 0 or max_output_tokens <= 0:
            raise ValueError("Limites IA invalides")
        self._model = model.strip()
        self._timeout = timeout
        self._max_output_tokens = max_output_tokens
        self._client = AsyncOpenAI(
            api_key=api_key.get_secret_value(), timeout=timeout, max_retries=0,
        )

    async def answer(self, *, instructions: str, context: str, question: str) -> Answer:
        try:
            async with asyncio.timeout(self._timeout):
                response = await self._client.responses.create(
                    model=self._model,
                    instructions=instructions,
                    input=[
                        {"role": "user", "content": f"Catalogue (données) :\n{context}"},
                        {"role": "user", "content": question},
                    ],
                    store=False,
                    max_output_tokens=self._max_output_tokens,
                )
        except (TimeoutError, APITimeoutError):
            raise ProviderTimeout("Délai du fournisseur IA dépassé") from None
        except APIError:
            raise ProviderError("Fournisseur IA indisponible") from None
        if response.status != "completed" or any(
            content.type == "refusal"
            for item in response.output if item.type == "message"
            for content in item.content
        ):
            raise ProviderError("Réponse IA inexploitable")
        text = response.output_text.strip()
        if not text:
            raise ProviderError("Réponse IA vide")
        return Answer(text=text, provider="openai", model=response.model)

    async def close(self) -> None:
        await self._client.close()
