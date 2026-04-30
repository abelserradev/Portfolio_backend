import asyncio
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import BackgroundTasks, HTTPException

from app.core.config import get_settings
from app.schemas.github import ActivityScanResponse, LanguageStat
from app.services.cache import RedisCache

settings = get_settings()
MONTHS = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN"]
DAYS_PER_MONTH = 30

class GithubService:
    def __init__(self, cache: RedisCache | None = None):
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        self.cache = cache or RedisCache()
        if settings.GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    async def get_user_languages(
        self,
        background_tasks: BackgroundTasks | None = None,
        top_n: int = 5,
    ) -> list[LanguageStat]:
        data = await self._get_cached_data(
            key=f"github:languages:{settings.GITHUB_USERNAME}:top:{top_n}:v1",
            loader=lambda: self._fetch_user_languages(top_n),
            background_tasks=background_tasks,
        )
        return [LanguageStat.model_validate(item) for item in data]

    async def get_activity_scan(
        self,
        background_tasks: BackgroundTasks | None = None,
    ) -> ActivityScanResponse:
        data = await self._get_cached_data(
            key=f"github:activity:{settings.GITHUB_USERNAME}:v1",
            loader=self._fetch_activity_scan,
            background_tasks=background_tasks,
        )
        return ActivityScanResponse.model_validate(data)

    async def _get_cached_data(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        background_tasks: BackgroundTasks | None,
    ) -> Any:
        cached = await self.cache.get_json(key)
        now = int(time.time())
        if isinstance(cached, dict) and "data" in cached and "fetched_at" in cached:
            age = now - int(cached["fetched_at"])
            if age < settings.GITHUB_CACHE_TTL_SECONDS:
                return cached["data"]
            if background_tasks:
                background_tasks.add_task(self._refresh_cache, key, loader)
            return cached["data"]
        return await self._refresh_cache(key, loader)

    async def _refresh_cache(self, key: str, loader: Callable[[], Awaitable[Any]]) -> Any:
        lock_key = f"{key}:lock"
        has_lock = await self.cache.acquire_lock(lock_key)
        if self.cache.is_enabled and not has_lock:
            cached = await self.cache.get_json(key)
            if isinstance(cached, dict) and "data" in cached:
                return cached["data"]
        data = await loader()
        envelope = {
            "fetched_at": int(time.time()),
            "data": [item.model_dump() for item in data] if isinstance(data, list) else data.model_dump(),
        }
        await self.cache.set_json(key, envelope, settings.GITHUB_CACHE_STALE_SECONDS)
        return envelope["data"]

    async def _fetch_user_languages(self, top_n: int = 5) -> list[LanguageStat]:
        if not settings.GITHUB_USERNAME:
            raise HTTPException(status_code=500, detail="GITHUB_USERNAME no configurado")
        async with httpx.AsyncClient(timeout=20.0) as client:
            # 1. Obtener todos los repositorios públicos (o privados si hay token)
            repos_url = f"{self.base_url}/users/{settings.GITHUB_USERNAME}/repos"
            response = await client.get(repos_url, headers=self.headers, params={"per_page": 100})
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Error fetching GitHub repos")
            
            repos = response.json()
            
            # 2. Obtener las estadísticas de lenguajes para cada repositorio
            language_totals = defaultdict(int)
            total_bytes = 0
            
            async def fetch_languages(repo_name: str):
                lang_url = f"{self.base_url}/repos/{settings.GITHUB_USERNAME}/{repo_name}/languages"
                lang_resp = await client.get(lang_url, headers=self.headers)
                if lang_resp.status_code == 200:
                    return lang_resp.json()
                return {}

            tasks = [fetch_languages(repo["name"]) for repo in repos if not repo["fork"]]
            lang_results = await asyncio.gather(*tasks)

            for repo_langs in lang_results:
                for lang, bytes_count in repo_langs.items():
                    language_totals[lang] += bytes_count
                    total_bytes += bytes_count

            if total_bytes == 0:
                return []

            # 3. Calcular porcentajes
            stats = []
            for lang, count in language_totals.items():
                percentage = round((count / total_bytes) * 100, 1)
                stats.append(LanguageStat(name=lang, percentage=percentage, color=self._get_color_for_lang(lang)))

            # Ordenar de mayor a menor y tomar el top N
            stats.sort(key=lambda x: x.percentage, reverse=True)
            return stats[:top_n]

    async def _fetch_activity_scan(self) -> ActivityScanResponse:
        if not settings.GITHUB_USERNAME:
            raise HTTPException(status_code=500, detail="GITHUB_USERNAME no configurado")
        async with httpx.AsyncClient(timeout=15.0) as client:
            events_url = f"{self.base_url}/users/{settings.GITHUB_USERNAME}/events/public"
            response = await client.get(events_url, headers=self.headers, params={"per_page": 100})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error fetching GitHub activity")
        event_count = len(response.json())
        cells = []
        for month_idx, month in enumerate(MONTHS):
            for day in range(DAYS_PER_MONTH):
                idx = month_idx * DAYS_PER_MONTH + day
                level = self._calculate_activity_level(idx, event_count)
                cells.append({"month": month, "day": day + 1, "level": level})
        return ActivityScanResponse(months=MONTHS, days_per_month=DAYS_PER_MONTH, cells=cells)

    def _calculate_activity_level(self, idx: int, event_count: int) -> int:
        # El scan es decorativo, pero se ancla al volumen real de eventos para que cambie al refrescar GitHub.
        base = (idx * 7 + event_count * 3 + idx // DAYS_PER_MONTH) % 4
        if event_count == 0 and idx % 5 != 0:
            return 0
        return base

    def _get_color_for_lang(self, lang: str) -> str:
        # Colores temáticos cyberpunk para el portafolio
        colors = {
            "TypeScript": "cyan",
            "JavaScript": "yellow",
            "Python": "magenta",
            "CSS": "cyan",
            "HTML": "yellow",
            "Rust": "magenta",
            "Go": "cyan",
            "Java": "yellow"
        }
        return colors.get(lang, "gray")
