from app.catalog.application.dto import CategoryResult, CreateCategoryInput
from app.catalog.domain.exceptions import (
    CategoryNotFoundError,
    CategorySlugAlreadyExistsError,
)
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class CreateCategoryUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: CreateCategoryInput) -> CategoryResult:
        async with self._uow_factory() as uow:
            if await uow.categories.find_by_slug(input.slug):
                raise CategorySlugAlreadyExistsError()

            if input.parent_id and not await uow.categories.find_by_id(input.parent_id):
                raise CategoryNotFoundError()

            category = await uow.categories.add(
                name=input.name,
                slug=input.slug,
                parent_id=input.parent_id,
            )
            await uow.commit()

        return CategoryResult(
            id=category.id,
            name=category.name,
            slug=category.slug,
            parent_id=category.parent_id,
            created_at=category.created_at,
        )
