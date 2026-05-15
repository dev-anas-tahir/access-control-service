import uuid
from typing import Protocol

from app.catalog.domain.entities.category import Category


class CategoryRepository(Protocol):
    async def find_by_id(self, id: uuid.UUID) -> Category | None: ...

    async def find_by_slug(self, slug: str) -> Category | None: ...

    async def list_all(self) -> list[Category]: ...

    async def add(
        self,
        *,
        name: str,
        slug: str,
        parent_id: uuid.UUID | None,
    ) -> Category: ...
