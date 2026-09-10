from unittest.mock import AsyncMock

import pytest

from app.services.github import GithubService


class CacheFalso:
    def __init__(self) -> None:
        self.almacen: dict[str, dict] = {}
        self.is_enabled = True

    async def get_json(self, key: str):
        return self.almacen.get(key)

    async def set_json(self, key: str, value: dict, _ttl: int) -> None:
        self.almacen[key] = value

    async def acquire_lock(self, _key: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_github_service_usa_cache_fresco_sin_llamar_loader() -> None:
    cache = CacheFalso()
    cache.almacen["github:languages:test:top:5:v1"] = {
        "fetched_at": 9_999_999_999,
        "data": [{"name": "TypeScript", "percentage": 80.0, "color": "#3178c6"}],
    }
    servicio = GithubService(cache=cache)
    loader = AsyncMock(return_value=[])

    data = await servicio._get_cached_data(
        key="github:languages:test:top:5:v1",
        loader=loader,
        background_tasks=None,
    )

    assert data[0]["name"] == "TypeScript"
    loader.assert_not_called()
