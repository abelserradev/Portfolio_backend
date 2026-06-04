import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import BackgroundTasks, HTTPException

from app.core.config import get_settings
from app.schemas.github import ActivityScanResponse, LanguageStat
from app.services.cache import RedisCache

logger = logging.getLogger(__name__)
settings = get_settings()
MONTHS = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN"]
DAYS_PER_MONTH = 30


def _timeout_github() -> httpx.Timeout:
    t = settings.GITHUB_HTTP_TIMEOUT_SECONDS
    return httpx.Timeout(connect=min(t, 30.0), read=t, write=t, pool=t)


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
        try:
            data = await loader()
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as err:
            logger.warning("GitHub no respondió a tiempo para %s: %s", key, err)
            stale = await self.cache.get_json(key)
            if isinstance(stale, dict) and stale.get("data") is not None:
                return stale["data"]
            raise HTTPException(
                status_code=503,
                detail="GitHub no respondió a tiempo; reintenta en unos minutos",
            ) from err
        envelope = {
            "fetched_at": int(time.time()),
            "data": (
                [item.model_dump() for item in data]
                if isinstance(data, list)
                else data.model_dump()
            ),
        }
        await self.cache.set_json(key, envelope, settings.GITHUB_CACHE_STALE_SECONDS)
        return envelope["data"]

    async def _fetch_user_languages(self, top_n: int = 5) -> list[LanguageStat]:
        if not settings.GITHUB_USERNAME:
            raise HTTPException(status_code=500, detail="GITHUB_USERNAME no configurado")
        timeout = _timeout_github()
        async with httpx.AsyncClient(timeout=timeout) as client:
            repos_url = f"{self.base_url}/users/{settings.GITHUB_USERNAME}/repos"
            response = await client.get(
                repos_url,
                headers=self.headers,
                params={"per_page": 100, "sort": "updated"},
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error fetching GitHub repos",
                )
            repos = [
                r for r in response.json()
                if not r.get("fork")
            ][: settings.GITHUB_LANG_MAX_REPOS]
            language_totals: defaultdict[str, int] = defaultdict(int)
            sem = asyncio.Semaphore(settings.GITHUB_LANG_CONCURRENCY)

            async def fetch_languages(repo_name: str) -> dict[str, int]:
                async with sem:
                    lang_url = (
                        f"{self.base_url}/repos/{settings.GITHUB_USERNAME}"
                        f"/{repo_name}/languages"
                    )
                    try:
                        lang_resp = await client.get(lang_url, headers=self.headers)
                    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException):
                        logger.debug("Timeout idiomas repo %s", repo_name)
                        return {}
                    if lang_resp.status_code == 200:
                        return lang_resp.json()
                    return {}

            tasks = [fetch_languages(repo["name"]) for repo in repos]
            lang_results = await asyncio.gather(*tasks, return_exceptions=True)
            for repo_langs in lang_results:
                if isinstance(repo_langs, BaseException):
                    continue
                for lang, bytes_count in repo_langs.items():
                    language_totals[lang] += bytes_count
            total_bytes = sum(language_totals.values())
            if total_bytes == 0:
                return []
            stats = []
            for lang, count in language_totals.items():
                percentage = round((count / total_bytes) * 100, 1)
                stats.append(
                    LanguageStat(
                        name=lang,
                        percentage=percentage,
                        color=self._get_color_for_lang(lang),
                    )
                )
            stats.sort(key=lambda x: x.percentage, reverse=True)
            return stats[:top_n]

    async def _fetch_activity_scan(self) -> ActivityScanResponse:
        if not settings.GITHUB_USERNAME:
            raise HTTPException(status_code=500, detail="GITHUB_USERNAME no configurado")
        timeout = _timeout_github()
        async with httpx.AsyncClient(timeout=timeout) as client:
            events_url = f"{self.base_url}/users/{settings.GITHUB_USERNAME}/events/public"
            response = await client.get(
                events_url,
                headers=self.headers,
                params={"per_page": 100},
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Error fetching GitHub activity",
            )
        event_count = len(response.json())
        cells = []
        for month_idx, month in enumerate(MONTHS):
            for day in range(DAYS_PER_MONTH):
                idx = month_idx * DAYS_PER_MONTH + day
                level = self._calculate_activity_level(idx, event_count)
                cells.append({"month": month, "day": day + 1, "level": level})
        return ActivityScanResponse(
            months=MONTHS,
            days_per_month=DAYS_PER_MONTH,
            cells=cells,
        )

    def _calculate_activity_level(self, idx: int, event_count: int) -> int:
        base = (idx * 7 + event_count * 3 + idx // DAYS_PER_MONTH) % 4
        if event_count == 0 and idx % 5 != 0:
            return 0
        return base

    def _get_color_for_lang(self, lang: str) -> str:
        colors = {
            "TypeScript": "cyan",
            "JavaScript": "yellow",
            "Python": "magenta",
            "CSS": "cyan",
            "HTML": "yellow",
            "Rust": "magenta",
            "Go": "cyan",
            "Java": "yellow",
        }
        return colors.get(lang, "gray")
