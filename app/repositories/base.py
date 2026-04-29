from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Evitar concatenar texto de usuario en SQL plano (ORM enlaza parámetros); ver sql_practicas.

ModelType = TypeVar("ModelType")

class AbstractRepository(ABC, Generic[ModelType]):
    @abstractmethod
    async def get(self, id: int) -> ModelType | None: ...
    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> list[ModelType]: ...
    @abstractmethod
    async def add(self, entity: ModelType) -> ModelType: ...
    @abstractmethod
    async def update(self, entity: ModelType) -> ModelType: ...
    @abstractmethod
    async def delete(self, id: int) -> None: ...

class SqlAlchemyRepository(AbstractRepository[ModelType]):
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get(self, id: int) -> ModelType | None:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        result = await self.session.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def add(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        # merge: reassocia objetos detached y unifica comportamiento con cargas desde otras sesiones
        merged = await self.session.merge(entity)
        await self.session.flush()
        return merged

    async def delete(self, id: int) -> None:
        entity = await self.get(id)
        if entity:
            await self.session.delete(entity)
            await self.session.flush()