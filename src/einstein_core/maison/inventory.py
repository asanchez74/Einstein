"""Validation et chargement du catalogue, sans accès réseau."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, TypeAdapter, ValidationError, field_validator


class Equipment(BaseModel):
    """Description d'un équipement connu."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1)
    category: Literal["nas", "router", "dns"]
    address: IPvAnyAddress
    role: str = Field(min_length=1)


    @field_validator("address", mode="before")
    @classmethod
    def address_must_be_text(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("L'adresse IP doit être une chaîne")
        return value


_catalogue = TypeAdapter(list[Equipment])


class InventoryError(ValueError):
    """Catalogue indisponible ou invalide, sans divulgation de son contenu."""


def load_inventory(path: Path) -> tuple[Equipment, ...]:
    """Charge une fois le fichier ; rejette tout identifiant dupliqué."""

    try:
        items = _catalogue.validate_json(path.read_bytes())
    except OSError:
        raise InventoryError("Inventaire Maison absent ou illisible") from None
    except ValidationError:
        raise InventoryError("Inventaire Maison : JSON ou équipement invalide") from None
    if len({item.id for item in items}) != len(items):
        raise InventoryError("Inventaire Maison : identifiant dupliqué")
    return tuple(sorted(items, key=lambda item: item.id))
