from app.inventory.application.dto import InventoryResult, RestockInput
from app.inventory.domain.events import InventoryRestocked
from app.inventory.domain.ports.unit_of_work import InventoryUnitOfWorkFactory


class RestockUseCase:
    def __init__(self, uow_factory: InventoryUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: RestockInput) -> InventoryResult:
        async with self._uow_factory() as uow:
            inv = await uow.inventory.find_by_variant_id(input.variant_id)
            if not inv:
                inv = await uow.inventory.add(variant_id=input.variant_id)

            was_depleted = inv.quantity_on_hand == 0
            inv.restock(input.quantity)
            await uow.inventory.save(inv)

            if was_depleted and inv.quantity_on_hand > 0:
                uow.add_event(
                    InventoryRestocked(
                        actor_id=input.actor_id,
                        variant_id=inv.variant_id,
                        quantity_added=input.quantity,
                        quantity_on_hand=inv.quantity_on_hand,
                    )
                )

            await uow.commit()

        return InventoryResult(
            id=inv.id,
            variant_id=inv.variant_id,
            quantity_on_hand=inv.quantity_on_hand,
            quantity_reserved=inv.quantity_reserved,
            available=inv.available,
            updated_at=inv.updated_at,
        )
