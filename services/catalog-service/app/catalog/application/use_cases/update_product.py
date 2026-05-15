from app.catalog.application.dto import (
    ProductResult,
    ProductVariantResult,
    UpdateProductInput,
)
from app.catalog.domain.exceptions import CategoryNotFoundError, ProductNotFoundError
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class UpdateProductUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: UpdateProductInput) -> ProductResult:
        async with self._uow_factory() as uow:
            product = await uow.products.find_by_id(input.product_id)
            if not product:
                raise ProductNotFoundError()

            if input.category_id and input.category_id != product.category_id:
                if not await uow.categories.find_by_id(input.category_id):
                    raise CategoryNotFoundError()
                product.category_id = input.category_id

            if input.name is not None:
                product.name = input.name
            if input.description is not None:
                product.description = input.description

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
