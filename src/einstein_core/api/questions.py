"""API de questions, séparée de la disponibilité du socle local."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from einstein_core.ai.provider import ProviderError, ProviderTimeout
from einstein_core.maison.questions import ContextTooLarge, QuestionsBusy

router = APIRouter(prefix="/api/v1/maison", tags=["maison"])


class Question(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(min_length=1, max_length=2000)


class QuestionAnswer(BaseModel):
    answer: str
    provider: str
    model: str


@router.post("/questions", response_model=QuestionAnswer)
async def ask_question(payload: Question, request: Request) -> QuestionAnswer:
    service = request.app.state.questions
    if service is None:
        raise HTTPException(status_code=503, detail="IA non configurée ou désactivée")
    try:
        result = await service.ask(payload.question)
    except QuestionsBusy:
        raise HTTPException(status_code=429, detail="Capacité IA occupée") from None
    except ContextTooLarge:
        raise HTTPException(status_code=503, detail="Catalogue trop volumineux pour l'IA") from None
    except ProviderTimeout:
        raise HTTPException(status_code=504, detail="Délai du fournisseur IA dépassé") from None
    except ProviderError:
        raise HTTPException(status_code=502, detail="Réponse du fournisseur IA indisponible") from None
    return QuestionAnswer(answer=result.text, provider=result.provider, model=result.model)
