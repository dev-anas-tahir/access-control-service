import uuid

from app.catalog.application.dto import ProductResult, ProductVariantResult
from app.catalog.domain.exceptions import ProductNotFoundError
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class GetProductUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, product_id: uuid.UUID) -> ProductResult:
        async with self._uow_factory() as uow:
            product = await uow.products.find_by_id(product_id)
            if not product:
                raise ProductNotFoundError()

        return ProductResult(
            id=product.id,
            name=product.name,
            description=product.description,
            category_id=product.category_id,
            status=product.status,
            created_by=product.created_by,
            variants=[
                ProductVariantResult(
                    id=v.id,
                    sku=v.sku,
                    price=v.price,
                    attributes=v.attributes,
                    is_active=v.is_active,
                )
                for v in product.variants
            ],
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
