import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.inventory.domain.entities.inventory import Inventory
from app.inventory.infrastructure.orm.inventory import Inventory as InventoryORM
from app.inventory.infrastructure.repositories.mappers import _inventory_orm_to_domain


class SqlAlchemyInventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_variant_id(self, variant_id: uuid.UUID) -> Inventory | None:
        result = await self._session.execute(
            select(InventoryORM).where(InventoryORM.variant_id == variant_id)
        )
        orm = result.scalar_one_or_none()
        return _inventory_orm_to_domain(orm) if orm else None

    async def add(self, *, variant_id: uuid.UUID) -> Inventory:
        orm = InventoryORM(variant_id=variant_id)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _inventory_orm_to_domain(orm)

    async def save(self, inventory: Inventory) -> None:
        result = await self._session.execute(
            select(InventoryORM).where(InventoryORM.id == inventory.id)
        )
        orm = result.scalar_one()
        orm.quantity_on_hand = inventory.quantity_on_hand
        orm.quantity_reserved = inventory.quantity_reserved
        self._session.add(orm)
