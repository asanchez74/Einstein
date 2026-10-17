"""Contrat métier et HTTP de l'inventaire, sans réseau externe."""

import json

import pytest
from fastapi.testclient import TestClient

from einstein_core.config import Settings
from einstein_core.main import create_app
from einstein_core.maison.inventory import InventoryError, load_inventory


EQUIPMENT = {
    "id": "nas", "name": "NAS", "category": "nas",
    "address": "192.168.1.3", "role": "Hébergement",
}


def write_catalogue(tmp_path, items):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(items))
    return path


def test_inventory_routes_and_snapshot(tmp_path):
    path = write_catalogue(tmp_path, [EQUIPMENT, {**EQUIPMENT, "id": "autre"}])
    app = create_app(Settings(maison_inventory_path=path))
    with TestClient(app) as client:
        response = client.get("/api/v1/maison/equipements")
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == ["autre", "nas"]
        assert client.get("/api/v1/maison/equipements/nas").json() == EQUIPMENT
        assert client.get("/api/v1/maison/equipements/inconnu").status_code == 404
        path.write_text("[]")
        assert len(client.get("/api/v1/maison/equipements").json()) == 2
    with TestClient(app) as client:
        assert client.get("/api/v1/maison/equipements").json() == []
        assert client.get("/api/v1/maison/equipements/nas").status_code == 404


@pytest.mark.parametrize("changes", [
    {"id": "INVALID ID"}, {"name": " "}, {"role": ""},
    {"address": "not-an-ip"}, {"category": "unknown"}, {"secret": "private-value"},
])
def test_invalid_equipment_blocks_startup(tmp_path, changes):
    path = write_catalogue(tmp_path, [{**EQUIPMENT, **changes}])
    with pytest.raises(InventoryError, match="invalide") as exc:
        with TestClient(create_app(Settings(maison_inventory_path=path))):
            pytest.fail("Le démarrage ne doit pas réussir")
    assert "private-value" not in str(exc.value)


@pytest.mark.parametrize("content", ["{", "{}", "null", "[1]", "[\xff]"])
def test_invalid_json(tmp_path, content):
    path = tmp_path / "inventory.json"
    path.write_bytes(content.encode("latin1"))
    with pytest.raises(InventoryError, match="invalide"):
        load_inventory(path)


def test_duplicate_ids(tmp_path):
    path = write_catalogue(tmp_path, [EQUIPMENT, EQUIPMENT])
    with pytest.raises(InventoryError, match="dupliqué"):
        load_inventory(path)


@pytest.mark.parametrize("directory", [False, True])
def test_unreadable_inventory_blocks_startup(tmp_path, directory):
    path = tmp_path / "missing.json"
    if directory:
        path.mkdir()
    with pytest.raises(InventoryError, match="absent ou illisible"):
        with TestClient(create_app(Settings(maison_inventory_path=path))):
            pytest.fail("Le démarrage ne doit pas réussir")
