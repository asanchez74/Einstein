"""Recherche locale ; aucun contenu transmis au fournisseur IA."""

from pathlib import PurePosixPath
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from einstein_core.documents.search import SearchResult, open_source

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class SearchQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=5, ge=1, le=20)


@router.post("/recherche", response_model=SearchResult)
def search_documents(payload: SearchQuery, request: Request) -> SearchResult:
    index = request.app.state.documents
    if index is None and getattr(request.app.state, "documents_indexing", False):
        raise HTTPException(status_code=503, detail="Indexation documentaire en cours ; réessayer plus tard")
    if index is None:
        raise HTTPException(status_code=503, detail="Recherche documentaire désactivée ou indisponible")
    return index.search(payload.query, payload.limit)


@router.get("/fichier")
def document_file(request: Request, source: str = Query(min_length=1, max_length=1024)) -> StreamingResponse:
    """Seules les sources de l'index courant sont servies : aucun chemin libre."""
    index = request.app.state.documents
    if index is None:
        raise HTTPException(status_code=503, detail="Recherche documentaire désactivée ou indisponible")
    suffix = PurePosixPath(source).suffix.lower()
    if source not in index.sources or suffix not in MEDIA_TYPES:
        raise HTTPException(status_code=404, detail="Document introuvable")
    try:
        file, size = open_source(request.app.state.settings.documents_path, source)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="Document introuvable") from None

    def chunks():
        with file:
            while chunk := file.read(256 * 1024):
                yield chunk

    disposition = "inline" if suffix == ".pdf" else "attachment"
    name = PurePosixPath(source).name
    return StreamingResponse(chunks(), media_type=MEDIA_TYPES[suffix], headers={
        "Content-Length": str(size),
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(name)}",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    })
