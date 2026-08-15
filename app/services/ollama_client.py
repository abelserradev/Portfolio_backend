import json
from pathlib import Path

import httpx

from app.core.config import Settings


class OllamaClient:
    """Cliente HTTP hacia Ollama; timeout acotado para no bloquear el event loop."""

    def __init__(self, settings: Settings) -> None:
        self._base = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL
        self._timeout = settings.OLLAMA_TIMEOUT_SECONDS

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def chat(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Respuesta vacía de Ollama")
        return content.strip()


def cargar_matriz_cotizacion(settings: Settings) -> dict:
    ruta = Path(settings.QUOTE_RANGES_PATH)
    if not ruta.is_absolute():
        ruta = Path(__file__).resolve().parents[2] / ruta
    with ruta.open(encoding="utf-8") as fh:
        return json.load(fh)
