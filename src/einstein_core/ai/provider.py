"""Contrat indépendant des SDK des fournisseurs."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Answer:
    text: str
    provider: str
    model: str


class ProviderError(Exception):
    """Échec fournisseur sans contenu distant ni secret."""


class ProviderTimeout(ProviderError):
    """Délai total dépassé."""


class AnswerProvider(Protocol):
    async def answer(self, *, instructions: str, context: str, question: str) -> Answer: ...

    async def close(self) -> None: ...
