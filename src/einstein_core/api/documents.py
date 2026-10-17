"""Recherche locale ; aucun contenu transmis au fournisseur IA."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from einstein_core.documents.search import SearchResult

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class SearchQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=5, ge=1, le=20)


@router.post("/recherche", response_model=SearchResult)
def search_documents(payload: SearchQuery, request: Request) -> SearchResult:
    index = request.app.state.documents
    if index is None:
        raise HTTPException(status_code=503, detail="Recherche documentaire désactivée ou indisponible")
    return index.search(payload.query, payload.limit)
