import json
import logging
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Cache JSON para datos públicos del portfolio; Redis acelera la visita, pero no debe tumbar la web."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client: redis.Redis | None = None
        if settings.REDIS_URL:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )

    @property
    def is_enabled(self) -> bool:
        return self._client is not None

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        if not self._client:
            return None
        try:
            raw = await self._client.get(key)
        except RedisError as err:
            logger.warning("Redis no respondió al leer %s: %s", key, err)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Si alguna versión vieja guardó basura, conviene limpiar la key desde un job de mantenimiento.
            logger.warning("Payload inválido en cache Redis para %s", key)
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self._client:
            return
        try:
            payload = json.dumps(value, ensure_ascii=False)
            await self._client.set(key, payload, ex=ttl_seconds)
        except (TypeError, RedisError) as err:
            logger.warning("Redis no pudo guardar %s: %s", key, err)

    async def acquire_lock(self, key: str, ttl_seconds: int = 60) -> bool:
        if not self._client:
            return False
        try:
            return bool(await self._client.set(key, "1", ex=ttl_seconds, nx=True))
        except RedisError as err:
            logger.warning("Redis no pudo bloquear %s: %s", key, err)
            return False
