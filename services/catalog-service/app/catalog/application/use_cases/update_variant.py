from app.catalog.application.dto import ProductVariantResult, UpdateVariantInput
from app.catalog.domain.exceptions import (
    ProductNotFoundError,
    ProductVariantNotFoundError,
)
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class UpdateVariantUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: UpdateVariantInput) -> ProductVariantResult:
        async with self._uow_factory() as uow:
            variant = await uow.products.find_variant_by_id(input.variant_id)
            if not variant:
                raise ProductVariantNotFoundError()

            product = await uow.products.find_by_id(variant.product_id)
            if not product:
                raise ProductNotFoundError()

            if input.price is not None:
                event = product.update_variant_price(
                    variant, input.price, actor_id=input.actor_id
                )
                if event:
                    uow.add_event(event)

            if input.attributes is not None:
                variant.attributes = input.attributes
            if input.is_active is not None:
                variant.is_active = input.is_active

            await uow.products.save_variant(variant)
            await uow.commit()

        return ProductVariantResult(
            id=variant.id,
            sku=variant.sku,
            price=variant.price,
            attributes=variant.attributes,
            is_active=variant.is_active,
        )
