from app.catalog.application.dto import (
    CreateProductInput,
    ProductResult,
    ProductVariantResult,
)
from app.catalog.domain.exceptions import CategoryNotFoundError
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class CreateProductUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: CreateProductInput) -> ProductResult:
        async with self._uow_factory() as uow:
            if not await uow.categories.find_by_id(input.category_id):
                raise CategoryNotFoundError()

            product = await uow.products.add(
                name=input.name,
                description=input.description,
                category_id=input.category_id,
                created_by=input.actor_id,
            )
            await uow.commit()

        return ProductResult(
            id=product.id,
            name=product.name,
            description=product.description,
            category_id=product.category_id,
            status=product.status,
            created_by=product.created_by,
            variants=[],
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
