import uuid

from app.catalog.domain.exceptions import ProductVariantNotFoundError
from app.catalog.domain.ports.unit_of_work import CatalogUnitOfWorkFactory


class DeleteVariantUseCase:
    def __init__(self, uow_factory: CatalogUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, variant_id: uuid.UUID) -> None:
        async with self._uow_factory() as uow:
            if not await uow.products.find_variant_by_id(variant_id):
                raise ProductVariantNotFoundError()
            await uow.products.delete_variant(variant_id)
            await uow.commit()
