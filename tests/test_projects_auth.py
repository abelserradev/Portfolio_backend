import pytest
from httpx import AsyncClient

from app.core.config import get_settings


@pytest.fixture
def admin_key(monkeypatch: pytest.MonkeyPatch) -> str:
    clave = "test-admin-key-secreta"
    monkeypatch.setenv("ADMIN_API_KEY", clave)
    get_settings.cache_clear()
    yield clave
    get_settings.cache_clear()


PAYLOAD_MINIMO = {
    "title": "Proyecto test",
    "description": "Descripción de prueba para auth",
    "status": "live",
}


@pytest.mark.asyncio
async def test_create_project_sin_api_key_retorna_401(
    client: AsyncClient, admin_key: str
) -> None:
    resp = await client.post("/api/v1/projects/", json=PAYLOAD_MINIMO)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_project_con_api_key_valida(
    client: AsyncClient, admin_key: str
) -> None:
    resp = await client.post(
        "/api/v1/projects/",
        json=PAYLOAD_MINIMO,
        headers={"X-Admin-Api-Key": admin_key},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == PAYLOAD_MINIMO["title"]


@pytest.mark.asyncio
async def test_delete_project_requiere_api_key(
    client: AsyncClient, admin_key: str
) -> None:
    crear = await client.post(
        "/api/v1/projects/",
        json=PAYLOAD_MINIMO,
        headers={"X-Admin-Api-Key": admin_key},
    )
    project_id = crear.json()["id"]

    sin_clave = await client.delete(f"/api/v1/projects/{project_id}")
    assert sin_clave.status_code == 401

    con_clave = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"X-Admin-Api-Key": admin_key},
    )
    assert con_clave.status_code == 204
