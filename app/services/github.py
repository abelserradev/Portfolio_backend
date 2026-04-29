import httpx
import asyncio
from fastapi import HTTPException
from collections import defaultdict
from app.core.config import get_settings
from app.schemas.github import LanguageStat

settings = get_settings()

class GithubService:
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            self.headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    async def get_user_languages(self, top_n: int = 5) -> list[LanguageStat]:
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
