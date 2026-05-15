import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog.domain.entities.product import Product, ProductStatus, ProductVariant
from app.catalog.infrastructure.orm.product import Product as ProductORM
from app.catalog.infrastructure.orm.product import ProductVariant as VariantORM
from app.catalog.infrastructure.repositories.mappers import (
    _product_orm_to_domain,
    _variant_orm_to_domain,
)


class SqlAlchemyProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: uuid.UUID) -> Product | None:
        result = await self._session.execute(
            select(ProductORM)
            .where(ProductORM.id == id)
            .options(selectinload(ProductORM.variants))
        )
        orm = result.scalar_one_or_none()
        return _product_orm_to_domain(orm) if orm else None

    async def list_active(self, limit: int, offset: int) -> list[Product]:
        result = await self._session.execute(
            select(ProductORM)
            .where(ProductORM.status == ProductStatus.ACTIVE)
            .options(selectinload(ProductORM.variants))
            .limit(limit)
            .offset(offset)
        )
        return [_product_orm_to_domain(row) for row in result.scalars().all()]

    async def add(
        self,
        *,
        name: str,
        description: str | None,
        category_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> Product:
        orm = ProductORM(
            name=name,
            description=description,
            category_id=category_id,
            status=ProductStatus.INACTIVE,
            created_by=created_by,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm, ["variants"])
        return _product_orm_to_domain(orm)

    async def save(self, product: Product) -> None:
        result = await self._session.execute(
            select(ProductORM).where(ProductORM.id == product.id)
        )
        orm = result.scalar_one()
        orm.name = product.name
        orm.description = product.description
        orm.category_id = product.category_id
        orm.status = product.status
        self._session.add(orm)

    async def add_variant(
        self,
        *,
        product_id: uuid.UUID,
        sku: str,
        price: float,
        attributes: dict,
    ) -> ProductVariant:
        orm = VariantORM(
            product_id=product_id, sku=sku, price=price, attributes=attributes
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _variant_orm_to_domain(orm)

    async def sku_exists(self, sku: str) -> bool:
        result = await self._session.execute(
            select(VariantORM.id).where(VariantORM.sku == sku)
        )
        return result.scalar_one_or_none() is not None

    async def find_variant_by_id(self, variant_id: uuid.UUID) -> ProductVariant | None:
        result = await self._session.execute(
            select(VariantORM).where(VariantORM.id == variant_id)
        )
        orm = result.scalar_one_or_none()
        return _variant_orm_to_domain(orm) if orm else None

    async def save_variant(self, variant: ProductVariant) -> None:
        result = await self._session.execute(
            select(VariantORM).where(VariantORM.id == variant.id)
        )
        orm = result.scalar_one()
        orm.price = variant.price
        orm.attributes = variant.attributes
        orm.is_active = variant.is_active
        self._session.add(orm)

    async def delete_variant(self, variant_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(VariantORM).where(VariantORM.id == variant_id)
        )
        orm = result.scalar_one()
        await self._session.delete(orm)
