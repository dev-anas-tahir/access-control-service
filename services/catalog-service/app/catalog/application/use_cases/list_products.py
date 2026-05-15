from app.catalog.application.dto import ProductResult, ProductVariantResult
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class ListProductsUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, limit: int = 20, offset: int = 0) -> list[ProductResult]:
        async with self._uow_factory() as uow:
            products = await uow.products.list_active(limit=limit, offset=offset)

        return [
            ProductResult(
                id=p.id,
                name=p.name,
                description=p.description,
                category_id=p.category_id,
                status=p.status,
                created_by=p.created_by,
                variants=[
                    ProductVariantResult(
                        id=v.id,
                        sku=v.sku,
                        price=v.price,
                        attributes=v.attributes,
                        is_active=v.is_active,
                    )
                    for v in p.variants
                ],
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in products
        ]
