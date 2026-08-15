from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession, QuoteLead


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obtener_sesion(self, session_id: str) -> ChatSession | None:
        result = await self._session.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def guardar_sesion(self, chat_session: ChatSession) -> ChatSession:
        self._session.add(chat_session)
        await self._session.flush()
        return chat_session

    async def crear_lead(self, lead: QuoteLead) -> QuoteLead:
        self._session.add(lead)
        await self._session.flush()
        await self._session.refresh(lead)
        return lead

    async def actualizar_lead(self, lead: QuoteLead) -> QuoteLead:
        merged = await self._session.merge(lead)
        await self._session.flush()
        return merged
