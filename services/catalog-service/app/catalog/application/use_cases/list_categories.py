from app.catalog.application.dto import CategoryResult
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class ListCategoriesUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self) -> list[CategoryResult]:
        async with self._uow_factory() as uow:
            categories = await uow.categories.list_all()

        return [
            CategoryResult(
                id=c.id,
                name=c.name,
                slug=c.slug,
                parent_id=c.parent_id,
                created_at=c.created_at,
            )
            for c in categories
        ]
