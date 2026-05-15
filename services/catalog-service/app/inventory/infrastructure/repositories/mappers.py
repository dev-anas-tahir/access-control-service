from app.inventory.domain.entities.inventory import Inventory
from app.inventory.infrastructure.orm.inventory import Inventory as InventoryORM


def _inventory_orm_to_domain(orm: InventoryORM) -> Inventory:
    return Inventory(
        id=orm.id,
        variant_id=orm.variant_id,
        quantity_on_hand=orm.quantity_on_hand,
        quantity_reserved=orm.quantity_reserved,
        updated_at=orm.updated_at,
    )
