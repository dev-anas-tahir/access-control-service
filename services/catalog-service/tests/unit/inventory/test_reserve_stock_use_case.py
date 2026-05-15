import uuid

import pytest

from app.inventory.application.dto import ReserveStockInput
from app.inventory.application.use_cases.reserve_stock import ReserveStockUseCase
from app.inventory.domain.events import InventoryDepleted
from app.inventory.domain.exceptions import (
    InsufficientStockError,
    InventoryNotFoundError,
)
from tests.unit.inventory.fakes import (
    FakeInventoryRepository,
    FakeInventoryUnitOfWork,
    make_inventory,
)


@pytest.fixture
def inventory():
    return make_inventory(on_hand=5, reserved=0)


@pytest.fixture
def uow(inventory):
    return FakeInventoryUnitOfWork(
        inventory=FakeInventoryRepository(records=[inventory])
    )


async def test_reserves_stock_successfully(uow, inventory):
    use_case = ReserveStockUseCase(uow_factory=lambda: uow)

    result = await use_case.execute(
        ReserveStockInput(
            variant_id=inventory.variant_id,
            quantity=3,
            actor_id=uuid.uuid4(),
        )
    )

    assert result.quantity_reserved == 3
    assert result.available == 2
    assert uow.committed


async def test_fires_depleted_event_when_available_hits_zero(uow, inventory):
    use_case = ReserveStockUseCase(uow_factory=lambda: uow)

    await use_case.execute(
        ReserveStockInput(
            variant_id=inventory.variant_id,
            quantity=5,
            actor_id=uuid.uuid4(),
        )
    )

    assert len(uow.emitted_events) == 1
    assert isinstance(uow.emitted_events[0], InventoryDepleted)


async def test_raises_when_insufficient_stock(uow, inventory):
    use_case = ReserveStockUseCase(uow_factory=lambda: uow)

    with pytest.raises(InsufficientStockError) as exc_info:
        await use_case.execute(
            ReserveStockInput(
                variant_id=inventory.variant_id,
                quantity=10,
                actor_id=uuid.uuid4(),
            )
        )

    assert exc_info.value.available == 5
    assert exc_info.value.requested == 10


async def test_raises_when_inventory_not_found():
    uow = FakeInventoryUnitOfWork()
    use_case = ReserveStockUseCase(uow_factory=lambda: uow)

    with pytest.raises(InventoryNotFoundError):
        await use_case.execute(
            ReserveStockInput(
                variant_id=uuid.uuid4(),
                quantity=1,
                actor_id=uuid.uuid4(),
            )
        )
