"""API key para mutaciones administrativas (catálogo de proyectos)."""

from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


async def requerir_api_key_admin(
    x_admin_api_key: Annotated[str | None, Header(alias="X-Admin-Api-Key")] = None,
) -> None:
    """Sin clave configurada en env no se exponen escrituras — evita CMS abierto por omisión."""
    clave_esperada = (get_settings().ADMIN_API_KEY or "").strip()
    if not clave_esperada:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mutaciones de proyectos deshabilitadas: configure ADMIN_API_KEY",
        )
    if not x_admin_api_key or x_admin_api_key.strip() != clave_esperada:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
        )
