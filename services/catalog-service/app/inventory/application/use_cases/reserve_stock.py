from app.inventory.application.dto import InventoryResult, ReserveStockInput
from app.inventory.domain.exceptions import (
    InsufficientStockError,
    InventoryNotFoundError,
)
from app.inventory.domain.ports.unit_of_work import InventoryUnitOfWorkFactory


class ReserveStockUseCase:
    def __init__(self, uow_factory: InventoryUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: ReserveStockInput) -> InventoryResult:
        async with self._uow_factory() as uow:
            inv = await uow.inventory.find_by_variant_id(input.variant_id)
            if not inv:
                raise InventoryNotFoundError()

            if input.quantity > inv.available:
                raise InsufficientStockError(inv.available, input.quantity)

            inv.reserve(input.quantity)
            await uow.inventory.save(inv)
            await uow.commit()

        return InventoryResult(
            id=inv.id,
            variant_id=inv.variant_id,
            quantity_on_hand=inv.quantity_on_hand,
            quantity_reserved=inv.quantity_reserved,
            available=inv.available,
            updated_at=inv.updated_at,
        )
