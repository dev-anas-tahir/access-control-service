import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.domain.entities.category import Category
from app.catalog.infrastructure.orm.category import Category as CategoryORM
from app.catalog.infrastructure.repositories.mappers import _category_orm_to_domain


class SqlAlchemyCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: uuid.UUID) -> Category | None:
        result = await self._session.execute(
            select(CategoryORM).where(CategoryORM.id == id)
        )
        orm = result.scalar_one_or_none()
        return _category_orm_to_domain(orm) if orm else None

    async def find_by_slug(self, slug: str) -> Category | None:
        result = await self._session.execute(
            select(CategoryORM).where(CategoryORM.slug == slug)
        )
        orm = result.scalar_one_or_none()
        return _category_orm_to_domain(orm) if orm else None

    async def list_all(self) -> list[Category]:
        result = await self._session.execute(
            select(CategoryORM).order_by(CategoryORM.name)
        )
        return [_category_orm_to_domain(row) for row in result.scalars().all()]

    async def add(
        self,
        *,
        name: str,
        slug: str,
        parent_id: uuid.UUID | None,
    ) -> Category:
        orm = CategoryORM(name=name, slug=slug, parent_id=parent_id)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _category_orm_to_domain(orm)
