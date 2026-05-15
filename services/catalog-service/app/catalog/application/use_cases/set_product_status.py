from app.catalog.application.dto import (
    ProductResult,
    ProductVariantResult,
    SetProductStatusInput,
)
from app.catalog.domain.events import ProductPublished
from app.catalog.domain.exceptions import ProductNotFoundError
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class SetProductStatusUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: SetProductStatusInput) -> ProductResult:
        async with self._uow_factory() as uow:
            product = await uow.products.find_by_id(input.product_id)
            if not product:
                raise ProductNotFoundError()

            if input.active:
                newly_activated = product.activate()
                if newly_activated:
                    uow.add_event(
                        ProductPublished(
                            actor_id=input.actor_id,
                            product_id=product.id,
                            name=product.name,
                            category_id=product.category_id,
                        )
                    )
            else:
                product.deactivate()

            await uow.products.save(product)
            await uow.commit()

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
