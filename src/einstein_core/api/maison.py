"""Routes en lecture seule de l'inventaire Maison."""

from fastapi import APIRouter, HTTPException, Request

from einstein_core.maison.inventory import Equipment

router = APIRouter(prefix="/api/v1/maison/equipements", tags=["maison"])


@router.get("", response_model=list[Equipment])
def list_equipment(request: Request) -> tuple[Equipment, ...]:
    return request.app.state.inventory


@router.get("/{equipment_id}", response_model=Equipment)
def get_equipment(equipment_id: str, request: Request) -> Equipment:
    for item in request.app.state.inventory:
        if item.id == equipment_id:
            return item
    raise HTTPException(status_code=404, detail="Équipement introuvable")
